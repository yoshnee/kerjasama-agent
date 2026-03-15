from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from src.services.calendar import (
    _sync_fetch_freebusy,
    format_availability,
    CalendarResult,
    BusyPeriod,
)


def test_format_availability_no_busy():
    result = CalendarResult(busy_periods=[])
    text = format_availability(result)
    assert "open" in text.lower()


def test_format_availability_with_busy():
    now = datetime.now(timezone.utc)
    result = CalendarResult(
        busy_periods=[
            BusyPeriod(start=now, end=now + timedelta(hours=1)),
            BusyPeriod(start=now + timedelta(days=1), end=now + timedelta(days=1, hours=2)),
        ]
    )
    text = format_availability(result)
    assert "Busy slots" in text
    assert "All other times are available" in text


def test_format_availability_error():
    result = CalendarResult(error="Token expired")
    text = format_availability(result)
    assert "unavailable" in text.lower()


@patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""})
def test_sync_fetch_missing_credentials():
    now = datetime.now(timezone.utc)
    result = _sync_fetch_freebusy(
        access_token="test",
        refresh_token="test",
        token_expiry=now + timedelta(hours=1),
        time_min=now,
        time_max=now + timedelta(days=60),
    )
    assert result.error is not None
    assert "GOOGLE_CLIENT_ID" in result.error


@patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "id", "GOOGLE_CLIENT_SECRET": "secret"})
@patch("src.services.calendar.build")
def test_sync_fetch_success(mock_build):
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=60)

    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {
            "primary": {
                "busy": [
                    {
                        "start": now.isoformat(),
                        "end": (now + timedelta(hours=1)).isoformat(),
                    }
                ]
            }
        }
    }

    result = _sync_fetch_freebusy(
        access_token="valid_token",
        refresh_token="refresh",
        token_expiry=now + timedelta(hours=1),
        time_min=now,
        time_max=time_max,
    )
    assert result.error is None
    assert len(result.busy_periods) == 1


@patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "id", "GOOGLE_CLIENT_SECRET": "secret"})
def test_sync_fetch_expired_no_refresh():
    now = datetime.now(timezone.utc)
    result = _sync_fetch_freebusy(
        access_token="expired",
        refresh_token=None,
        token_expiry=now - timedelta(hours=1),
        time_min=now,
        time_max=now + timedelta(days=60),
    )
    assert result.error is not None
    assert "refresh token" in result.error.lower()
