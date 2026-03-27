"""Unit tests for collection name extraction.

Tests concrete examples and edge cases for extract_collection_name.

Requirements: season-layout-generator 2.1, 2.2, 2.3, 2.4
"""

import pytest

from season_layout_generator.collection import extract_collection_name


class TestSeasonExtraction:
    """Tests for Season X directory name pattern."""

    def test_season_5(self) -> None:
        assert extract_collection_name("Season 5") == ("5", 5)

    def test_season_1(self) -> None:
        assert extract_collection_name("Season 1") == ("1", 1)

    def test_season_large_number(self) -> None:
        assert extract_collection_name("Season 42") == ("42", 42)

    def test_season_case_insensitive(self) -> None:
        assert extract_collection_name("season 3") == ("3", 3)

    def test_season_mixed_case(self) -> None:
        assert extract_collection_name("SEASON 7") == ("7", 7)


class TestQuestsExtraction:
    """Tests for Quests directory name pattern."""

    def test_quests_title_case(self) -> None:
        assert extract_collection_name("Quests") == ("Quests", None)

    def test_quests_lowercase(self) -> None:
        assert extract_collection_name("quests") == ("Quests", None)

    def test_quests_uppercase(self) -> None:
        assert extract_collection_name("QUESTS") == ("Quests", None)


class TestBountiesExtraction:
    """Tests for Bounties directory name pattern."""

    def test_bounties_title_case(self) -> None:
        assert extract_collection_name("Bounties") == ("Bounties", None)

    def test_bounties_uppercase(self) -> None:
        assert extract_collection_name("BOUNTIES") == ("Bounties", None)

    def test_bounties_lowercase(self) -> None:
        assert extract_collection_name("bounties") == ("Bounties", None)


class TestInvalidNames:
    """Tests for directory names that should raise ValueError."""

    def test_invalid_name(self) -> None:
        with pytest.raises(ValueError, match="Unrecognized directory name"):
            extract_collection_name("Invalid")

    def test_season_without_number(self) -> None:
        with pytest.raises(ValueError, match="Unrecognized directory name"):
            extract_collection_name("Season")

    def test_season_negative_number(self) -> None:
        with pytest.raises(ValueError, match="Unrecognized directory name"):
            extract_collection_name("Season -1")

    def test_season_zero(self) -> None:
        with pytest.raises(ValueError, match="Invalid season number"):
            extract_collection_name("Season 0")

    def test_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Unrecognized directory name"):
            extract_collection_name("")

    def test_season_with_extra_text(self) -> None:
        with pytest.raises(ValueError, match="Unrecognized directory name"):
            extract_collection_name("Season 5 Extra")
