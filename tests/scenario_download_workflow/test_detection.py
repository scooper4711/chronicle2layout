"""Unit tests for scenario_download_workflow.detection.

Tests concrete examples and edge cases for detect_game_system
and system_prefix.
"""

from scenario_download_workflow.detection import (
    GameSystem,
    detect_game_system,
    system_prefix,
)


class TestDetectPathfinder:
    """Tests for Pathfinder Society detection."""

    def test_pathfinder_society_text(self) -> None:
        text = "Welcome to Pathfinder Society Scenario #7-06"
        assert detect_game_system(text) == GameSystem.PFS

    def test_pathfinder_uppercase(self) -> None:
        assert detect_game_system("PATHFINDER SOCIETY") == GameSystem.PFS

    def test_pathfinder_mixed_case(self) -> None:
        assert detect_game_system("pathFINDER soCIETY") == GameSystem.PFS


class TestDetectStarfinder:
    """Tests for Starfinder Society detection."""

    def test_starfinder_society_text(self) -> None:
        text = "Welcome to Starfinder Society Scenario #1-01"
        assert detect_game_system(text) == GameSystem.SFS

    def test_starfinder_uppercase(self) -> None:
        assert detect_game_system("STARFINDER SOCIETY") == GameSystem.SFS

    def test_starfinder_mixed_case(self) -> None:
        assert detect_game_system("starFINDER soCIETY") == GameSystem.SFS


class TestDetectNeither:
    """Tests for text containing neither society string."""

    def test_empty_string(self) -> None:
        assert detect_game_system("") is None

    def test_unrelated_text(self) -> None:
        assert detect_game_system("Just some random PDF content") is None

    def test_partial_match_pathfinder(self) -> None:
        assert detect_game_system("Pathfinder but not the society") is None

    def test_partial_match_starfinder(self) -> None:
        assert detect_game_system("Starfinder but not the society") is None


class TestDetectBothPrecedence:
    """Tests that Pathfinder takes precedence when both are present."""

    def test_pathfinder_before_starfinder(self) -> None:
        text = "Pathfinder Society and Starfinder Society"
        assert detect_game_system(text) == GameSystem.PFS

    def test_starfinder_before_pathfinder(self) -> None:
        text = "Starfinder Society and Pathfinder Society"
        assert detect_game_system(text) == GameSystem.PFS


class TestSystemPrefix:
    """Tests for system_prefix mapping."""

    def test_pfs_prefix(self) -> None:
        assert system_prefix(GameSystem.PFS) == "pfs2"

    def test_sfs_prefix(self) -> None:
        assert system_prefix(GameSystem.SFS) == "sfs2"
