"""
FastAPI webhook router for Instagram/Meta Platform.

GET  /webhook  –  Meta webhook verification (challenge handshake)
POST /webhook  –  Receive Instagram messaging events
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks
from src.config import INSTAGRAM_VERIFY_TOKEN
from src.agent import get_agent
from src.api.instagram import send_message

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
router = APIRouter()


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
    body = await request.json()
    logger.debug("Webhook payload: %s", body)

    for entry in body.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender_id: str = messaging.get("sender", {}).get("id", "")
            message = messaging.get("message", {})
            text: str = message.get("text", "")

            if message.get("is_echo"):
                continue

            if sender_id and text:
                logger.info("[RECV] from=%s text=%s", sender_id[-6:], text[:80])
                background_tasks.add_task(_handle_message, sender_id, text)

    return {"status": "received"}


async def _handle_message(sender_id: str, text: str) -> None:
    """Process a single message through the Agno agent and reply to the user."""
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

        if reply_text:
            logger.info("[SEND] to=%s text=%s", short_id, reply_text[:80])
            chunks = [reply_text[i:i+1000] for i in range(0, len(reply_text), 1000)]
            for chunk in chunks:
                await send_message(sender_id, chunk)
        else:
            logger.warning("[%s] Empty response from agent.", short_id)

    except Exception as exc:
        logger.error("Error handling message from %s: %s", sender_id, exc, exc_info=True)
