"""Property-based tests for scenario_download_workflow.duration.

Uses hypothesis to verify universal properties of duration parsing
across randomly generated inputs.
"""

from datetime import timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from scenario_download_workflow.duration import parse_duration

_VALID_SUFFIXES = ["m", "h", "d"]

_SUFFIX_TO_KWARG = {
    "m": "minutes",
    "h": "hours",
    "d": "days",
}


# Feature: scenario-download-workflow, Property 1: Duration parsing round-trip
@given(
    amount=st.integers(min_value=1, max_value=10_000),
    suffix=st.sampled_from(_VALID_SUFFIXES),
)
def test_valid_duration_produces_correct_timedelta(
    amount: int, suffix: str
) -> None:
    """For any positive int and valid suffix, parse_duration returns
    the corresponding timedelta.

    Validates: Requirements 1.4, 1.8
    """
    value = f"{amount}{suffix}"
    result = parse_duration(value)
    expected = timedelta(**{_SUFFIX_TO_KWARG[suffix]: amount})
    assert result == expected, (
        f"parse_duration({value!r}) = {result}, expected {expected}"
    )


# Feature: scenario-download-workflow, Property 1: Duration parsing round-trip
@given(
    value=st.text(
        st.characters(exclude_categories=("Cs",)),
        min_size=0,
        max_size=20,
    ).filter(lambda s: not _is_valid_duration(s)),
)
def test_invalid_duration_raises_value_error(value: str) -> None:
    """For any string that does not match <positive_int><m|h|d>,
    parse_duration raises ValueError.

    Validates: Requirements 1.4, 1.8
    """
    with pytest.raises(ValueError):
        parse_duration(value)


def _is_valid_duration(value: str) -> bool:
    """Check if a string matches the valid duration pattern."""
    import re
    match = re.match(r"^(\d+)([mhd])$", value)
    if not match:
        return False
    return int(match.group(1)) > 0
