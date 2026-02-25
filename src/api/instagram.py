"""
Instagram Graph API helper.
Sends text messages back to users via the Instagram Messaging API.
"""
import httpx
import logging
import asyncio
from src.config import INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_API_VERSION
from src.interaction_blocker import get_blocker

logger = logging.getLogger(__name__)
GRAPH_INSTAGRAM_BASE_URL = "https://graph.instagram.com"


def _text_messages_url() -> str:
    return f"{GRAPH_INSTAGRAM_BASE_URL}/{INSTAGRAM_API_VERSION}/me/messages"


async def send_message(recipient_id: str, text: str, retry_count: int = 2) -> dict:
    """
    Send a text message to an Instagram user via the Graph API.
    
    Args:
        recipient_id: Instagram user ID
        text: Message text (truncated to 1000 chars)
        retry_count: Number of retries on failure (default: 2)
    
    Returns:
        API response JSON
    
    Raises:
        httpx.HTTPError: If all retries fail
    """
    url = _text_messages_url()
    headers = {
        "Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text[:1000]},  # Instagram limit is 1000 chars
    }

    short_id = recipient_id[-6:]
    last_error = None
    
    for attempt in range(1, retry_count + 1):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                get_blocker().register_agent_outbound_message(recipient_id, payload["message"]["text"])
                logger.info("[%s] Message sent successfully (attempt %d/%d)", short_id, attempt, retry_count)
                return response.json()
        
        except httpx.TimeoutException as e:
            last_error = f"Timeout: {str(e)}"
            logger.warning("[%s] Timeout sending message (attempt %d/%d): %s", short_id, attempt, retry_count, e)
            if attempt < retry_count:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.warning("[%s] HTTP error sending message (attempt %d/%d): %s", short_id, attempt, retry_count, last_error)
            
            # Don't retry on auth errors or permanent errors
            if e.response.status_code in (401, 403, 404):
                raise
            
            if attempt < retry_count:
                await asyncio.sleep(2 ** attempt)
        
        except Exception as e:
            last_error = str(e)
            logger.error("[%s] Error sending message (attempt %d/%d): %s", short_id, attempt, retry_count, e, exc_info=True)
            if attempt < retry_count:
                await asyncio.sleep(2 ** attempt)
    
    # All retries failed
    error_msg = f"Failed to send message after {retry_count} attempts: {last_error}"
    logger.error("[%s] %s", short_id, error_msg)
    raise RuntimeError(error_msg)


async def send_audio_message(
    recipient_id: str,
    audio_url: str,
    retry_count: int = 2,
    is_reusable: bool = False,
) -> dict:
    """
    Send an audio attachment via public HTTPS URL using /me/messages.
    """
    messages_url = _text_messages_url()
    headers = {
        "Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    short_id = recipient_id[-6:]
    last_error = None

    for attempt in range(1, retry_count + 1):
        try:
            payload = {
                "recipient": {"id": recipient_id},
                "message": {
                    "attachment": {
                        "type": "audio",
                        "payload": {
                            "url": audio_url,
                            "is_reusable": is_reusable,
                        },
                    }
                },
            }

            async with httpx.AsyncClient(timeout=25.0) as client:
                send_response = await client.post(messages_url, json=payload, headers=headers)
                send_response.raise_for_status()
                logger.info("[%s] Audio message sent successfully (attempt %d/%d)", short_id, attempt, retry_count)
                return send_response.json()
        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            last_error = f"HTTP {e.response.status_code}: {error_body}"
            logger.warning(
                "[%s] Error sending audio (attempt %d/%d): %s",
                short_id,
                attempt,
                retry_count,
                last_error,
            )
            if attempt < retry_count:
                await asyncio.sleep(2 ** attempt)
        except Exception as e:
            last_error = str(e)
            logger.warning(
                "[%s] Error sending audio (attempt %d/%d): %s",
                short_id,
                attempt,
                retry_count,
                e,
            )
            if attempt < retry_count:
                await asyncio.sleep(2 ** attempt)

    error_msg = f"Failed to send audio after {retry_count} attempts: {last_error}"
    logger.error("[%s] %s", short_id, error_msg)
    raise RuntimeError(error_msg)
