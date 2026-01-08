"""Tests for calendar service."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.services.calendar import (
    AvailabilityResult,
    BusyPeriod,
    format_availability_for_prompt,
    get_calendar_availability,
)


@pytest.fixture
def mock_credentials():
    """Create mock Google credentials."""
    creds = MagicMock()
    creds.token = "mock_access_token"
    creds.expired = False
    creds.valid = True
    return creds


@pytest.fixture
def token_params():
    """Common token parameters for tests."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "token_expiry": datetime.now(timezone.utc) + timedelta(hours=1),
        "oauth_token_id": uuid.uuid4(),
    }


class TestGetCalendarAvailability:
    """Tests for get_calendar_availability function."""

    @patch("src.services.calendar.build")
    @patch("src.services.calendar._get_or_refresh_credentials")
    @patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "test_id", "GOOGLE_CLIENT_SECRET": "test_secret"})
    def test_returns_available_when_no_busy_periods(
        self, mock_get_creds, mock_build, mock_credentials, token_params
    ):
        """Should return available=True when FreeBusy returns no busy periods."""
        mock_get_creds.return_value = mock_credentials

        # Mock FreeBusy response with no busy periods
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.freebusy().query().execute.return_value = {
            "calendars": {"primary": {"busy": []}}
        }

        time_min = datetime(2026, 1, 20, 9, 0, 0)
        time_max = datetime(2026, 1, 20, 17, 0, 0)

        result = get_calendar_availability(
            time_min=time_min,
            time_max=time_max,
            **token_params,
        )

        assert result.available is True
        assert result.busy_periods == []
        assert result.error is None

    @patch("src.services.calendar.build")
    @patch("src.services.calendar._get_or_refresh_credentials")
    @patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "test_id", "GOOGLE_CLIENT_SECRET": "test_secret"})
    def test_returns_busy_when_has_busy_periods(
        self, mock_get_creds, mock_build, mock_credentials, token_params
    ):
        """Should return available=False when FreeBusy returns busy periods."""
        mock_get_creds.return_value = mock_credentials

        # Mock FreeBusy response with busy periods
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.freebusy().query().execute.return_value = {
            "calendars": {
                "primary": {
                    "busy": [
                        {
                            "start": "2026-01-20T10:00:00Z",
                            "end": "2026-01-20T11:00:00Z",
                        },
                        {
                            "start": "2026-01-20T14:00:00Z",
                            "end": "2026-01-20T15:30:00Z",
                        },
                    ]
                }
            }
        }

        time_min = datetime(2026, 1, 20, 9, 0, 0)
        time_max = datetime(2026, 1, 20, 17, 0, 0)

        result = get_calendar_availability(
            time_min=time_min,
            time_max=time_max,
            **token_params,
        )

        assert result.available is False
        assert len(result.busy_periods) == 2
        assert result.error is None

    @patch("src.services.calendar._get_or_refresh_credentials")
    def test_returns_error_when_credentials_fail(
        self, mock_get_creds, token_params
    ):
        """Should return error when credentials cannot be obtained."""
        mock_get_creds.return_value = None

        time_min = datetime(2026, 1, 20, 9, 0, 0)
        time_max = datetime(2026, 1, 20, 17, 0, 0)

        result = get_calendar_availability(
            time_min=time_min,
            time_max=time_max,
            **token_params,
        )

        assert result.available is False
        assert result.error is not None
        assert "credentials" in result.error.lower()

    @patch("src.services.calendar.build")
    @patch("src.services.calendar._get_or_refresh_credentials")
    def test_handles_api_error(
        self, mock_get_creds, mock_build, mock_credentials, token_params
    ):
        """Should handle API errors gracefully."""
        mock_get_creds.return_value = mock_credentials

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.freebusy().query().execute.side_effect = Exception("API error")

        time_min = datetime(2026, 1, 20, 9, 0, 0)
        time_max = datetime(2026, 1, 20, 17, 0, 0)

        result = get_calendar_availability(
            time_min=time_min,
            time_max=time_max,
            **token_params,
        )

        assert result.available is False
        assert result.error is not None


class TestFormatAvailabilityForPrompt:
    """Tests for format_availability_for_prompt function."""

    def test_format_available(self):
        """Should format available result correctly."""
        result = AvailabilityResult(
            available=True,
            busy_periods=[],
            checked_range_start=datetime(2026, 1, 20, 9, 0, 0),
            checked_range_end=datetime(2026, 1, 20, 17, 0, 0),
        )

        formatted = format_availability_for_prompt(result)

        assert "Available" in formatted
        assert "January 20, 2026" in formatted

    def test_format_busy_with_periods(self):
        """Should format busy result with time periods."""
        result = AvailabilityResult(
            available=False,
            busy_periods=[
                BusyPeriod(
                    start=datetime(2026, 1, 20, 10, 0, 0),
                    end=datetime(2026, 1, 20, 11, 0, 0),
                ),
                BusyPeriod(
                    start=datetime(2026, 1, 20, 14, 0, 0),
                    end=datetime(2026, 1, 20, 15, 30, 0),
                ),
            ],
            checked_range_start=datetime(2026, 1, 20, 9, 0, 0),
            checked_range_end=datetime(2026, 1, 20, 17, 0, 0),
        )

        formatted = format_availability_for_prompt(result)

        assert "Busy" in formatted
        assert "January 20, 2026" in formatted
        assert "10:00" in formatted
        assert "11:00" in formatted

    def test_format_error(self):
        """Should format error result correctly."""
        result = AvailabilityResult(
            available=False,
            busy_periods=[],
            checked_range_start=datetime(2026, 1, 20, 9, 0, 0),
            checked_range_end=datetime(2026, 1, 20, 17, 0, 0),
            error="API quota exceeded",
        )

        formatted = format_availability_for_prompt(result)

        assert "Unable to check calendar" in formatted
        assert "API quota exceeded" in formatted
