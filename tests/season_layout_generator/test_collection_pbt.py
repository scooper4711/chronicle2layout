"""Property-based tests for collection name extraction.

Uses hypothesis to verify universal properties of
extract_collection_name across randomly generated inputs.
"""

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from season_layout_generator.collection import (
    SEASON_PATTERN,
    extract_collection_name,
)

KNOWN_NAMES = {"quests", "bounties"}


# Feature: season-layout-generator, Property 1: Season number extraction round trip
@given(season_number=st.integers(min_value=1, max_value=10_000))
def test_season_number_round_trip(season_number: int) -> None:
    """For any positive integer X, extract_collection_name("Season X")
    returns (str(X), X).

    Validates: Requirements 2.1
    """
    dir_name = f"Season {season_number}"
    collection_name, extracted_number = extract_collection_name(dir_name)

    assert collection_name == str(season_number)
    assert extracted_number == season_number


# Feature: season-layout-generator, Property 2: Invalid directory names are rejected
@given(
    name=st.text(min_size=0, max_size=50).filter(
        lambda s: (
            not SEASON_PATTERN.match(s)
            and s.lower() not in KNOWN_NAMES
        )
    )
)
def test_invalid_directory_names_rejected(name: str) -> None:
    """For any string not matching known patterns,
    extract_collection_name raises ValueError.

    Validates: Requirements 2.4
    """
    with pytest.raises(ValueError):
        extract_collection_name(name)
