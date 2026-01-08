"""Tests for AI Agent with Gemini integration."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.agent import (
    AIAgent,
    FALLBACK_RESPONSE,
    NO_DATE_RESPONSE,
)
from src.services.calendar import AvailabilityResult, BusyPeriod
from utils.constants import (
    CATEGORY_GREETING,
    CATEGORY_AVAILABILITY,
    CATEGORY_PRICING,
    BUSINESS_AI_VOICE_NAME,
)


@pytest.fixture
def mock_business():
    """Create a mock Business object for testing."""
    business = MagicMock()
    business.id = uuid.uuid4()
    business.user_id = uuid.uuid4()
    business.business_name = "Test Salon"
    business.business_type = "hair salon"
    business.business_description = "A premium hair salon"
    business.ai_voice = BUSINESS_AI_VOICE_NAME
    business.show_ai_disclaimer = False
    business.pricing_packages = "Haircut: $30, Color: $80"
    return business


@pytest.fixture
def mock_oauth_token():
    """Create a mock OAuth token."""
    token = MagicMock()
    token.id = uuid.uuid4()
    token.access_token = "test_access_token"
    token.refresh_token = "test_refresh_token"
    token.token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    return token


@pytest.fixture
def mock_availability_result():
    """Create a mock AvailabilityResult."""
    return AvailabilityResult(
        available=True,
        busy_periods=[],
        checked_range_start=datetime(2026, 1, 20, 9, 0, 0),
        checked_range_end=datetime(2026, 1, 20, 17, 0, 0),
    )


# ============================================================================
# RESPONSE GENERATION TESTS
# ============================================================================


class TestGenerateResponse:
    """Tests for generate_response method."""

    def test_generate_greeting_response(self, mock_business):
        """Should generate greeting response using Gemini."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.genai") as mock_genai:
                with patch("src.agent.DatabaseClient"):
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client
                    mock_client.models.generate_content.return_value.text = "Hello! Welcome to Test Salon."

                    agent = AIAgent()
                    response = agent.generate_response(
                        message="Hi there!",
                        classification=CATEGORY_GREETING,
                        business=mock_business,
                    )

                    assert response == "Hello! Welcome to Test Salon."
                    mock_client.models.generate_content.assert_called_once()

    def test_generate_availability_response(self, mock_business):
        """Should generate availability response with availability_info."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.genai") as mock_genai:
                with patch("src.agent.DatabaseClient"):
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client
                    mock_client.models.generate_content.return_value.text = "Yes, we're available on January 20th!"

                    agent = AIAgent()
                    response = agent.generate_response(
                        message="Are you free on Jan 20th?",
                        classification=CATEGORY_AVAILABILITY,
                        business=mock_business,
                        availability_info="Available on January 20, 2026",
                    )

                    assert response == "Yes, we're available on January 20th!"
                    # Verify the prompt contains availability info
                    call_args = mock_client.models.generate_content.call_args
                    prompt = call_args.kwargs["contents"]
                    assert "Available on January 20, 2026" in prompt

    def test_generate_pricing_response(self, mock_business):
        """Should generate pricing response with business pricing_packages."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.genai") as mock_genai:
                with patch("src.agent.DatabaseClient"):
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client
                    mock_client.models.generate_content.return_value.text = "Our haircut is $30."

                    agent = AIAgent()
                    response = agent.generate_response(
                        message="How much for a haircut?",
                        classification=CATEGORY_PRICING,
                        business=mock_business,
                    )

                    assert response == "Our haircut is $30."
                    # Verify the prompt contains pricing info
                    call_args = mock_client.models.generate_content.call_args
                    prompt = call_args.kwargs["contents"]
                    assert "Haircut: $30" in prompt

    def test_appends_ai_disclaimer_when_enabled(self, mock_business):
        """Should append AI disclaimer when business.show_ai_disclaimer is True."""
        mock_business.show_ai_disclaimer = True
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.genai") as mock_genai:
                with patch("src.agent.DatabaseClient"):
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client
                    mock_client.models.generate_content.return_value.text = "Hello!"

                    agent = AIAgent()
                    response = agent.generate_response(
                        message="Hi",
                        classification=CATEGORY_GREETING,
                        business=mock_business,
                    )

                    assert "This response was AI generated" in response

    def test_returns_fallback_when_no_api_key(self, mock_business):
        """Should return fallback response when API key not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.agent.DatabaseClient"):
                agent = AIAgent()
                response = agent.generate_response(
                    message="Hi",
                    classification=CATEGORY_GREETING,
                    business=mock_business,
                )

                assert response == FALLBACK_RESPONSE


# ============================================================================
# AVAILABILITY HANDLING TESTS
# ============================================================================


class TestHandleAvailability:
    """Tests for _handle_availability method."""

    async def test_returns_no_date_response_when_no_date_found(self, mock_business):
        """Should return NO_DATE_RESPONSE when no date can be extracted."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient"):
                agent = AIAgent()

                response = await agent._handle_availability(
                    message="Are you available?",  # No date in message
                    business=mock_business,
                )

                assert response == NO_DATE_RESPONSE

    async def test_returns_none_when_no_oauth_token(self, mock_business):
        """Should return None when no OAuth token exists (silent failure)."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient") as mock_db_client_class:
                with patch("src.agent.extract_datetime_range") as mock_extract_date:
                    with patch("src.agent.get_calendar_availability") as mock_get_availability:
                        mock_extract_date.return_value = (
                            datetime(2026, 1, 20, 0, 0),
                            datetime(2026, 1, 20, 23, 59),
                        )
                        mock_db_instance = MagicMock()
                        mock_db_instance.get_oauth_token.return_value = None
                        mock_db_client_class.return_value = mock_db_instance

                        agent = AIAgent()

                        response = await agent._handle_availability(
                            message="Are you free on January 20th?",
                            business=mock_business,
                        )

                        assert response is None
                        mock_get_availability.assert_not_called()

    async def test_returns_none_when_calendar_api_error(self, mock_business, mock_oauth_token):
        """Should return None when calendar API returns an error (silent failure)."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient") as mock_db_client_class:
                with patch("src.agent.extract_datetime_range") as mock_extract_date:
                    with patch("src.agent.get_calendar_availability") as mock_get_availability:
                        mock_extract_date.return_value = (
                            datetime(2026, 1, 20, 0, 0),
                            datetime(2026, 1, 20, 23, 59),
                        )
                        mock_db_instance = MagicMock()
                        mock_db_instance.get_oauth_token.return_value = mock_oauth_token
                        mock_db_client_class.return_value = mock_db_instance

                        mock_get_availability.return_value = AvailabilityResult(
                            available=False,
                            busy_periods=[],
                            checked_range_start=datetime(2026, 1, 20, 0, 0),
                            checked_range_end=datetime(2026, 1, 20, 23, 59),
                            error="API quota exceeded",
                        )

                        agent = AIAgent()

                        response = await agent._handle_availability(
                            message="Are you free on January 20th?",
                            business=mock_business,
                        )

                        assert response is None

    async def test_generates_response_when_available(
        self, mock_business, mock_oauth_token, mock_availability_result
    ):
        """Should generate Gemini response when calendar shows available."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient") as mock_db_client_class:
                with patch("src.agent.extract_datetime_range") as mock_extract_date:
                    with patch("src.agent.get_calendar_availability") as mock_get_availability:
                        with patch("src.agent.genai") as mock_genai:
                            mock_extract_date.return_value = (
                                datetime(2026, 1, 20, 0, 0),
                                datetime(2026, 1, 20, 23, 59),
                            )
                            mock_db_instance = MagicMock()
                            mock_db_instance.get_oauth_token.return_value = mock_oauth_token
                            mock_db_client_class.return_value = mock_db_instance

                            mock_get_availability.return_value = mock_availability_result

                            mock_client = MagicMock()
                            mock_genai.Client.return_value = mock_client
                            mock_client.models.generate_content.return_value.text = "Yes, we're available!"

                            agent = AIAgent()

                            response = await agent._handle_availability(
                                message="Are you free on January 20th?",
                                business=mock_business,
                            )

                            assert response == "Yes, we're available!"
                            mock_client.models.generate_content.assert_called_once()

    async def test_generates_response_when_busy(self, mock_business, mock_oauth_token):
        """Should generate Gemini response with busy periods info."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient") as mock_db_client_class:
                with patch("src.agent.extract_datetime_range") as mock_extract_date:
                    with patch("src.agent.get_calendar_availability") as mock_get_availability:
                        with patch("src.agent.genai") as mock_genai:
                            mock_extract_date.return_value = (
                                datetime(2026, 1, 20, 0, 0),
                                datetime(2026, 1, 20, 23, 59),
                            )
                            mock_db_instance = MagicMock()
                            mock_db_instance.get_oauth_token.return_value = mock_oauth_token
                            mock_db_client_class.return_value = mock_db_instance

                            mock_get_availability.return_value = AvailabilityResult(
                                available=False,
                                busy_periods=[
                                    BusyPeriod(
                                        start=datetime(2026, 1, 20, 10, 0),
                                        end=datetime(2026, 1, 20, 11, 0),
                                    )
                                ],
                                checked_range_start=datetime(2026, 1, 20, 0, 0),
                                checked_range_end=datetime(2026, 1, 20, 23, 59),
                            )

                            mock_client = MagicMock()
                            mock_genai.Client.return_value = mock_client
                            mock_client.models.generate_content.return_value.text = "We're busy 10-11am."

                            agent = AIAgent()

                            response = await agent._handle_availability(
                                message="Are you free on January 20th?",
                                business=mock_business,
                            )

                            assert response == "We're busy 10-11am."
                            # Verify prompt contains busy info
                            call_args = mock_client.models.generate_content.call_args
                            prompt = call_args.kwargs["contents"]
                            assert "Busy" in prompt


# ============================================================================
# INVOKE AGENT TESTS
# ============================================================================


class TestInvokeAgent:
    """Tests for invoke_agent method."""

    async def test_routes_greeting_to_generate_response(self, mock_business):
        """Should route GREETING directly to generate_response."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient"):
                with patch("src.agent.genai") as mock_genai:
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client
                    mock_client.models.generate_content.return_value.text = "Hello!"

                    agent = AIAgent()

                    response = await agent.invoke_agent(
                        category=CATEGORY_GREETING,
                        message="Hi there!",
                        business=mock_business,
                    )

                    assert response == "Hello!"

    async def test_routes_pricing_to_generate_response(self, mock_business):
        """Should route PRICING directly to generate_response."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient"):
                with patch("src.agent.genai") as mock_genai:
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client
                    mock_client.models.generate_content.return_value.text = "Haircut is $30."

                    agent = AIAgent()

                    response = await agent.invoke_agent(
                        category=CATEGORY_PRICING,
                        message="How much?",
                        business=mock_business,
                    )

                    assert response == "Haircut is $30."

    async def test_routes_availability_to_handle_availability(self, mock_business):
        """Should route AVAILABILITY to _handle_availability."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient"):
                agent = AIAgent()

                # Message with no date will return NO_DATE_RESPONSE
                response = await agent.invoke_agent(
                    category=CATEGORY_AVAILABILITY,
                    message="Are you available?",
                    business=mock_business,
                )

                assert response == NO_DATE_RESPONSE


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_gemini_api_error_returns_fallback(self, mock_business):
        """Should return FALLBACK_RESPONSE when Gemini API fails."""
        with patch.dict(os.environ, {"GOOGLE_ADK_API_KEY": "test_key"}):
            with patch("src.agent.DatabaseClient"):
                with patch("src.agent.genai") as mock_genai:
                    mock_client = MagicMock()
                    mock_genai.Client.return_value = mock_client
                    mock_client.models.generate_content.side_effect = Exception("API error")

                    agent = AIAgent()

                    response = agent.generate_response(
                        message="Hi",
                        classification=CATEGORY_GREETING,
                        business=mock_business,
                    )

                    assert response == FALLBACK_RESPONSE
