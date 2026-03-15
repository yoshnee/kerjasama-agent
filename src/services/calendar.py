"""Google Calendar FreeBusy integration (async)."""

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import OAuthToken
from utils.crypto import encrypt_token

logger = logging.getLogger(__name__)

TOKEN_EXPIRY_BUFFER = timedelta(minutes=5)


@dataclass
class BusyPeriod:
    start: datetime
    end: datetime


@dataclass
class CalendarResult:
    busy_periods: list[BusyPeriod] = field(default_factory=list)
    refreshed_token: Optional[str] = None
    refreshed_expiry: Optional[datetime] = None
    timezone: Optional[str] = None
    error: Optional[str] = None


def _sync_fetch_freebusy(
    access_token: str,
    refresh_token: Optional[str],
    token_expiry: Optional[datetime],
    time_min: datetime,
    time_max: datetime,
) -> CalendarResult:
    """Synchronous Google Calendar FreeBusy call (run in executor)."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return CalendarResult(error="GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")

    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    # Check if token needs refresh
    refreshed_token = None
    refreshed_expiry = None
    now = datetime.now(timezone.utc)

    needs_refresh = False
    if token_expiry:
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)
        needs_refresh = token_expiry < now + TOKEN_EXPIRY_BUFFER

    if needs_refresh or not access_token:
        if not refresh_token:
            return CalendarResult(error="Token expired and no refresh token available")
        try:
            credentials.refresh(Request())
            refreshed_token = credentials.token
            refreshed_expiry = credentials.expiry
            logger.info("Access token refreshed successfully")
        except Exception as e:
            logger.error("Failed to refresh token: %s", e)
            return CalendarResult(error=f"Token refresh failed: {e}")

    # Query FreeBusy API and calendar timezone
    try:
        service = build("calendar", "v3", credentials=credentials)

        # Fetch the owner's calendar timezone
        cal_timezone = None
        try:
            tz_setting = service.settings().get(setting="timezone").execute()
            cal_timezone = tz_setting.get("value")
            logger.info("Calendar timezone: %s", cal_timezone)
        except Exception as e:
            logger.warning("Could not fetch calendar timezone: %s", e)

        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "items": [{"id": "primary"}],
        }
        result = service.freebusy().query(body=body).execute()

        busy_periods = []
        calendars = result.get("calendars", {})
        primary = calendars.get("primary", {})
        for busy in primary.get("busy", []):
            start = datetime.fromisoformat(busy["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(busy["end"].replace("Z", "+00:00"))
            busy_periods.append(BusyPeriod(start=start, end=end))

        return CalendarResult(
            busy_periods=busy_periods,
            refreshed_token=refreshed_token,
            refreshed_expiry=refreshed_expiry,
            timezone=cal_timezone,
        )
    except Exception as e:
        logger.error("FreeBusy query failed: %s", e)
        return CalendarResult(error=str(e))


async def get_calendar_availability(
    access_token: str,
    refresh_token: Optional[str],
    token_expiry: Optional[datetime],
    oauth_token_id: uuid.UUID,
    time_min: datetime,
    time_max: datetime,
    db: AsyncSession,
) -> CalendarResult:
    """Fetch calendar availability asynchronously."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        _sync_fetch_freebusy,
        access_token,
        refresh_token,
        token_expiry,
        time_min,
        time_max,
    )

    # If token was refreshed, persist to DB
    if result.refreshed_token:
        encrypted = encrypt_token(result.refreshed_token)
        if encrypted:
            await db.execute(
                update(OAuthToken)
                .where(OAuthToken.id == oauth_token_id)
                .values(access_token=encrypted, expires_at=result.refreshed_expiry)
            )
            await db.commit()

    return result


def format_availability(result: CalendarResult) -> str:
    """Format calendar result for the system prompt, converting to local time."""
    if result.error:
        return "CALENDAR_UNAVAILABLE"

    if not result.busy_periods:
        return "No busy slots found — the calendar appears open for the next 3 months."

    local_tz = None
    if result.timezone:
        try:
            from zoneinfo import ZoneInfo
            local_tz = ZoneInfo(result.timezone)
        except Exception:
            logger.warning("Could not parse timezone: %s", result.timezone)

    # Group busy periods by date in local time
    by_date: dict[str, list[str]] = {}
    for period in result.busy_periods:
        start_local = period.start.astimezone(local_tz) if local_tz else period.start
        end_local = period.end.astimezone(local_tz) if local_tz else period.end
        date_key = start_local.strftime("%A, %B %d, %Y")
        start_time = start_local.strftime("%I:%M %p")
        end_time = end_local.strftime("%I:%M %p")
        by_date.setdefault(date_key, []).append(f"{start_time}-{end_time}")

    lines = []
    for date, slots in by_date.items():
        lines.append(f"- {date}: busy {', '.join(slots)}")

    return "Busy slots (local time):\n" + "\n".join(lines) + "\n\nAll other times are available."
