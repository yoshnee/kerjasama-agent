"""Tests for WhatsApp webhook handler."""

import hashlib
import hmac
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.webhook import verify_signature, extract_message, router
from utils.constants import CATEGORY_GREETING, CATEGORY_AVAILABILITY, CATEGORY_PRICING, CATEGORY_OTHER


# =============================================================================
# SAMPLE PAYLOADS
# =============================================================================

SAMPLE_TEXT_MESSAGE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "123456789",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "15551234567",
                    "phone_number_id": "phone_id_123"
                },
                "messages": [{
                    "from": "14155551234",
                    "id": "wamid.abc123",
                    "timestamp": "1234567890",
                    "type": "text",
                    "text": {"body": "Hello, I need your services"}
                }]
            },
            "field": "messages"
        }]
    }]
}

SAMPLE_STATUS_UPDATE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "123456789",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "15551234567",
                    "phone_number_id": "phone_id_123"
                },
                "statuses": [{
                    "id": "wamid.abc123",
                    "status": "delivered",
                    "timestamp": "1234567890"
                }]
            },
            "field": "messages"
        }]
    }]
}

SAMPLE_IMAGE_MESSAGE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "123456789",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "15551234567",
                    "phone_number_id": "phone_id_123"
                },
                "messages": [{
                    "from": "14155551234",
                    "id": "wamid.abc123",
                    "timestamp": "1234567890",
                    "type": "image",
                    "image": {"id": "img123", "mime_type": "image/jpeg"}
                }]
            },
            "field": "messages"
        }]
    }]
}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def client():
    """Create test client with mocked services."""
    with patch("src.webhook.classifier"), patch("src.webhook.agent"):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)
        yield TestClient(app)


# =============================================================================
# WEBHOOK VERIFICATION TESTS
# =============================================================================

def test_webhook_verification_success(client):
    """
    Test GET /webhook with valid verify_token returns challenge.

    Should verify:
    - Request with hub.mode="subscribe" and correct hub.verify_token
    - Returns 200 OK with hub.challenge as plain text body
    """
    with patch.dict("os.environ", {"WHATSAPP_VERIFY_TOKEN": "test_token"}):
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test_token",
                "hub.challenge": "challenge_string_123"
            }
        )

    assert response.status_code == 200
    assert response.text == "challenge_string_123"


def test_webhook_verification_failure(client):
    """
    Test GET /webhook with invalid verify_token returns 403.

    Should verify:
    - Request with incorrect hub.verify_token returns 403 Forbidden
    - Request with missing hub.mode returns 403 Forbidden
    - Request with hub.mode != "subscribe" returns 403 Forbidden
    """
    with patch.dict("os.environ", {"WHATSAPP_VERIFY_TOKEN": "test_token"}):
        # Wrong token
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "challenge_123"
            }
        )
        assert response.status_code == 403

        # Missing mode
        response = client.get(
            "/webhook",
            params={
                "hub.verify_token": "test_token",
                "hub.challenge": "challenge_123"
            }
        )
        assert response.status_code == 403

        # Wrong mode
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": "test_token",
                "hub.challenge": "challenge_123"
            }
        )
        assert response.status_code == 403


# =============================================================================
# SIGNATURE VALIDATION TESTS
# =============================================================================

def test_webhook_signature_validation_valid():
    """
    Test signature verification with valid signature.

    Should verify:
    - Valid HMAC-SHA256 signature passes verification
    - verify_signature() returns True for correct signature
    """
    app_secret = "test_secret"
    payload = b'{"test": "data"}'

    # Calculate expected signature
    expected_hash = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    signature = f"sha256={expected_hash}"

    with patch.dict("os.environ", {"WHATSAPP_APP_SECRET": app_secret}):
        result = verify_signature(payload, signature)

    assert result is True


def test_webhook_signature_validation_invalid():
    """
    Test signature verification with invalid signature.

    Should verify:
    - Invalid signature fails verification
    - verify_signature() returns False for incorrect signature
    - Missing signature header returns False
    - Malformed signature format returns False
    """
    app_secret = "test_secret"
    payload = b'{"test": "data"}'

    with patch.dict("os.environ", {"WHATSAPP_APP_SECRET": app_secret}):
        # Wrong signature
        assert verify_signature(payload, "sha256=wronghash") is False

        # Missing signature
        assert verify_signature(payload, "") is False
        assert verify_signature(payload, None) is False

        # Malformed signature (no sha256= prefix)
        assert verify_signature(payload, "just_a_hash") is False

    # Missing app secret
    with patch.dict("os.environ", {}, clear=True):
        assert verify_signature(payload, "sha256=somehash") is False


# =============================================================================
# MESSAGE EXTRACTION TESTS
# =============================================================================

def test_message_extraction_text_message():
    """
    Test extracting message details from text message webhook payload.

    Should verify:
    - Correctly extracts "from" phone number
    - Correctly extracts "to" business phone number
    - Correctly extracts message text
    - Correctly extracts business_account_id
    """
    result = extract_message(SAMPLE_TEXT_MESSAGE_PAYLOAD)

    assert result is not None
    assert result["from"] == "14155551234"
    assert result["to"] == "15551234567"
    assert result["text"] == "Hello, I need your services"
    assert result["business_account_id"] == "123456789"
    assert result["message_id"] == "wamid.abc123"
    assert result["phone_number_id"] == "phone_id_123"


def test_message_extraction_status_update():
    """
    Test extract_message returns None for status updates.

    Should verify:
    - Status update payloads return None
    - Non-message webhooks are gracefully ignored
    """
    result = extract_message(SAMPLE_STATUS_UPDATE_PAYLOAD)
    assert result is None


def test_message_extraction_non_text_message():
    """
    Test extract_message returns None for non-text messages.

    Should verify:
    - Image messages return None
    - Audio messages return None
    - Document messages return None
    """
    # Image message
    result = extract_message(SAMPLE_IMAGE_MESSAGE_PAYLOAD)
    assert result is None

    # Audio message
    audio_payload = SAMPLE_IMAGE_MESSAGE_PAYLOAD.copy()
    audio_payload["entry"][0]["changes"][0]["value"]["messages"][0]["type"] = "audio"
    result = extract_message(audio_payload)
    assert result is None


def test_message_extraction_empty_payload():
    """Test extract_message handles empty/malformed payloads."""
    assert extract_message({}) is None
    assert extract_message({"entry": []}) is None
    assert extract_message({"entry": [{"changes": []}]}) is None


# =============================================================================
# WEBHOOK POST ENDPOINT TESTS
# =============================================================================

def test_webhook_post_returns_200(client):
    """
    Test POST /webhook returns 200 OK quickly.

    Should verify:
    - Valid webhook payload with correct signature returns 200
    - Response is returned within acceptable time (< 20 seconds)
    """
    app_secret = "test_secret"
    payload = json.dumps(SAMPLE_TEXT_MESSAGE_PAYLOAD).encode()

    # Calculate valid signature
    signature = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    with patch.dict("os.environ", {"WHATSAPP_APP_SECRET": app_secret}), \
         patch("src.webhook.process_message", new_callable=AsyncMock) as mock_process:

        response = client.post(
            "/webhook",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature
            }
        )

    assert response.status_code == 200
    mock_process.assert_called_once()


def test_webhook_post_invalid_signature(client):
    """
    Test POST /webhook with invalid signature returns 403.

    Should verify:
    - Request with invalid X-Hub-Signature-256 returns 403
    """
    with patch.dict("os.environ", {"WHATSAPP_APP_SECRET": "test_secret"}):
        response = client.post(
            "/webhook",
            json=SAMPLE_TEXT_MESSAGE_PAYLOAD,
            headers={"X-Hub-Signature-256": "sha256=invalid_signature"}
        )

    assert response.status_code == 403


# =============================================================================
# MESSAGE PROCESSING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_process_message_greeting():
    """
    Test processing GREETING message calls agent.

    Should verify:
    - Message classified as GREETING triggers agent.invoke_agent()
    - Agent is called with correct category and message
    """
    from src.webhook import process_message

    mock_business = MagicMock()
    mock_business.id = "biz123"
    mock_business.business_name = "Test Business"
    mock_business.user_id = "user123"

    mock_oauth_token = MagicMock()
    mock_oauth_token.access_token = "test_access_token"

    with patch("src.webhook.DatabaseClient") as mock_db_class, \
         patch("src.webhook.classifier") as mock_classifier, \
         patch("src.webhook.agent") as mock_agent, \
         patch("src.webhook.send_whatsapp_message", new_callable=AsyncMock) as mock_send:

        mock_db = mock_db_class.return_value
        mock_db.get_business_by_whatsapp_account_id.return_value = mock_business
        mock_db.get_oauth_token.return_value = mock_oauth_token

        mock_classifier.classify.return_value = (CATEGORY_GREETING, 0.95)
        mock_agent.invoke_agent = AsyncMock(return_value="Hello! How can I help you?")
        mock_send.return_value = True

        await process_message(
            from_phone="1234567890",
            to_phone="0987654321",
            message_text="Hi, I need your services",
            business_account_id="biz_account_123",
            phone_number_id="phone_123"
        )

        mock_classifier.classify.assert_called_once_with("Hi, I need your services", return_confidence=True)
        mock_agent.invoke_agent.assert_called_once()
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_availability():
    """
    Test processing AVAILABILITY message calls agent.

    Should verify:
    - Message classified as AVAILABILITY triggers agent.invoke_agent()
    - Agent is called with correct category and message
    """
    from src.webhook import process_message

    mock_business = MagicMock()
    mock_business.id = "biz123"
    mock_business.business_name = "Test Business"
    mock_business.user_id = "user123"

    mock_oauth_token = MagicMock()
    mock_oauth_token.access_token = "test_access_token"

    with patch("src.webhook.DatabaseClient") as mock_db_class, \
         patch("src.webhook.classifier") as mock_classifier, \
         patch("src.webhook.agent") as mock_agent, \
         patch("src.webhook.send_whatsapp_message", new_callable=AsyncMock) as mock_send:

        mock_db = mock_db_class.return_value
        mock_db.get_business_by_whatsapp_account_id.return_value = mock_business
        mock_db.get_oauth_token.return_value = mock_oauth_token

        mock_classifier.classify.return_value = (CATEGORY_AVAILABILITY, 0.92)
        mock_agent.invoke_agent = AsyncMock(return_value="I'm available on Saturday!")
        mock_send.return_value = True

        await process_message(
            from_phone="1234567890",
            to_phone="0987654321",
            message_text="Are you available next Saturday?",
            business_account_id="biz_account_123",
            phone_number_id="phone_123"
        )

        mock_classifier.classify.assert_called_once_with("Are you available next Saturday?", return_confidence=True)
        mock_agent.invoke_agent.assert_called_once()
        call_args = mock_agent.invoke_agent.call_args
        assert call_args[1]["category"] == CATEGORY_AVAILABILITY


@pytest.mark.asyncio
async def test_process_message_pricing():
    """
    Test processing PRICING message calls agent.

    Should verify:
    - Message classified as PRICING triggers agent.invoke_agent()
    - Agent is called with correct category and message
    """
    from src.webhook import process_message

    mock_business = MagicMock()
    mock_business.id = "biz123"
    mock_business.business_name = "Test Business"
    mock_business.user_id = "user123"

    mock_oauth_token = MagicMock()
    mock_oauth_token.access_token = "test_access_token"

    with patch("src.webhook.DatabaseClient") as mock_db_class, \
         patch("src.webhook.classifier") as mock_classifier, \
         patch("src.webhook.agent") as mock_agent, \
         patch("src.webhook.send_whatsapp_message", new_callable=AsyncMock) as mock_send:

        mock_db = mock_db_class.return_value
        mock_db.get_business_by_whatsapp_account_id.return_value = mock_business
        mock_db.get_oauth_token.return_value = mock_oauth_token

        mock_classifier.classify.return_value = (CATEGORY_PRICING, 0.98)
        mock_agent.invoke_agent = AsyncMock(return_value="Our packages start at $100/hour")
        mock_send.return_value = True

        await process_message(
            from_phone="1234567890",
            to_phone="0987654321",
            message_text="What are your prices?",
            business_account_id="biz_account_123",
            phone_number_id="phone_123"
        )

        mock_classifier.classify.assert_called_once_with("What are your prices?", return_confidence=True)
        mock_agent.invoke_agent.assert_called_once()
        call_args = mock_agent.invoke_agent.call_args
        assert call_args[1]["category"] == CATEGORY_PRICING


@pytest.mark.asyncio
async def test_process_message_other_ignored():
    """
    Test OTHER category messages are ignored.

    Should verify:
    - Message classified as OTHER does not trigger agent
    - Function returns early without sending response
    """
    from src.webhook import process_message

    mock_business = MagicMock()
    mock_business.id = "biz123"
    mock_business.business_name = "Test Business"

    with patch("src.webhook.DatabaseClient") as mock_db_class, \
         patch("src.webhook.classifier") as mock_classifier, \
         patch("src.webhook.agent") as mock_agent, \
         patch("src.webhook.send_whatsapp_message", new_callable=AsyncMock) as mock_send:

        mock_db = mock_db_class.return_value
        mock_db.get_business_by_whatsapp_account_id.return_value = mock_business

        mock_classifier.classify.return_value = (CATEGORY_OTHER, 0.85)

        await process_message(
            from_phone="1234567890",
            to_phone="0987654321",
            message_text="Thanks!",
            business_account_id="biz_account_123",
            phone_number_id="phone_123"
        )

        mock_classifier.classify.assert_called_once()
        mock_agent.invoke_agent.assert_not_called()
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_business_not_found():
    """
    Test processing exits early when business is not found.
    """
    from src.webhook import process_message

    with patch("src.webhook.DatabaseClient") as mock_db_class, \
         patch("src.webhook.classifier") as mock_classifier, \
         patch("src.webhook.agent") as mock_agent:

        mock_db = mock_db_class.return_value
        mock_db.get_business_by_whatsapp_account_id.return_value = None

        await process_message(
            from_phone="1234567890",
            to_phone="0987654321",
            message_text="Hello",
            business_account_id="unknown_account",
            phone_number_id="phone_123"
        )

        # Should exit early - classifier and agent never called
        mock_classifier.classify.assert_not_called()
        mock_agent.invoke_agent.assert_not_called()
