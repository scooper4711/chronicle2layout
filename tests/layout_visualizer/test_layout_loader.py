"""Unit tests for layout loading and inheritance resolution.

Tests cover build_layout_index, load_layout_with_inheritance,
and canvas merging behaviour including error cases.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import json
from pathlib import Path

import pytest

from layout_visualizer.layout_loader import (
    build_layout_index,
    load_layout_with_inheritance,
)
from layout_visualizer.models import CanvasRegion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_layout(path: Path, data: dict) -> Path:
    """Write a layout dict as JSON to the given path."""
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# build_layout_index
# ---------------------------------------------------------------------------

class TestBuildLayoutIndex:
    """Tests for build_layout_index."""

    def test_indexes_single_layout(self, tmp_path: Path) -> None:
        """A directory with one valid layout produces a single entry."""
        write_layout(tmp_path / "a.json", {"id": "alpha"})

        index = build_layout_index(tmp_path)

        assert index == {"alpha": tmp_path / "a.json"}

    def test_indexes_multiple_layouts(self, tmp_path: Path) -> None:
        """Multiple valid layouts are all indexed."""
        write_layout(tmp_path / "a.json", {"id": "alpha"})
        write_layout(tmp_path / "b.json", {"id": "beta"})

        index = build_layout_index(tmp_path)

        assert len(index) == 2
        assert index["alpha"] == tmp_path / "a.json"
        assert index["beta"] == tmp_path / "b.json"


    def test_indexes_nested_subdirectories(self, tmp_path: Path) -> None:
        """Layouts in subdirectories are discovered recursively."""
        sub = tmp_path / "sub"
        sub.mkdir()
        write_layout(sub / "nested.json", {"id": "nested"})

        index = build_layout_index(tmp_path)

        assert "nested" in index

    def test_skips_file_without_id(self, tmp_path: Path) -> None:
        """A JSON file missing the 'id' field is silently skipped."""
        write_layout(tmp_path / "no_id.json", {"canvas": {}})

        index = build_layout_index(tmp_path)

        assert index == {}

    def test_skips_invalid_json(self, tmp_path: Path) -> None:
        """A file with invalid JSON is silently skipped."""
        (tmp_path / "bad.json").write_text("{not valid", encoding="utf-8")

        index = build_layout_index(tmp_path)

        assert index == {}

    def test_skips_non_json_files(self, tmp_path: Path) -> None:
        """Non-.json files are ignored even if they contain valid JSON."""
        (tmp_path / "readme.txt").write_text('{"id": "sneaky"}', encoding="utf-8")

        index = build_layout_index(tmp_path)

        assert index == {}

    def test_empty_directory(self, tmp_path: Path) -> None:
        """An empty directory produces an empty index."""
        index = build_layout_index(tmp_path)

        assert index == {}


# ---------------------------------------------------------------------------
# load_layout_with_inheritance — single layout (no parent)
# ---------------------------------------------------------------------------

class TestLoadLayoutSingleLayout:
    """Tests for loading a single layout with no parent."""

    def test_extracts_canvas_regions(self, tmp_path: Path) -> None:
        """Canvas entries are parsed into CanvasRegion instances."""
        layout_path = write_layout(tmp_path / "leaf.json", {
            "id": "leaf",
            "canvas": {
                "page": {"x": 0, "y": 0, "x2": 100, "y2": 100},
            },
        })
        index = build_layout_index(tmp_path)

        canvases, _paths = load_layout_with_inheritance(layout_path, index)

        assert "page" in canvases
        region = canvases["page"]
        assert region == CanvasRegion(name="page", x=0.0, y=0.0, x2=100.0, y2=100.0)

    def test_returns_single_path(self, tmp_path: Path) -> None:
        """The file paths list contains only the loaded layout."""
        layout_path = write_layout(tmp_path / "leaf.json", {
            "id": "leaf",
            "canvas": {"page": {"x": 0, "y": 0, "x2": 100, "y2": 100}},
        })
        index = build_layout_index(tmp_path)

        _, paths = load_layout_with_inheritance(layout_path, index)

        assert paths == [layout_path]

    def test_canvas_with_parent_field(self, tmp_path: Path) -> None:
        """A canvas entry with a 'parent' field preserves it."""
        layout_path = write_layout(tmp_path / "leaf.json", {
            "id": "leaf",
            "canvas": {
                "page": {"x": 0, "y": 0, "x2": 100, "y2": 100},
                "main": {"parent": "page", "x": 5, "y": 10, "x2": 95, "y2": 90},
            },
        })
        index = build_layout_index(tmp_path)

        canvases, _paths = load_layout_with_inheritance(layout_path, index)

        assert canvases["main"].parent == "page"

    def test_empty_canvas_object(self, tmp_path: Path) -> None:
        """A layout with an empty canvas object produces no regions."""
        layout_path = write_layout(tmp_path / "empty.json", {
            "id": "empty",
            "canvas": {},
        })
        index = build_layout_index(tmp_path)

        canvases, _paths = load_layout_with_inheritance(layout_path, index)

        assert canvases == {}

    def test_missing_canvas_key(self, tmp_path: Path) -> None:
        """A layout with no 'canvas' key produces no regions."""
        layout_path = write_layout(tmp_path / "no_canvas.json", {
            "id": "no_canvas",
        })
        index = build_layout_index(tmp_path)

        canvases, _paths = load_layout_with_inheritance(layout_path, index)

        assert canvases == {}


# ---------------------------------------------------------------------------
# load_layout_with_inheritance — parent-child chain
# ---------------------------------------------------------------------------

class TestLoadLayoutInheritanceChain:
    """Tests for resolving parent-child inheritance chains."""

    def test_two_level_chain(self, tmp_path: Path) -> None:
        """A child layout inherits canvases from its parent."""
        write_layout(tmp_path / "parent.json", {
            "id": "root",
            "canvas": {
                "page": {"x": 0, "y": 0, "x2": 100, "y2": 100},
            },
        })
        child_path = write_layout(tmp_path / "child.json", {
            "id": "child",
            "parent": "root",
            "canvas": {
                "main": {"parent": "page", "x": 5, "y": 10, "x2": 95, "y2": 90},
            },
        })
        index = build_layout_index(tmp_path)

        canvases, paths = load_layout_with_inheritance(child_path, index)

        assert "page" in canvases
        assert "main" in canvases
        assert len(paths) == 2

    def test_three_level_chain(self, tmp_path: Path) -> None:
        """A grandchild inherits from both parent and grandparent."""
        write_layout(tmp_path / "grandparent.json", {
            "id": "gp",
            "canvas": {"a": {"x": 0, "y": 0, "x2": 100, "y2": 100}},
        })
        write_layout(tmp_path / "parent.json", {
            "id": "p",
            "parent": "gp",
            "canvas": {"b": {"x": 10, "y": 10, "x2": 90, "y2": 90}},
        })
        grandchild_path = write_layout(tmp_path / "grandchild.json", {
            "id": "gc",
            "parent": "p",
            "canvas": {"c": {"x": 20, "y": 20, "x2": 80, "y2": 80}},
        })
        index = build_layout_index(tmp_path)

        canvases, paths = load_layout_with_inheritance(grandchild_path, index)

        assert set(canvases.keys()) == {"a", "b", "c"}
        assert len(paths) == 3

    def test_chain_paths_ordered_root_first(self, tmp_path: Path) -> None:
        """The returned paths list is ordered root-first, leaf-last."""
        parent_path = write_layout(tmp_path / "parent.json", {
            "id": "root",
            "canvas": {},
        })
        child_path = write_layout(tmp_path / "child.json", {
            "id": "child",
            "parent": "root",
            "canvas": {},
        })
        index = build_layout_index(tmp_path)

        _, paths = load_layout_with_inheritance(child_path, index)

        assert paths[0] == parent_path
        assert paths[1] == child_path


# ---------------------------------------------------------------------------
# Canvas merging — child overrides parent
# ---------------------------------------------------------------------------

class TestCanvasMerging:
    """Tests for canvas merging during inheritance resolution."""

    def test_child_overrides_same_named_canvas(self, tmp_path: Path) -> None:
        """When parent and child define the same canvas, child wins."""
        write_layout(tmp_path / "parent.json", {
            "id": "root",
            "canvas": {
                "page": {"x": 0, "y": 0, "x2": 100, "y2": 100},
            },
        })
        child_path = write_layout(tmp_path / "child.json", {
            "id": "child",
            "parent": "root",
            "canvas": {
                "page": {"x": 5, "y": 5, "x2": 95, "y2": 95},
            },
        })
        index = build_layout_index(tmp_path)

        canvases, _ = load_layout_with_inheritance(child_path, index)

        assert canvases["page"].x == pytest.approx(5.0)
        assert canvases["page"].y == pytest.approx(5.0)
        assert canvases["page"].x2 == pytest.approx(95.0)
        assert canvases["page"].y2 == pytest.approx(95.0)

    def test_parent_only_canvases_preserved(self, tmp_path: Path) -> None:
        """Canvases defined only in the parent are kept in the merge."""
        write_layout(tmp_path / "parent.json", {
            "id": "root",
            "canvas": {
                "header": {"x": 0, "y": 0, "x2": 100, "y2": 10},
            },
        })
        child_path = write_layout(tmp_path / "child.json", {
            "id": "child",
            "parent": "root",
            "canvas": {
                "footer": {"x": 0, "y": 90, "x2": 100, "y2": 100},
            },
        })
        index = build_layout_index(tmp_path)

        canvases, _ = load_layout_with_inheritance(child_path, index)

        assert "header" in canvases
        assert "footer" in canvases


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestLoadLayoutErrors:
    """Tests for error conditions in layout loading."""

    def test_missing_layout_file_raises(self, tmp_path: Path) -> None:
        """Loading a nonexistent file raises FileNotFoundError."""
        missing = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            load_layout_with_inheritance(missing, {})

    def test_missing_parent_id_raises(self, tmp_path: Path) -> None:
        """A parent id not in the index raises ValueError."""
        child_path = write_layout(tmp_path / "child.json", {
            "id": "child",
            "parent": "missing_parent",
            "canvas": {},
        })
        index = build_layout_index(tmp_path)

        with pytest.raises(ValueError, match="missing_parent"):
            load_layout_with_inheritance(child_path, index)

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        """A layout file with invalid JSON raises ValueError."""
        bad_path = tmp_path / "bad.json"
        bad_path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_layout_with_inheritance(bad_path, {})
