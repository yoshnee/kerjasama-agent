"""Tests for date parser utility."""

from datetime import datetime, time, timedelta

import pytest

from utils.date_parser import (
    _message_contains_time,
    extract_date_range_for_general_query,
    extract_datetime_range,
)


class TestExtractDatetimeRange:
    """Tests for extract_datetime_range function."""

    def test_tomorrow(self):
        """Should parse 'tomorrow' to next day full window."""
        ref = datetime(2026, 1, 15, 10, 0, 0)
        result = extract_datetime_range("Are you free tomorrow?", ref)

        assert result is not None
        time_min, time_max = result
        assert time_min.date() == datetime(2026, 1, 16).date()
        assert time_min.time() == time.min
        assert time_max.time() == time.max

    def test_specific_date(self):
        """Should parse specific date like 'January 20th'."""
        ref = datetime(2026, 1, 15, 10, 0, 0)
        result = extract_datetime_range("Available on January 20th?", ref)

        assert result is not None
        time_min, time_max = result
        assert time_min.date() == datetime(2026, 1, 20).date()

    def test_specific_date_with_time(self):
        """Should parse date with time like 'January 20th at 2pm'."""
        ref = datetime(2026, 1, 15, 10, 0, 0)
        result = extract_datetime_range("Are you free January 20th at 2pm?", ref)

        assert result is not None
        time_min, time_max = result
        # Should have 1-hour window
        assert time_max - time_min == timedelta(hours=1)

    def test_next_friday(self):
        """Should parse 'next Friday'."""
        # January 15, 2026 is a Wednesday
        ref = datetime(2026, 1, 15, 10, 0, 0)
        result = extract_datetime_range("Can you do next Friday?", ref)

        assert result is not None
        time_min, _ = result
        # Next Friday from Wed Jan 15 is Jan 17
        assert time_min.weekday() == 4  # Friday

    def test_no_date_returns_none(self):
        """Should return None when no date is found."""
        result = extract_datetime_range("What services do you offer?")
        assert result is None

    def test_relative_date_in_past_prefers_future(self):
        """Should prefer future dates for ambiguous cases."""
        ref = datetime(2026, 6, 15, 10, 0, 0)
        result = extract_datetime_range("Are you free on January 15?", ref)

        assert result is not None
        time_min, _ = result
        # Should pick January 2027, not January 2026
        assert time_min.year == 2027


class TestMessageContainsTime:
    """Tests for _message_contains_time helper."""

    def test_time_with_am_pm(self):
        """Should detect '2pm', '3 am' patterns."""
        assert _message_contains_time("at 2pm") is True
        assert _message_contains_time("around 3 am") is True
        assert _message_contains_time("11am works") is True

    def test_time_24hour(self):
        """Should detect '14:30' patterns."""
        assert _message_contains_time("at 14:30") is True
        assert _message_contains_time("2:30 pm") is True

    def test_time_of_day(self):
        """Should detect 'morning', 'afternoon', etc."""
        assert _message_contains_time("tomorrow morning") is True
        assert _message_contains_time("Friday afternoon") is True
        assert _message_contains_time("Saturday evening") is True

    def test_no_time(self):
        """Should return False when no time is present."""
        assert _message_contains_time("Are you free tomorrow?") is False
        assert _message_contains_time("What about January 15th?") is False


class TestExtractDateRangeForGeneralQuery:
    """Tests for extract_date_range_for_general_query function."""

    def test_month_query(self):
        """Should return full month range for 'January'."""
        ref = datetime(2025, 12, 15, 10, 0, 0)
        result = extract_date_range_for_general_query(
            "What's your availability for January?", ref
        )

        assert result is not None
        time_min, time_max = result
        assert time_min == datetime(2026, 1, 1, 0, 0, 0)
        assert time_max.month == 1
        assert time_max.day == 31

    def test_past_month_uses_next_year(self):
        """Should use next year if month is in the past."""
        ref = datetime(2026, 3, 15, 10, 0, 0)
        result = extract_date_range_for_general_query(
            "Any openings in February?", ref
        )

        assert result is not None
        time_min, _ = result
        assert time_min.year == 2027  # February 2027, not 2026

    def test_next_week(self):
        """Should return next week range."""
        # Wednesday January 15, 2026
        ref = datetime(2026, 1, 15, 10, 0, 0)
        result = extract_date_range_for_general_query("Are you free next week?", ref)

        assert result is not None
        time_min, time_max = result
        # Should start on Monday Jan 20
        assert time_min.weekday() == 0  # Monday
        # Should end on Sunday Jan 26
        assert time_max.weekday() == 6  # Sunday

    def test_this_week(self):
        """Should return this week range."""
        # Wednesday January 15, 2026
        ref = datetime(2026, 1, 15, 10, 0, 0)
        result = extract_date_range_for_general_query("Free this week?", ref)

        assert result is not None
        time_min, time_max = result
        # Should start today (Wed)
        assert time_min.date() == ref.date()
        # Should end on Sunday
        assert time_max.weekday() == 6

    def test_weekend(self):
        """Should return weekend range (Sat-Sun)."""
        # Wednesday January 15, 2026
        ref = datetime(2026, 1, 15, 10, 0, 0)
        result = extract_date_range_for_general_query("Free this weekend?", ref)

        assert result is not None
        time_min, time_max = result
        # Should be Saturday
        assert time_min.weekday() == 5
        # Should be Sunday
        assert time_max.weekday() == 6

    def test_falls_back_to_single_date(self):
        """Should fall back to single date extraction."""
        ref = datetime(2026, 1, 15, 10, 0, 0)
        result = extract_date_range_for_general_query("Free on Friday?", ref)

        assert result is not None
        time_min, _ = result
        assert time_min.weekday() == 4  # Friday
