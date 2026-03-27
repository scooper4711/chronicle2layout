"""Unit tests for the layout builder module.

Tests build_layout_json and build_output_path for seasons,
Quests, and Bounties collections with various variant indices.

Requirements: season-layout-generator 15.1-15.12
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from season_layout_generator.layout_builder import build_layout_json, build_output_path
from season_layout_generator.models import CanvasCoordinates, PageRegions


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SAMPLE_CONSENSUS = PageRegions(
    main=CanvasCoordinates(x=6.0, y=10.0, x2=94.0, y2=95.0),
    player_info=CanvasCoordinates(x=0.0, y=0.0, x2=100.0, y2=8.0),
    summary=CanvasCoordinates(x=0.0, y=9.0, x2=100.0, y2=31.0),
    rewards=CanvasCoordinates(x=82.0, y=33.0, x2=100.0, y2=83.0),
    items=CanvasCoordinates(x=0.5, y=50.0, x2=40.0, y2=83.0),
    notes=CanvasCoordinates(x=42.0, y=50.0, x2=77.0, y2=81.0),
    boons=CanvasCoordinates(x=0.5, y=33.0, x2=80.0, y2=49.0),
    reputation=CanvasCoordinates(x=0.2, y=85.0, x2=99.8, y2=93.0),
    session_info=CanvasCoordinates(x=0.0, y=94.0, x2=100.0, y2=100.0),
)


# ---------------------------------------------------------------------------
# build_layout_json — Season layouts
# ---------------------------------------------------------------------------


class TestBuildLayoutJsonSeason:
    """Tests for build_layout_json with season collections."""

    def test_season5_first_variant_id(self) -> None:
        """First variant of Season 5 has id 'pfs2.season5'."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        assert result["id"] == "pfs2.season5"

    def test_season5_first_variant_description(self) -> None:
        """First variant description is 'Season 5 Base Layout'."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        assert result["description"] == "Season 5 Base Layout"

    def test_season5_parent(self) -> None:
        """All layouts have parent 'pfs2'."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        assert result["parent"] == "pfs2"

    def test_season4_first_variant_id(self) -> None:
        """First variant of Season 4 has id 'pfs2.season4'."""
        result = build_layout_json("4", 4, _SAMPLE_CONSENSUS, 0, "4-01")
        assert result["id"] == "pfs2.season4"

    def test_season4_variant1_id(self) -> None:
        """Second variant (index 1) of Season 4 has id 'pfs2.season4a'."""
        result = build_layout_json("4", 4, _SAMPLE_CONSENSUS, 1, "4-09")
        assert result["id"] == "pfs2.season4a"

    def test_season4_variant2_id(self) -> None:
        """Third variant (index 2) of Season 4 has id 'pfs2.season4b'."""
        result = build_layout_json("4", 4, _SAMPLE_CONSENSUS, 2, "4-06")
        assert result["id"] == "pfs2.season4b"

    def test_season4_variant1_description(self) -> None:
        """Subsequent variant description includes starting scenario."""
        result = build_layout_json("4", 4, _SAMPLE_CONSENSUS, 1, "4-09")
        assert result["description"] == "Season 4 Base Layout (starting 4-09)"

    def test_season4_variant2_description(self) -> None:
        """Third variant description includes its starting scenario."""
        result = build_layout_json("4", 4, _SAMPLE_CONSENSUS, 2, "4-06")
        assert result["description"] == "Season 4 Base Layout (starting 4-06)"


# ---------------------------------------------------------------------------
# build_layout_json — Quests and Bounties
# ---------------------------------------------------------------------------


class TestBuildLayoutJsonQuestsBounties:
    """Tests for build_layout_json with Quests and Bounties collections."""

    def test_quests_first_variant_id(self) -> None:
        """First Quests variant has id 'pfs2.quests'."""
        result = build_layout_json("Quests", None, _SAMPLE_CONSENSUS, 0, "Q14")
        assert result["id"] == "pfs2.quests"

    def test_quests_subsequent_variant_id(self) -> None:
        """Second Quests variant has id 'pfs2.questsa'."""
        result = build_layout_json("Quests", None, _SAMPLE_CONSENSUS, 1, "Q18")
        assert result["id"] == "pfs2.questsa"

    def test_quests_first_variant_description(self) -> None:
        """First Quests variant description is 'Quests Base Layout'."""
        result = build_layout_json("Quests", None, _SAMPLE_CONSENSUS, 0, "Q14")
        assert result["description"] == "Quests Base Layout"

    def test_quests_subsequent_variant_description(self) -> None:
        """Subsequent Quests variant includes starting scenario."""
        result = build_layout_json("Quests", None, _SAMPLE_CONSENSUS, 1, "Q18")
        assert result["description"] == "Quests Base Layout (starting Q18)"

    def test_bounties_first_variant_id(self) -> None:
        """First Bounties variant has id 'pfs2.bounties'."""
        result = build_layout_json("Bounties", None, _SAMPLE_CONSENSUS, 0, "B1")
        assert result["id"] == "pfs2.bounties"

    def test_bounties_subsequent_variant_id(self) -> None:
        """Second Bounties variant has id 'pfs2.bountiesa'."""
        result = build_layout_json("Bounties", None, _SAMPLE_CONSENSUS, 1, "B5")
        assert result["id"] == "pfs2.bountiesa"

    def test_bounties_first_variant_description(self) -> None:
        """First Bounties variant description is 'Bounties Base Layout'."""
        result = build_layout_json("Bounties", None, _SAMPLE_CONSENSUS, 0, "B1")
        assert result["description"] == "Bounties Base Layout"


# ---------------------------------------------------------------------------
# build_layout_json — Canvas structure
# ---------------------------------------------------------------------------


class TestBuildLayoutJsonCanvas:
    """Tests for the canvas section of build_layout_json output."""

    def test_canvas_contains_page(self) -> None:
        """Canvas always includes 'page' at (0, 0, 100, 100)."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        page = result["canvas"]["page"]
        assert page == {"x": 0.0, "y": 0.0, "x2": 100.0, "y2": 100.0}

    def test_canvas_main_has_parent_page(self) -> None:
        """The 'main' canvas entry has parent 'page'."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        assert result["canvas"]["main"]["parent"] == "page"

    def test_canvas_main_coordinates(self) -> None:
        """The 'main' canvas entry has the consensus main coordinates."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        main = result["canvas"]["main"]
        assert main["x"] == pytest.approx(6.0)
        assert main["y"] == pytest.approx(10.0)
        assert main["x2"] == pytest.approx(94.0)
        assert main["y2"] == pytest.approx(95.0)

    def test_canvas_regions_have_parent_main(self) -> None:
        """All non-page, non-main regions have parent 'main'."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        canvas = result["canvas"]
        for name, entry in canvas.items():
            if name in ("page", "main"):
                continue
            assert entry["parent"] == "main", f"{name} should have parent 'main'"

    def test_canvas_includes_all_non_none_regions(self) -> None:
        """Canvas includes entries for every non-None region in consensus."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        canvas = result["canvas"]
        expected = {
            "page", "main", "player_info", "summary", "rewards",
            "items", "notes", "boons", "reputation", "session_info",
        }
        assert set(canvas.keys()) == expected

    def test_canvas_omits_none_regions(self) -> None:
        """Canvas omits regions that are None in the consensus."""
        partial = PageRegions(
            main=CanvasCoordinates(x=6.0, y=10.0, x2=94.0, y2=95.0),
            player_info=CanvasCoordinates(x=0.0, y=0.0, x2=100.0, y2=8.0),
        )
        result = build_layout_json("5", 5, partial, 0, "5-01")
        canvas = result["canvas"]
        assert "reputation" not in canvas
        assert "summary" not in canvas
        assert "player_info" in canvas

    def test_canvas_page_has_no_parent(self) -> None:
        """The 'page' canvas entry has no parent field."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        assert "parent" not in result["canvas"]["page"]


# ---------------------------------------------------------------------------
# build_layout_json — JSON 4-space indentation
# ---------------------------------------------------------------------------


class TestJsonIndentation:
    """Tests that the layout dict serializes with 4-space indentation."""

    def test_json_4_space_indentation(self) -> None:
        """json.dumps with indent=4 produces 4-space indented output."""
        result = build_layout_json("5", 5, _SAMPLE_CONSENSUS, 0, "5-01")
        text = json.dumps(result, indent=4)
        lines = text.split("\n")
        # Second line should start with 4 spaces (first level of indentation)
        assert lines[1].startswith("    ")
        # Verify no 2-space-only indentation at the first nesting level
        assert not lines[1].startswith("  ") or lines[1].startswith("    ")


# ---------------------------------------------------------------------------
# build_output_path — Season paths
# ---------------------------------------------------------------------------


class TestBuildOutputPathSeason:
    """Tests for build_output_path with season collections."""

    def test_season5_first_variant(self) -> None:
        """Season 5 first variant produces Season 5/Season5.json."""
        result = build_output_path(Path("/out"), "5", 5, 0)
        assert result == Path("/out/Season 5/Season5.json")

    def test_season4_variant1(self) -> None:
        """Season 4 second variant produces Season 4/Season4a.json."""
        result = build_output_path(Path("/out"), "4", 4, 1)
        assert result == Path("/out/Season 4/Season4a.json")

    def test_season4_variant2(self) -> None:
        """Season 4 third variant produces Season 4/Season4b.json."""
        result = build_output_path(Path("/out"), "4", 4, 2)
        assert result == Path("/out/Season 4/Season4b.json")

    def test_season1_first_variant(self) -> None:
        """Season 1 first variant produces Season 1/Season1.json."""
        result = build_output_path(Path("/out"), "1", 1, 0)
        assert result == Path("/out/Season 1/Season1.json")


# ---------------------------------------------------------------------------
# build_output_path — Quests and Bounties paths
# ---------------------------------------------------------------------------


class TestBuildOutputPathQuestsBounties:
    """Tests for build_output_path with Quests and Bounties collections."""

    def test_quests_first_variant(self) -> None:
        """Quests first variant produces Quests/Quests.json."""
        result = build_output_path(Path("/out"), "Quests", None, 0)
        assert result == Path("/out/Quests/Quests.json")

    def test_quests_subsequent_variant(self) -> None:
        """Quests second variant produces Quests/Questsa.json."""
        result = build_output_path(Path("/out"), "Quests", None, 1)
        assert result == Path("/out/Quests/Questsa.json")

    def test_bounties_first_variant(self) -> None:
        """Bounties first variant produces Bounties/Bounties.json."""
        result = build_output_path(Path("/out"), "Bounties", None, 0)
        assert result == Path("/out/Bounties/Bounties.json")

    def test_bounties_subsequent_variant(self) -> None:
        """Bounties second variant produces Bounties/Bountiesa.json."""
        result = build_output_path(Path("/out"), "Bounties", None, 1)
        assert result == Path("/out/Bounties/Bountiesa.json")
