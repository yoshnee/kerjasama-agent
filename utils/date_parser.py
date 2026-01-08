"""Date/time extraction from natural language messages."""

import logging
import re
from datetime import datetime, time, timedelta
from typing import Optional

import dateparser
from dateparser.search import search_dates

logger = logging.getLogger(__name__)

# Dateparser settings for natural language parsing
DATEPARSER_SETTINGS = {
    "PREFER_DATES_FROM": "future",  # Prefer future dates for ambiguous cases
    "RELATIVE_BASE": None,  # Will be set dynamically to current time
    "RETURN_AS_TIMEZONE_AWARE": False,
}


def extract_datetime_range(
    message: str,
    reference_date: Optional[datetime] = None,
) -> Optional[tuple[datetime, datetime]]:
    """
    Extract date/time range from a natural language message.

    Parses dates like:
    - "tomorrow", "next week", "this Friday"
    - "January 15th", "Jan 15 2026", "15/01/2026"
    - "tomorrow at 2pm", "next Monday evening"
    - "Are you free on the 20th?"

    Args:
        message: The message text to parse
        reference_date: Reference date for relative dates (defaults to now)

    Returns:
        Tuple of (time_min, time_max) datetimes, or None if no date found.
        - If specific time mentioned: 1-hour window
        - If only date mentioned: full day (00:00 to 23:59)
    """
    if reference_date is None:
        reference_date = datetime.now()

    # Update settings with reference date
    settings = DATEPARSER_SETTINGS.copy()
    settings["RELATIVE_BASE"] = reference_date

    # Use search_dates to find dates within sentences
    # This is more robust than parse() for natural language
    found_dates = search_dates(message, settings=settings)

    if not found_dates:
        logger.debug("No date found in message: %s", message[:50])
        return None

    # Filter out false positives - require meaningful date strings
    valid_dates = []
    for date_string, parsed_date in found_dates:
        # Skip very short matches (likely false positives like "do", "me", "are")
        if len(date_string) < 3:
            continue
        # Skip matches that don't look like dates (no digits or date-related words)
        if not _looks_like_date(date_string):
            continue
        valid_dates.append((date_string, parsed_date))

    if not valid_dates:
        logger.debug("No valid date found in message: %s", message[:50])
        return None

    # Use the first valid date (most relevant)
    date_string, parsed_date = valid_dates[0]
    logger.info("Parsed date '%s' from message: %s", date_string, parsed_date)

    # Check if a specific time was mentioned
    has_specific_time = _message_contains_time(message)

    if has_specific_time:
        # Use 1-hour window around the specified time
        time_min = parsed_date
        time_max = parsed_date + timedelta(hours=1)
    else:
        # Use full day window (00:00 to 23:59:59)
        time_min = datetime.combine(parsed_date.date(), time.min)
        time_max = datetime.combine(parsed_date.date(), time.max)

    logger.info("Date range: %s to %s", time_min, time_max)
    return (time_min, time_max)


def _looks_like_date(date_string: str) -> bool:
    """
    Check if a string looks like an actual date reference.

    Filters out false positives from search_dates like "do", "are", "me".

    Args:
        date_string: The extracted date string

    Returns:
        True if it looks like a valid date reference
    """
    date_lower = date_string.lower()

    # Contains digits - likely a real date
    if re.search(r"\d", date_string):
        return True

    # Common date-related words
    date_words = [
        "today",
        "tomorrow",
        "yesterday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "week",
        "month",
        "year",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
        "next",
        "this",
        "last",
        "morning",
        "afternoon",
        "evening",
        "night",
    ]

    for word in date_words:
        if word in date_lower:
            return True

    return False


def _message_contains_time(message: str) -> bool:
    """
    Check if message contains a specific time reference.

    Args:
        message: The message text

    Returns:
        True if message mentions a specific time
    """
    message_lower = message.lower()

    # Time patterns: "2pm", "2:30pm", "14:00", "at 3", "at 3pm"
    time_patterns = [
        r"\d{1,2}:\d{2}",  # 14:30, 2:30
        r"\d{1,2}\s*(am|pm)",  # 2pm, 2 pm
        r"at\s+\d{1,2}",  # at 3, at 14
        r"\b(morning|afternoon|evening|night)\b",  # time of day
        r"\b(noon|midnight)\b",  # specific times
    ]

    for pattern in time_patterns:
        if re.search(pattern, message_lower):
            return True

    return False


def extract_date_range_for_general_query(
    message: str,
    reference_date: Optional[datetime] = None,
) -> Optional[tuple[datetime, datetime]]:
    """
    Extract date range for general availability queries.

    Handles queries like:
    - "What's your availability for January?" → Full month
    - "Are you free next week?" → Full week
    - "Any openings this weekend?" → Sat-Sun

    Args:
        message: The message text
        reference_date: Reference date for relative dates

    Returns:
        Tuple of (time_min, time_max) for the range, or None
    """
    if reference_date is None:
        reference_date = datetime.now()

    message_lower = message.lower()

    # Check for month queries
    month_match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        message_lower,
    )
    if month_match:
        return _get_month_range(month_match.group(1), reference_date)

    # Check for weekend BEFORE "this week" since "this weekend" contains "this week"
    if "weekend" in message_lower:
        return _get_weekend_range(reference_date, "next" in message_lower)

    # Check for "next week" / "this week"
    if "next week" in message_lower:
        return _get_next_week_range(reference_date)
    if "this week" in message_lower:
        return _get_this_week_range(reference_date)

    # Fall back to single date extraction
    return extract_datetime_range(message, reference_date)


def _get_month_range(
    month_name: str, reference_date: datetime
) -> tuple[datetime, datetime]:
    """Get the date range for a named month."""
    month_map = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    month_num = month_map[month_name]

    # Determine year - if month is in the past, use next year
    year = reference_date.year
    if month_num < reference_date.month:
        year += 1

    # First day of month
    time_min = datetime(year, month_num, 1)

    # Last day of month
    if month_num == 12:
        time_max = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        time_max = datetime(year, month_num + 1, 1) - timedelta(seconds=1)

    return (time_min, time_max)


def _get_next_week_range(reference_date: datetime) -> tuple[datetime, datetime]:
    """Get date range for next week (Monday to Sunday)."""
    # Find next Monday
    days_until_monday = (7 - reference_date.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # If today is Monday, get next Monday
    next_monday = reference_date + timedelta(days=days_until_monday)

    time_min = datetime.combine(next_monday.date(), time.min)
    time_max = datetime.combine((next_monday + timedelta(days=6)).date(), time.max)

    return (time_min, time_max)


def _get_this_week_range(reference_date: datetime) -> tuple[datetime, datetime]:
    """Get date range for this week (today to Sunday)."""
    # Days until end of week (Sunday)
    days_until_sunday = 6 - reference_date.weekday()
    end_of_week = reference_date + timedelta(days=days_until_sunday)

    time_min = datetime.combine(reference_date.date(), time.min)
    time_max = datetime.combine(end_of_week.date(), time.max)

    return (time_min, time_max)


def _get_weekend_range(
    reference_date: datetime, next_weekend: bool = False
) -> tuple[datetime, datetime]:
    """Get date range for weekend (Saturday and Sunday)."""
    current_weekday = reference_date.weekday()

    # Calculate days until Saturday (weekday 5)
    if current_weekday <= 5:
        # We're before or on Saturday
        days_until_saturday = 5 - current_weekday
    else:
        # We're on Sunday, Saturday was yesterday
        days_until_saturday = 6  # Wait until next Saturday

    # If we're already on the weekend and asking for "this weekend"
    if days_until_saturday == 0 and not next_weekend:
        # It's Saturday today
        pass
    elif current_weekday == 6 and not next_weekend:
        # It's Sunday today, return today only
        time_min = datetime.combine(reference_date.date(), time.min)
        time_max = datetime.combine(reference_date.date(), time.max)
        return (time_min, time_max)

    # If asking for "next weekend", skip to the following weekend
    if next_weekend:
        if current_weekday < 5:  # Before Saturday
            days_until_saturday += 7
        elif current_weekday == 5:  # On Saturday
            days_until_saturday = 7
        else:  # On Sunday
            days_until_saturday = 6

    saturday = reference_date + timedelta(days=days_until_saturday)

    time_min = datetime.combine(saturday.date(), time.min)
    time_max = datetime.combine((saturday + timedelta(days=1)).date(), time.max)

    return (time_min, time_max)
