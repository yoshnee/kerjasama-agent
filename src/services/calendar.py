"""Google Calendar integration using FreeBusy API."""

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.database_client import DatabaseClient

logger = logging.getLogger(__name__)

# Shared database client instance
_db_client = DatabaseClient()

# Buffer time before token expiry to trigger refresh (5 minutes)
TOKEN_EXPIRY_BUFFER = timedelta(minutes=5)


@dataclass
class BusyPeriod:
    """Represents a busy time slot from the calendar."""

    start: datetime
    end: datetime


@dataclass
class AvailabilityResult:
    """Result of a calendar availability check."""

    available: bool
    busy_periods: list[BusyPeriod]
    checked_range_start: datetime
    checked_range_end: datetime
    error: Optional[str] = None


def get_calendar_availability(
    access_token: str,
    refresh_token: Optional[str],
    token_expiry: Optional[datetime],
    oauth_token_id: uuid.UUID,
    time_min: datetime,
    time_max: datetime,
) -> AvailabilityResult:
    """
    Check Google Calendar availability using FreeBusy API.

    Args:
        access_token: Google OAuth access token
        refresh_token: Google OAuth refresh token (for refreshing expired tokens)
        token_expiry: Token expiry datetime
        oauth_token_id: OAuth token primary key (for updating after refresh)
        time_min: Start of time range to check
        time_max: End of time range to check

    Returns:
        AvailabilityResult with availability status and busy periods
    """
    try:
        # Get credentials, refreshing if needed
        credentials = _get_or_refresh_credentials(
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            oauth_token_id=oauth_token_id,
        )

        if credentials is None:
            return AvailabilityResult(
                available=False,
                busy_periods=[],
                checked_range_start=time_min,
                checked_range_end=time_max,
                error="Failed to obtain valid credentials",
            )

        # Build Calendar service
        service = build("calendar", "v3", credentials=credentials)

        # Query FreeBusy API
        body = {
            "timeMin": time_min.isoformat() + "Z" if time_min.tzinfo is None else time_min.isoformat(),
            "timeMax": time_max.isoformat() + "Z" if time_max.tzinfo is None else time_max.isoformat(),
            "items": [{"id": "primary"}],
        }

        logger.info("Querying FreeBusy API: %s to %s", time_min, time_max)
        result = service.freebusy().query(body=body).execute()

        # Parse busy periods
        busy_periods = []
        calendars = result.get("calendars", {})
        primary_calendar = calendars.get("primary", {})
        busy_times = primary_calendar.get("busy", [])

        for busy in busy_times:
            start = datetime.fromisoformat(busy["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(busy["end"].replace("Z", "+00:00"))
            busy_periods.append(BusyPeriod(start=start, end=end))

        is_available = len(busy_periods) == 0

        logger.info(
            "Availability check result: %s (%d busy periods)",
            "Available" if is_available else "Busy",
            len(busy_periods),
        )

        return AvailabilityResult(
            available=is_available,
            busy_periods=busy_periods,
            checked_range_start=time_min,
            checked_range_end=time_max,
        )

    except Exception as e:
        logger.error("Calendar availability check failed: %s", str(e), exc_info=True)
        return AvailabilityResult(
            available=False,
            busy_periods=[],
            checked_range_start=time_min,
            checked_range_end=time_max,
            error=str(e),
        )


def _get_or_refresh_credentials(
    access_token: str,
    refresh_token: Optional[str],
    token_expiry: Optional[datetime],
    oauth_token_id: uuid.UUID,
) -> Optional[Credentials]:
    """
    Get Google OAuth credentials, refreshing if expired.

    Args:
        access_token: Current access token
        refresh_token: Refresh token for obtaining new access token
        token_expiry: When the access token expires
        oauth_token_id: OAuth token primary key for database update

    Returns:
        Valid Credentials object, or None if refresh failed
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
        return None

    # Create credentials object
    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    # Check if token needs refresh
    now = datetime.now(timezone.utc)
    needs_refresh = False

    if token_expiry:
        # Make token_expiry timezone-aware if it isn't
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)
        needs_refresh = token_expiry < now + TOKEN_EXPIRY_BUFFER

    if needs_refresh or not access_token:
        if not refresh_token:
            logger.error("Token expired and no refresh token available")
            return None

        logger.info("Refreshing expired access token")
        try:
            credentials.refresh(Request())

            # Update token in database
            _db_client.update_oauth_token(
                oauth_token_id=oauth_token_id,
                access_token=credentials.token,
                token_expiry=credentials.expiry,
            )

            logger.info("Access token refreshed successfully")
        except Exception as e:
            logger.error("Failed to refresh access token: %s", str(e), exc_info=True)
            return None

    return credentials


def format_availability_for_prompt(result: AvailabilityResult) -> str:
    """
    Format availability result for use in AI prompt.

    Args:
        result: AvailabilityResult from calendar check

    Returns:
        Human-readable string describing availability
    """
    if result.error:
        return f"Unable to check calendar: {result.error}"

    date_str = result.checked_range_start.strftime("%B %d, %Y")

    if result.available:
        return f"Available on {date_str}"

    # Format busy periods
    busy_strs = []
    for period in result.busy_periods:
        start_time = period.start.strftime("%I:%M %p")
        end_time = period.end.strftime("%I:%M %p")
        busy_strs.append(f"{start_time} - {end_time}")

    busy_list = ", ".join(busy_strs)
    return f"Busy on {date_str} during: {busy_list}"
