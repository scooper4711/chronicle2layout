"""Unit tests for shared_utils.find_layout_file and transform_canvas_coordinates.

Tests edge cases including missing files, single-part IDs, variant suffixes,
scenario references, generic fallback, and canvas coordinate transformation
with missing canvases, nested parent chains, and single-level parents.

Requirements: refactor-chronicle2layout 1.6, 1.7, 1.9
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from shared_utils import find_layout_file, transform_canvas_coordinates


# ---------------------------------------------------------------------------
# find_layout_file tests
# ---------------------------------------------------------------------------

class TestFindLayoutFile:
    """Unit tests for find_layout_file."""

    def test_missing_layout_file_raises_value_error(self, tmp_path: Path) -> None:
        """A layout ID that resolves to a nonexistent file raises ValueError."""
        with pytest.raises(ValueError, match="Layout file not found"):
            find_layout_file(str(tmp_path), "pfs2")

    def test_single_part_id_resolves_correctly(self, tmp_path: Path) -> None:
        """Single-part ID 'pfs2' resolves to <dir>/pfs2/pfs2.json."""
        expected = tmp_path / "pfs2" / "pfs2.json"
        expected.parent.mkdir(parents=True)
        expected.touch()

        result = find_layout_file(str(tmp_path), "pfs2")
        assert result == expected

    def test_season_variant_suffix_a(self, tmp_path: Path) -> None:
        """Variant suffix 'season4a' resolves to Season4a.json."""
        expected = tmp_path / "pfs2" / "s4" / "Season4a.json"
        expected.parent.mkdir(parents=True)
        expected.touch()

        result = find_layout_file(str(tmp_path), "pfs2.season4a")
        assert result == expected

    def test_season_variant_suffix_b(self, tmp_path: Path) -> None:
        """Variant suffix 'season4b' resolves to Season4b.json."""
        expected = tmp_path / "pfs2" / "s4" / "Season4b.json"
        expected.parent.mkdir(parents=True)
        expected.touch()

        result = find_layout_file(str(tmp_path), "pfs2.season4b")
        assert result == expected

    def test_season_variant_prefers_generated_json(self, tmp_path: Path) -> None:
        """When .generated.json exists, variant IDs prefer it over .json."""
        regular = tmp_path / "pfs2" / "s4" / "Season4a.json"
        generated = tmp_path / "pfs2" / "s4" / "Season4a.generated.json"
        regular.parent.mkdir(parents=True)
        regular.touch()
        generated.touch()

        result = find_layout_file(str(tmp_path), "pfs2.season4a")
        assert result == generated

    def test_season_variant_falls_back_to_regular_json(self, tmp_path: Path) -> None:
        """When .generated.json does not exist, variant IDs use .json."""
        regular = tmp_path / "pfs2" / "s4" / "Season4a.json"
        regular.parent.mkdir(parents=True)
        regular.touch()

        result = find_layout_file(str(tmp_path), "pfs2.season4a")
        assert result == regular

    def test_scenario_reference(self, tmp_path: Path) -> None:
        """Scenario ID 'pfs2.s5-07' resolves to <dir>/pfs2/s5/s5-07.json."""
        expected = tmp_path / "pfs2" / "s5" / "s5-07.json"
        expected.parent.mkdir(parents=True)
        expected.touch()

        result = find_layout_file(str(tmp_path), "pfs2.s5-07")
        assert result == expected

    def test_generic_fallback(self, tmp_path: Path) -> None:
        """Unknown second part 'foo' resolves to <dir>/pfs2/foo/foo.json."""
        expected = tmp_path / "pfs2" / "foo" / "foo.json"
        expected.parent.mkdir(parents=True)
        expected.touch()

        result = find_layout_file(str(tmp_path), "pfs2.foo")
        assert result == expected

    def test_season_without_variant(self, tmp_path: Path) -> None:
        """Season ID 'pfs2.season5' resolves to Season 5.json (with space)."""
        expected = tmp_path / "pfs2" / "s5" / "Season 5.json"
        expected.parent.mkdir(parents=True)
        expected.touch()

        result = find_layout_file(str(tmp_path), "pfs2.season5")
        assert result == expected

    def test_missing_variant_file_raises_value_error(self, tmp_path: Path) -> None:
        """Variant ID with no matching file on disk raises ValueError."""
        # Create the directory but not the file
        (tmp_path / "pfs2" / "s4").mkdir(parents=True)

        with pytest.raises(ValueError, match="Layout file not found"):
            find_layout_file(str(tmp_path), "pfs2.season4a")


# ---------------------------------------------------------------------------
# transform_canvas_coordinates tests
# ---------------------------------------------------------------------------

class TestTransformCanvasCoordinates:
    """Unit tests for transform_canvas_coordinates."""

    def test_missing_canvas_key_raises_value_error(self) -> None:
        """Layout JSON without a 'canvas' key raises ValueError."""
        layout_json: dict = {}
        with pytest.raises(ValueError, match="not found in layout"):
            transform_canvas_coordinates(layout_json, "items")

    def test_missing_canvas_name_raises_value_error(self) -> None:
        """Canvas name not present in the 'canvas' dict raises ValueError."""
        layout_json = {"canvas": {"other": {"x": 0, "y": 0, "x2": 100, "y2": 100}}}
        with pytest.raises(ValueError, match="not found in layout"):
            transform_canvas_coordinates(layout_json, "items")

    def test_simple_canvas_no_parent(self) -> None:
        """Canvas without a parent returns its coordinates directly."""
        layout_json = {
            "canvas": {
                "items": {"x": 10, "y": 20, "x2": 80, "y2": 90}
            }
        }
        result = transform_canvas_coordinates(layout_json, "items")
        assert result == [10, 20, 80, 90]

    def test_single_level_parent(self) -> None:
        """Canvas with one parent transforms coordinates relative to parent."""
        layout_json = {
            "canvas": {
                "page": {"x": 10, "y": 20, "x2": 60, "y2": 70},
                "items": {"x": 50, "y": 50, "x2": 100, "y2": 100, "parent": "page"},
            }
        }
        # page spans [10, 20] to [60, 70] → width=50, height=50
        # items at 50%..100% of parent → x: 10 + 0.5*50=35, y: 20 + 0.5*50=45
        #                                  x2: 10 + 1.0*50=60, y2: 20 + 1.0*50=70
        result = transform_canvas_coordinates(layout_json, "items")
        assert result == pytest.approx([35.0, 45.0, 60.0, 70.0])

    def test_nested_parent_chain(self) -> None:
        """Canvas with a two-level parent chain transforms through both levels."""
        layout_json = {
            "canvas": {
                "root": {"x": 0, "y": 0, "x2": 100, "y2": 100},
                "middle": {"x": 50, "y": 50, "x2": 100, "y2": 100, "parent": "root"},
                "leaf": {"x": 0, "y": 0, "x2": 50, "y2": 50, "parent": "middle"},
            }
        }
        # root: [0, 0, 100, 100] (full page)
        # middle: 50%..100% of root → [50, 50, 100, 100] (width=50, height=50)
        # leaf: 0%..50% of middle → x: 50+0*50=50, y: 50+0*50=50
        #                            x2: 50+0.5*50=75, y2: 50+0.5*50=75
        result = transform_canvas_coordinates(layout_json, "leaf")
        assert result == pytest.approx([50.0, 50.0, 75.0, 75.0])
