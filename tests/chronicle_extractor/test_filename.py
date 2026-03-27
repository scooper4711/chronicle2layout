"""Unit tests for chronicle_extractor.filename.

Tests concrete examples and edge cases for sanitize_name and
build_output_path functions.
"""

from pathlib import Path

from chronicle_extractor.filename import build_output_path, sanitize_name
from chronicle_extractor.parser import ScenarioInfo, _BOUNTY_SEASON


class TestSanitizeName:
    """Tests for sanitize_name function."""

    def test_removes_apostrophes(self) -> None:
        assert sanitize_name("Flooded King's Court") == "FloodedKingsCourt"

    def test_removes_colons(self) -> None:
        assert sanitize_name("Part One: The Beginning") == "PartOneTheBeginning"

    def test_removes_question_marks(self) -> None:
        assert sanitize_name("Who Are You?") == "WhoAreYou"

    def test_removes_semicolons(self) -> None:
        assert sanitize_name("Act I; Scene II") == "ActISceneII"

    def test_removes_slashes(self) -> None:
        assert sanitize_name("Day/Night Cycle") == "DayNightCycle"

    def test_removes_backslashes(self) -> None:
        assert sanitize_name("Path\\To\\Glory") == "PathToGlory"

    def test_removes_asterisks(self) -> None:
        assert sanitize_name("Star*Power") == "StarPower"

    def test_removes_angle_brackets(self) -> None:
        assert sanitize_name("The <Great> Escape") == "TheGreatEscape"

    def test_removes_pipes(self) -> None:
        assert sanitize_name("Left|Right") == "LeftRight"

    def test_removes_double_quotes(self) -> None:
        assert sanitize_name('The "Big" One') == "TheBigOne"

    def test_removes_spaces(self) -> None:
        assert sanitize_name("Flooded Kings Court") == "FloodedKingsCourt"

    def test_preserves_casing(self) -> None:
        assert sanitize_name("ThE QuIcK BrOwN") == "ThEQuIcKBrOwN"

    def test_empty_result(self) -> None:
        assert sanitize_name("' : ; ?") == ""

    def test_already_clean(self) -> None:
        assert sanitize_name("CleanName") == "CleanName"

    def test_multiple_unsafe_chars(self) -> None:
        assert sanitize_name("A'B:C;D?E") == "ABCDE"

    def test_preserves_digits(self) -> None:
        assert sanitize_name("Level 10 Dungeon") == "Level10Dungeon"


class TestBuildOutputPath:
    """Tests for build_output_path function."""

    def test_standard_scenario(self) -> None:
        info = ScenarioInfo(season=1, scenario="07", name="Flooded King's Court")
        result = build_output_path(Path("/output"), info)
        expected = Path("/output/Season 1/1-07-FloodedKingsCourtChronicle.pdf")
        assert result == expected

    def test_multi_digit_season(self) -> None:
        info = ScenarioInfo(season=12, scenario="01", name="Big Season")
        result = build_output_path(Path("/out"), info)
        expected = Path("/out/Season 12/12-01-BigSeasonChronicle.pdf")
        assert result == expected

    def test_name_with_colons(self) -> None:
        info = ScenarioInfo(season=3, scenario="15", name="Part One: The Beginning")
        result = build_output_path(Path("/out"), info)
        expected = Path("/out/Season 3/3-15-PartOneTheBeginningChronicle.pdf")
        assert result == expected

    def test_empty_sanitized_name(self) -> None:
        info = ScenarioInfo(season=1, scenario="01", name="' : ;")
        result = build_output_path(Path("/out"), info)
        expected = Path("/out/Season 1/1-01-Chronicle.pdf")
        assert result == expected

    def test_relative_output_dir(self) -> None:
        info = ScenarioInfo(season=2, scenario="03", name="Test")
        result = build_output_path(Path("output"), info)
        expected = Path("output/Season 2/2-03-TestChronicle.pdf")
        assert result == expected

    def test_bounty_output_path(self) -> None:
        info = ScenarioInfo(
            season=_BOUNTY_SEASON, scenario="2", name="Blood of the Beautiful"
        )
        result = build_output_path(Path("/output"), info)
        expected = Path("/output/Bounties/B2-BloodoftheBeautifulChronicle.pdf")
        assert result == expected

    def test_bounty_double_digit(self) -> None:
        info = ScenarioInfo(
            season=_BOUNTY_SEASON, scenario="15", name="Treasure Off The Coast"
        )
        result = build_output_path(Path("/output"), info)
        expected = Path("/output/Bounties/B15-TreasureOffTheCoastChronicle.pdf")
        assert result == expected
