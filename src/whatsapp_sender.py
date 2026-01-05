# whatsapp_sender.py
"""WhatsApp Cloud API message sender."""

import logging

import httpx

logger = logging.getLogger(__name__)

WHATSAPP_API_BASE_URL = "https://graph.facebook.com/v21.0"


async def send_whatsapp_message(
    to_phone: str,
    message: str,
    phone_number_id: str,
    access_token: str
) -> bool:
    """
    Send a WhatsApp message using the Cloud API.

    Args:
        to_phone: Recipient's phone number (with country code, no +)
        message: Text message to send
        phone_number_id: WhatsApp phone number ID (from webhook metadata)
        access_token: Business's WhatsApp access token

    Returns:
        True on success, False on failure
    """
    url = f"{WHATSAPP_API_BASE_URL}/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                logger.info("Message sent successfully to %s", to_phone)
                return True

            logger.error(
                "Failed to send message to %s: status=%d, response=%s",
                to_phone,
                response.status_code,
                response.text,
            )
            return False

    except httpx.RequestError as e:
        logger.error("Request error sending message to %s: %s", to_phone, e)
        return False
