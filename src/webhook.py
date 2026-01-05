# webhook.py
"""WhatsApp webhook handler for incoming messages."""

import hashlib
import hmac
import logging
import os

from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse

from src.classifier import MessageClassifier
from src.agent import AIAgent
from utils.constants import CATEGORY_OTHER, OAUTH_PROVIDER_WHATSAPP
from src.database_client import DatabaseClient
from src.whatsapp_sender import send_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize classifier and agent (will be properly initialized on startup)
classifier: MessageClassifier = None
agent: AIAgent = None

def init_services():
    """Initialize classifier and agent services."""
    global classifier, agent
    logger.info("Initializing classifier...")
    classifier = MessageClassifier()  # Loads pre-trained model
    logger.info("Classifier loaded")

    agent = AIAgent()
    logger.info("Agent initialized")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def verify_signature(payload: bytes, signature: str) -> bool:
    """
    Verify HMAC signature from Meta using WHATSAPP_APP_SECRET.

    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value (format: "sha256=...")

    Returns:
        True if signature is valid, False otherwise
    """
    app_secret = os.getenv("WHATSAPP_APP_SECRET")

    if not app_secret:
        logger.error("WHATSAPP_APP_SECRET not configured")
        return False

    if not signature or not signature.startswith("sha256="):
        logger.warning("Invalid signature format")
        return False

    expected_signature = signature[7:]  # Remove "sha256=" prefix

    # Calculate HMAC SHA256
    computed_hash = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_hash, expected_signature)


def extract_message(payload: dict) -> Optional[dict]:
    """
    Extract from_phone, to_phone, message_text from webhook payload.

    Args:
        payload: Webhook JSON payload from Meta

    Returns:
        Dict with {"from": phone, "to": phone, "text": message, "business_account_id": id}
        None if not a valid text message (could be status update, etc.)
    """
    try:
        entry = payload.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})

        # Check if this is a message (not a status update)
        messages = value.get("messages", [])
        if not messages:
            logger.debug("No messages in payload (might be status update)")
            return None

        message = messages[0]

        # Only process text messages for now
        if message.get("type") != "text":
            #logger.debug("Non-text message type: %s", message.get("type"))
            return None

        # Extract metadata
        metadata = value.get("metadata", {})

        return {
            "from": message.get("from"),  # Customer's phone number
            "to": metadata.get("display_phone_number"),  # Business phone number
            "text": message.get("text", {}).get("body", ""),
            "business_account_id": entry[0].get("id"),  # WABA ID from entry, not phone_number_id
            "message_id": message.get("id"),
            "phone_number_id": metadata.get("phone_number_id"),  # For sending replies
        }

    except (KeyError, IndexError) as e:
        logger.error("Error extracting message: %s", e)
        return None


async def process_message(
    from_phone: str,
    to_phone: str,
    message_text: str,
    business_account_id: str,
    phone_number_id: str
):
    """
    Main message processing flow.

    Args:
        from_phone: Customer's phone number
        to_phone: Business phone number
        message_text: The message content
        business_account_id: WhatsApp Business Account ID
        phone_number_id: WhatsApp phone number ID for sending replies
    """
    # Step 1: Look up business (must be active)
    db_client = DatabaseClient()
    business = db_client.get_business_by_whatsapp_account_id(business_account_id)

    if not business:
        return  # Exit early - don't classify, don't process

    logger.info("Processing message for business: %s (id: %s)", business.business_name, business.id)

    # Step 2: Classify message
    category, confidence = classifier.classify(message_text, return_confidence=True)
    logger.debug("Classified as %s (confidence: %.3f)", category, confidence)

    # Step 3: If OTHER, ignore (return early)
    if category == CATEGORY_OTHER:
        return

    # Step 4: If GREETING/AVAILABILITY/PRICING, call agent
    logger.debug("Invoking agent for %s message", category)

    response_text = await agent.invoke_agent(
        category=category,
        message=message_text,
        business=business
    )

    logger.info("Agent response: %s", response_text[:100] if response_text else "None")

    # Step 5: Send response via WhatsApp
    if not response_text:
        logger.warning("No response text from agent, skipping send")
        return

    # Fetch business's WhatsApp access token
    oauth_token = db_client.get_oauth_token(
        user_id=business.user_id,
        provider=OAUTH_PROVIDER_WHATSAPP
    )

    if not oauth_token:
        logger.error("No WhatsApp OAuth token found for business %s", business.id)
        return

    success = await send_whatsapp_message(
        to_phone=from_phone,
        message=response_text,
        phone_number_id=phone_number_id,
        access_token=oauth_token.access_token
    )

    if success:
        logger.info("Response sent to %s", from_phone)
    else:
        logger.error("Failed to send response to %s", from_phone)


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    WhatsApp webhook verification endpoint.

    Meta sends a GET request with:
    - hub.mode: Should be "subscribe"
    - hub.verify_token: Should match our WHATSAPP_VERIFY_TOKEN
    - hub.challenge: Challenge string to echo back
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verification successful")
        return PlainTextResponse(content=challenge)

    logger.error("Webhook verification failed: mode=%s, token_match=%s", mode, token == verify_token)
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    WhatsApp webhook handler for incoming messages.

    Important: Must return 200 OK within 20 seconds or WhatsApp will retry.
    """
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    # Verify webhook signature
    if not verify_signature(body, signature):
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid HMAC signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Error parsing webhook payload: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.debug("Received webhook payload: %s", payload)

    # Extract message details
    message_data = extract_message(payload)

    if message_data:
        # Process message asynchronously (don't wait for completion)
        # In production, you might want to use a task queue here
        await process_message(
            from_phone=message_data["from"],
            to_phone=message_data["to"],
            message_text=message_data["text"],
            business_account_id=message_data["business_account_id"],
            phone_number_id=message_data["phone_number_id"]
        )

    # Always return 200 OK quickly
    return Response(status_code=200)
