"""Unit tests for scenario_renamer.image_parser.

Tests concrete stems and edge cases for extract_image_scenario_id,
covering PZOPFS patterns, season-number patterns, unrecognized stems,
and suffix extraction.

Requirements: scenario-renamer 13.3, 13.4, 13.5, 13.6, 13.7, 13.8
"""

from scenario_renamer.image_parser import ImageScenarioId, extract_image_scenario_id


class TestPzopfsPattern:
    """Tests for PZOPFS pattern extraction."""

    def test_pzopfs_with_edition_letter_and_suffix(self) -> None:
        result = extract_image_scenario_id("PZOPFS0107E Maps")
        assert result == ImageScenarioId(1, "07", "Maps")

    def test_pzopfs_without_edition_letter_with_suffix(self) -> None:
        result = extract_image_scenario_id("PZOPFS0409 A-Nighttime Ambush")
        assert result == ImageScenarioId(4, "09", "A-Nighttime Ambush")

    def test_pzopfs_with_edition_letter_no_suffix(self) -> None:
        result = extract_image_scenario_id("PZOPFS0101E")
        assert result == ImageScenarioId(1, "01", "")

    def test_pzopfs_without_edition_letter_no_suffix(self) -> None:
        result = extract_image_scenario_id("PZOPFS0101")
        assert result == ImageScenarioId(1, "01", "")

    def test_pzopfs_lowercase(self) -> None:
        result = extract_image_scenario_id("pzopfs0305E Maps")
        assert result == ImageScenarioId(3, "05", "Maps")


class TestSeasonNumberPattern:
    """Tests for season-number pattern extraction."""

    def test_season_number_with_suffix(self) -> None:
        result = extract_image_scenario_id("2-03-Map-1")
        assert result == ImageScenarioId(2, "03", "Map-1")

    def test_pfs_prefix_season_number(self) -> None:
        result = extract_image_scenario_id("PFS 2-21 Map 1")
        assert result == ImageScenarioId(2, "21", "Map 1")


class TestUnrecognizedStems:
    """Tests for stems that match neither pattern."""

    def test_random_word(self) -> None:
        assert extract_image_scenario_id("random-image") is None

    def test_empty_string(self) -> None:
        assert extract_image_scenario_id("") is None


class TestEdgeCases:
    """Edge cases for suffix extraction and pattern boundaries."""

    def test_pzopfs_digits_only_no_edition_letter(self) -> None:
        """PZOPFS with exactly four digits and no edition letter."""
        result = extract_image_scenario_id("PZOPFS0509")
        assert result == ImageScenarioId(5, "09", "")

    def test_pzopfs_digits_only_with_space_suffix(self) -> None:
        result = extract_image_scenario_id("PZOPFS0509 Handout")
        assert result == ImageScenarioId(5, "09", "Handout")
