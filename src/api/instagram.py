"""
Instagram Graph API helper.
Sends text messages back to users via the Instagram Messaging API.
"""
import httpx
from src.config import INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_API_VERSION


async def send_message(recipient_id: str, text: str) -> dict:
    """Send a text message to an Instagram user via the Graph API."""
    url = f"https://graph.instagram.com/{INSTAGRAM_API_VERSION}/me/messages"
    headers = {
        "Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text[:1000]},  # Instagram limit is 1000 chars
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
