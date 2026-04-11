"""Unit tests for scenario_download_workflow.duration.

Tests concrete examples and edge cases for parse_duration.
"""

from datetime import timedelta

import pytest

from scenario_download_workflow.duration import parse_duration


class TestParseDurationValid:
    """Tests for valid duration strings."""

    def test_one_hour(self) -> None:
        assert parse_duration("1h") == timedelta(hours=1)

    def test_thirty_minutes(self) -> None:
        assert parse_duration("30m") == timedelta(minutes=30)

    def test_two_days(self) -> None:
        assert parse_duration("2d") == timedelta(days=2)

    def test_large_day_value(self) -> None:
        assert parse_duration("999d") == timedelta(days=999)


class TestParseDurationInvalid:
    """Tests for invalid duration strings that should raise ValueError."""

    def test_empty_string(self) -> None:
        with pytest.raises(ValueError):
            parse_duration("")

    def test_no_digits(self) -> None:
        with pytest.raises(ValueError):
            parse_duration("abc")

    def test_zero_hours(self) -> None:
        with pytest.raises(ValueError):
            parse_duration("0h")

    def test_negative_hours(self) -> None:
        with pytest.raises(ValueError):
            parse_duration("-1h")

    def test_unknown_suffix(self) -> None:
        with pytest.raises(ValueError):
            parse_duration("1x")

    def test_suffix_only(self) -> None:
        with pytest.raises(ValueError):
            parse_duration("h")

    def test_digits_only(self) -> None:
        with pytest.raises(ValueError):
            parse_duration("3")
