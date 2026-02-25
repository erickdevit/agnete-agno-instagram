"""
FastAPI webhook router for Instagram/Meta Platform.

GET  /webhook  –  Meta webhook verification (challenge handshake)
POST /webhook  –  Receive Instagram messaging events
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import ValidationError
from src.config import ENABLE_INSTAGRAM_AUDIO_REPLY, INSTAGRAM_VERIFY_TOKEN
from src.agent import get_agent
from src.api.instagram import send_audio_message, send_message
from src.api.transcription import transcribe_audio_from_url
from src.api.scope_classifier import is_out_of_scope
from src.api.audio_reply import create_audio_reply_url, resolve_audio_file
from src.models import WebhookMessage
from src.interaction_blocker import get_blocker

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
router = APIRouter()


def _extract_audio_url(attachments) -> str:
    if not attachments:
        return ""

    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        attachment_type = attachment.get("type", "")
        payload = attachment.get("payload", {}) or {}
        url = payload.get("url", "")
        if attachment_type in {"audio", "file"} and url:
            return url
    return ""


# --------------------------------------------------------------------------- #
# GET /webhook – Meta verification                                             #
# --------------------------------------------------------------------------- #

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Meta sends a GET request with hub.challenge when you register the webhook.
    We must reply with hub.challenge if the verify_token matches.
    """
    if hub_mode == "subscribe" and hub_verify_token == INSTAGRAM_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return int(hub_challenge)

    logger.warning("Webhook verification failed: invalid token or mode")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.get("/media/audio/{file_name}")
async def get_audio_file(file_name: str):
    file_path = resolve_audio_file(file_name)
    if not file_path:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(path=file_path, media_type="audio/wav")


# --------------------------------------------------------------------------- #
# POST /webhook – Receive and process messages                                 #
# --------------------------------------------------------------------------- #

@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives all Instagram messaging events.
    Filters for 'messages' entries and processes them asynchronously.
    Meta expects a 200 OK within 20s – we return immediately and process in background.
    """
    # Validate HMAC signature (reject if missing)
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        logger.warning("[SECURITY] Webhook POST received without X-Hub-Signature-256 header")
        raise HTTPException(status_code=403, detail="Missing webhook signature header")
    
    logger.debug("[SECURITY] Webhook signature header present: %s...", signature[:20])
    
    body = await request.json()
    logger.debug("Webhook payload: %s", body)

    blocker = get_blocker()

    for entry in body.get("entry", []):
        entry_id: str = entry.get("id", "")
        for messaging in entry.get("messaging", []):
            sender_id: str = messaging.get("sender", {}).get("id", "")
            recipient_id: str = messaging.get("recipient", {}).get("id", "")
            message = messaging.get("message", {})
            text: str = message.get("text", "")
            attachments = message.get("attachments", [])
            audio_url = _extract_audio_url(attachments)
            is_echo_message = message.get("is_echo", False)
            is_outgoing_message = bool(entry_id and sender_id == entry_id)

            # Outgoing messages (from your Instagram business account) should never
            # be processed by the agent as incoming user messages.
            # For echo events, only block when it is NOT an echo of agent API send.
            if is_echo_message or is_outgoing_message:
                conversation_user_id = recipient_id if is_outgoing_message else sender_id
                logger.info(
                    "[OUTGOING] sender=%s recipient=%s echo=%s text=%s",
                    sender_id[-6:] if sender_id else "",
                    recipient_id[-6:] if recipient_id else "",
                    is_echo_message,
                    text[:80],
                )
                if is_echo_message and conversation_user_id and text:
                    is_agent_echo = blocker.consume_agent_outbound_echo(conversation_user_id, text)
                    if is_agent_echo:
                        logger.info("[OUTGOING] Agent echo ignored for %s", conversation_user_id[-6:])
                    else:
                        logger.info("[OUTGOING] Manual interface interaction detected for %s", conversation_user_id[-6:])
                        blocker.mark_user_interaction(conversation_user_id)
                continue

            if sender_id and text:
                logger.info("[RECV] from=%s text=%s", sender_id[-6:], text[:80])
                background_tasks.add_task(_handle_message, sender_id, text)
            elif sender_id and audio_url:
                logger.info("[RECV] from=%s audio_attachment=1", sender_id[-6:])
                background_tasks.add_task(_handle_audio_message, sender_id, audio_url)

    return {"status": "received"}


async def _handle_audio_message(sender_id: str, audio_url: str) -> None:
    short_id = sender_id[-6:]
    transcription = await transcribe_audio_from_url(audio_url, sender_id)
    if not transcription:
        logger.warning("[%s] Could not transcribe audio attachment", short_id)
        await send_message(sender_id, "Recebi seu audio, mas nao consegui transcrever agora. Pode enviar em texto?")
        return

    logger.info("[%s] Audio transcribed successfully (%d chars)", short_id, len(transcription))
    if await is_out_of_scope(transcription):
        logger.info("[%s] Out-of-scope audio detected, generating agent reply in audio mode", short_id)
        out_of_scope_text = await _generate_agent_reply(sender_id, transcription)
        if not out_of_scope_text:
            out_of_scope_text = (
                "Entendi o que voce disse. Posso te ajudar com motos Shineray, pagamento e simulacao."
            )
        if ENABLE_INSTAGRAM_AUDIO_REPLY:
            reply_audio_url = await create_audio_reply_url(out_of_scope_text)
            if reply_audio_url:
                try:
                    await send_audio_message(sender_id, reply_audio_url)
                    return
                except Exception as exc:
                    logger.warning("[%s] Audio reply failed, falling back to text: %s", short_id, exc)
            else:
                logger.warning("[%s] Could not build audio reply URL, falling back to text", short_id)
        else:
            logger.info("[%s] Instagram audio reply disabled; sending text fallback", short_id)
        await send_message(sender_id, out_of_scope_text)
        return

    await _handle_message(sender_id, transcription)


async def _handle_message(sender_id: str, text: str) -> None:
    """
    Process a single message through the Agno agent and reply to the user.
    Respects user interaction blocks - waits for user to finish interacting.
    """
    short_id = sender_id[-6:]
    blocker = get_blocker()
    
    # Check if agent is blocked (user is actively interacting)
    if blocker.is_blocked(sender_id):
        remaining = blocker.get_remaining_block_time(sender_id)
        logger.info("[%s] Agent blocked - user still interacting (%.0f sec remaining)", 
                   short_id, remaining or 0)
        return
    
    # Validate incoming message format
    try:
        WebhookMessage(sender_id=sender_id, text=text)
    except ValidationError as e:
        logger.error("[%s] Invalid message format: %s", short_id, e)
        return

    reply_text = await _generate_agent_reply(sender_id, text)

    if reply_text:
        logger.info("[SEND] to=%s text=%s", short_id, reply_text[:80])
        chunks = [reply_text[i:i+1000] for i in range(0, len(reply_text), 1000)]
        for chunk in chunks:
            await send_message(sender_id, chunk)
    else:
        logger.warning("[%s] Empty response from agent.", short_id)


async def _generate_agent_reply(sender_id: str, text: str) -> str:
    short_id = sender_id[-6:]
    try:
        agent = get_agent(session_id=sender_id)

        def _run_agent():
            return agent.run(text)

        response = await asyncio.to_thread(_run_agent)

        reply_text = ""
        if response is not None:
            if hasattr(response, "content") and response.content:
                reply_text = response.content
            elif isinstance(response, str):
                reply_text = response
        return reply_text or ""

    except Exception as exc:
        logger.error("[%s] Error handling message: %s", short_id, exc, exc_info=True)
        # Try to notify user of error
        try:
            await send_message(sender_id, "Desculpe, encontrei um erro ao processar sua mensagem. Tente novamente mais tarde.")
        except Exception as notify_exc:
            logger.error("[%s] Failed to send error message to user: %s", short_id, notify_exc)
        return ""
