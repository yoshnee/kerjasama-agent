# tests/test_whatsapp_sender.py
"""Tests for WhatsApp message sender."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.whatsapp_sender import send_whatsapp_message, WHATSAPP_API_BASE_URL


@pytest.mark.asyncio
async def test_send_message_success():
    """Test successful message sending."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("src.whatsapp_sender.httpx.AsyncClient", return_value=mock_client):
        result = await send_whatsapp_message(
            to_phone="1234567890",
            message="Hello, this is a test message",
            phone_number_id="phone123",
            access_token="test_token"
        )

    assert result is True
    mock_client.post.assert_called_once()

    # Verify the correct URL and payload
    call_args = mock_client.post.call_args
    assert call_args[0][0] == f"{WHATSAPP_API_BASE_URL}/phone123/messages"
    assert call_args[1]["json"]["to"] == "1234567890"
    assert call_args[1]["json"]["text"]["body"] == "Hello, this is a test message"
    assert call_args[1]["headers"]["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_send_message_failure():
    """Test message sending failure (API error)."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("src.whatsapp_sender.httpx.AsyncClient", return_value=mock_client):
        result = await send_whatsapp_message(
            to_phone="1234567890",
            message="Hello",
            phone_number_id="phone123",
            access_token="test_token"
        )

    assert result is False


@pytest.mark.asyncio
async def test_invalid_phone_number():
    """Test sending to invalid phone number."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"error": {"message": "Invalid phone number format"}}'

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("src.whatsapp_sender.httpx.AsyncClient", return_value=mock_client):
        result = await send_whatsapp_message(
            to_phone="invalid",
            message="Hello",
            phone_number_id="phone123",
            access_token="test_token"
        )

    assert result is False


@pytest.mark.asyncio
async def test_send_message_network_error():
    """Test handling of network errors."""
    import httpx

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.RequestError("Connection failed")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("src.whatsapp_sender.httpx.AsyncClient", return_value=mock_client):
        result = await send_whatsapp_message(
            to_phone="1234567890",
            message="Hello",
            phone_number_id="phone123",
            access_token="test_token"
        )

    assert result is False
