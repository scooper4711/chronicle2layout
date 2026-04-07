"""Unit tests for layout loading and inheritance resolution.

Tests cover build_layout_index, load_layout_with_inheritance,
and canvas merging behaviour including error cases.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import json
from pathlib import Path

import pytest

from layout_visualizer.layout_loader import (
    _extract_fields_from_content,
    _extract_preset_based_field,
    build_layout_index,
    load_content_fields,
    load_layout_with_inheritance,
    merge_presets,
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


# ---------------------------------------------------------------------------
# Preset merging in load_content_fields
# ---------------------------------------------------------------------------

class TestPresetMergingInContentFields:
    """Tests for preset merging during content field extraction.

    Validates Requirements 4.1 and 4.2: presets from parent layouts are
    merged root-to-leaf, and child definitions override parent definitions
    for the same preset name.
    """

    def test_merge_presets_parent_presets_available(self) -> None:
        """Parent preset definitions are present in the merged result."""
        chain: list[tuple[Path, dict]] = [
            (Path("parent.json"), {
                "id": "parent",
                "presets": {
                    "strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95},
                },
            }),
            (Path("child.json"), {
                "id": "child",
                "parent": "parent",
                "presets": {
                    "item.line.potion": {"y": 55.4, "y2": 58.9},
                },
            }),
        ]

        merged = merge_presets(chain)

        assert "strikeout_item" in merged
        assert merged["strikeout_item"]["canvas"] == "items"
        assert "item.line.potion" in merged

    def test_merge_presets_child_overrides_parent(self) -> None:
        """Child preset definition overrides parent for the same name."""
        chain: list[tuple[Path, dict]] = [
            (Path("parent.json"), {
                "id": "parent",
                "presets": {
                    "strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95},
                },
            }),
            (Path("child.json"), {
                "id": "child",
                "parent": "parent",
                "presets": {
                    "strikeout_item": {"canvas": "items_v2", "x": 1.0, "x2": 90},
                },
            }),
        ]

        merged = merge_presets(chain)

        assert merged["strikeout_item"]["canvas"] == "items_v2"
        assert merged["strikeout_item"]["x"] == pytest.approx(1.0)
        assert merged["strikeout_item"]["x2"] == pytest.approx(90)

    def test_merge_presets_empty_chain(self) -> None:
        """An empty chain produces an empty presets dict."""
        merged = merge_presets([])

        assert merged == {}

    def test_merge_presets_layout_without_presets_key(self) -> None:
        """Layouts missing the presets key are silently skipped."""
        chain: list[tuple[Path, dict]] = [
            (Path("no_presets.json"), {"id": "bare"}),
        ]

        merged = merge_presets(chain)

        assert merged == {}

    def test_load_content_fields_with_parent_presets(self, tmp_path: Path) -> None:
        """load_content_fields succeeds on a chain where parent defines presets."""
        write_layout(tmp_path / "parent.json", {
            "id": "root",
            "canvas": {
                "page": {"x": 0, "y": 0, "x2": 100, "y2": 100},
                "items": {"parent": "page", "x": 5, "y": 10, "x2": 95, "y2": 90},
            },
            "presets": {
                "strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95},
            },
        })
        child_path = write_layout(tmp_path / "child.json", {
            "id": "child",
            "parent": "root",
            "presets": {
                "item.line.potion": {"y": 55.4, "y2": 58.9},
            },
            "content": [
                {
                    "type": "strikeout",
                    "presets": ["strikeout_item", "item.line.potion"],
                },
            ],
        })
        index = build_layout_index(tmp_path)

        _fields, canvases, paths = load_content_fields(child_path, index)

        assert "page" in canvases
        assert "items" in canvases
        assert len(paths) == 2

    def test_load_content_fields_child_preset_override(self, tmp_path: Path) -> None:
        """Child preset override is used when parent and child define the same name."""
        write_layout(tmp_path / "parent.json", {
            "id": "root",
            "canvas": {
                "page": {"x": 0, "y": 0, "x2": 100, "y2": 100},
            },
            "presets": {
                "shared_preset": {"canvas": "page", "x": 10, "x2": 90},
            },
            "content": [],
        })
        child_path = write_layout(tmp_path / "child.json", {
            "id": "child",
            "parent": "root",
            "presets": {
                "shared_preset": {"canvas": "page", "x": 20, "x2": 80},
            },
            "content": [
                {
                    "type": "text",
                    "canvas": "page",
                    "x": 0,
                    "y": 0,
                    "x2": 100,
                    "y2": 100,
                    "value": "visible_field",
                },
            ],
        })
        index = build_layout_index(tmp_path)

        fields, _canvases, paths = load_content_fields(child_path, index)

        # The inline text field is extracted; no crash from preset merging
        assert len(fields) == 1
        assert fields[0].name == "visible_field"
        assert len(paths) == 2


# ---------------------------------------------------------------------------
# Strikeout entry extraction
# ---------------------------------------------------------------------------

class TestStrikeoutEntryExtraction:
    """Tests for strikeout entry extraction via preset resolution.

    Validates Requirements 2.1, 2.2, 2.3, 5.1, 5.2.
    """

    def test_strikeout_with_resolved_presets_produces_canvas_region(self) -> None:
        """A strikeout entry with fully resolved preset coordinates yields a field."""
        presets = {
            "strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95},
            "item.line.some_key": {"y": 3.5, "y2": 7.0},
        }
        content = [
            {
                "type": "choice",
                "content": {
                    "Some Item (level 4; 75 gp)": [
                        {
                            "type": "strikeout",
                            "presets": ["strikeout_item", "item.line.some_key"],
                        }
                    ],
                },
            }
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 1
        assert fields[0].parent == "items"
        assert fields[0].x == pytest.approx(0.5)
        assert fields[0].y == pytest.approx(3.5)
        assert fields[0].x2 == pytest.approx(95)
        assert fields[0].y2 == pytest.approx(7.0)

    def test_choice_key_text_used_as_label(self) -> None:
        """The choice key text is propagated as the field name."""
        presets = {
            "strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95},
            "item.line.potion": {"y": 55.4, "y2": 58.9},
        }
        content = [
            {
                "type": "choice",
                "content": {
                    "Potion of invisibility (level 4; 20 gp)": [
                        {
                            "type": "strikeout",
                            "presets": ["strikeout_item", "item.line.potion"],
                        }
                    ],
                },
            }
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 1
        assert fields[0].name == "Potion of invisibility (level 4; 20 gp)"

    def test_incomplete_coordinates_after_resolution_skipped(self) -> None:
        """A strikeout entry missing y/y2 after preset resolution is skipped."""
        presets = {
            "strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95},
        }
        content = [
            {"type": "strikeout", "presets": ["strikeout_item"]},
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 0

    def test_missing_preset_reference_skipped(self) -> None:
        """A strikeout entry referencing a nonexistent preset is skipped."""
        content = [
            {"type": "strikeout", "presets": ["nonexistent"]},
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], {})

        assert len(fields) == 0


# ---------------------------------------------------------------------------
# Checkbox entry extraction
# ---------------------------------------------------------------------------

class TestCheckboxEntryExtraction:
    """Tests for checkbox entry extraction via preset resolution.

    Validates Requirements 6.1, 6.2, 6.3, 6.6.
    """

    def test_checkbox_with_resolved_presets_produces_canvas_region(self) -> None:
        """A checkbox entry with fully resolved preset coordinates yields a field."""
        presets = {
            "checkbox": {"canvas": "summary"},
            "checkbox.killed": {
                "x": 69.71, "y": 46.228, "x2": 71.41, "y2": 59.449,
            },
        }
        content = [
            {
                "type": "choice",
                "content": {
                    "killed": [
                        {
                            "type": "checkbox",
                            "presets": ["checkbox", "checkbox.killed"],
                        }
                    ],
                },
            }
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 1
        assert fields[0].parent == "summary"
        assert fields[0].x == pytest.approx(69.71)
        assert fields[0].y == pytest.approx(46.228)
        assert fields[0].x2 == pytest.approx(71.41)
        assert fields[0].y2 == pytest.approx(59.449)

    def test_choice_key_text_used_as_checkbox_label(self) -> None:
        """The choice key text is propagated as the checkbox field name."""
        presets = {
            "checkbox": {"canvas": "summary"},
            "checkbox.recruited": {
                "x": 10.0, "y": 20.0, "x2": 15.0, "y2": 25.0,
            },
        }
        content = [
            {
                "type": "choice",
                "content": {
                    "recruited": [
                        {
                            "type": "checkbox",
                            "presets": ["checkbox", "checkbox.recruited"],
                        }
                    ],
                },
            }
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 1
        assert fields[0].name == "recruited"

    def test_checkbox_nested_inside_choice_content_map(self) -> None:
        """Checkbox entries nested in multiple choice keys are all extracted."""
        presets = {
            "checkbox": {"canvas": "summary"},
            "checkbox.killed": {
                "x": 69.71, "y": 46.228, "x2": 71.41, "y2": 59.449,
            },
            "checkbox.recruited": {
                "x": 10.0, "y": 20.0, "x2": 15.0, "y2": 25.0,
            },
        }
        content = [
            {
                "type": "choice",
                "content": {
                    "killed": [
                        {
                            "type": "checkbox",
                            "presets": ["checkbox", "checkbox.killed"],
                        }
                    ],
                    "recruited": [
                        {
                            "type": "checkbox",
                            "presets": ["checkbox", "checkbox.recruited"],
                        }
                    ],
                },
            }
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 2
        names = {f.name for f in fields}
        assert names == {"killed", "recruited"}


# ---------------------------------------------------------------------------
# Choice content traversal
# ---------------------------------------------------------------------------

class TestChoiceContentTraversal:
    """Tests for choice content map traversal during field extraction.

    Validates Requirements 3.1, 3.2, 3.3.
    """

    def test_all_choice_keys_iterated(self) -> None:
        """Every key in a choice content map is visited."""
        presets = {
            "strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95},
            "item.line.a": {"y": 3.5, "y2": 7.0},
            "item.line.b": {"y": 10.0, "y2": 14.0},
            "item.line.c": {"y": 20.0, "y2": 24.0},
        }
        content = [
            {
                "type": "choice",
                "content": {
                    "Item A": [
                        {"type": "strikeout", "presets": ["strikeout_item", "item.line.a"]},
                    ],
                    "Item B": [
                        {"type": "strikeout", "presets": ["strikeout_item", "item.line.b"]},
                    ],
                    "Item C": [
                        {"type": "strikeout", "presets": ["strikeout_item", "item.line.c"]},
                    ],
                },
            }
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 3

    def test_entries_from_all_branches_included(self) -> None:
        """Fields from every choice branch appear in the output."""
        presets = {
            "strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95},
            "item.line.a": {"y": 3.5, "y2": 7.0},
            "item.line.b": {"y": 10.0, "y2": 14.0},
        }
        content = [
            {
                "type": "choice",
                "content": {
                    "Item A": [
                        {"type": "strikeout", "presets": ["strikeout_item", "item.line.a"]},
                    ],
                    "Item B": [
                        {"type": "strikeout", "presets": ["strikeout_item", "item.line.b"]},
                    ],
                },
            }
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 2
        names = {f.name for f in fields}
        assert "Item A" in names
        assert "Item B" in names

    def test_choice_key_propagated_as_label(self) -> None:
        """The choice key is used as the label for nested preset-based entries."""
        presets = {
            "checkbox": {"canvas": "summary"},
            "checkbox.killed": {
                "x": 69.71, "y": 46.228, "x2": 71.41, "y2": 59.449,
            },
        }
        content = [
            {
                "type": "choice",
                "content": {
                    "killed": [
                        {
                            "type": "checkbox",
                            "presets": ["checkbox", "checkbox.killed"],
                        }
                    ],
                },
            }
        ]
        fields: list[CanvasRegion] = []

        _extract_fields_from_content(content, fields, [0], presets)

        assert len(fields) == 1
        assert fields[0].name == "killed"


# ---------------------------------------------------------------------------
# Graceful error handling
# ---------------------------------------------------------------------------

class TestGracefulErrorHandling:
    """Tests for graceful skipping of unresolvable entries.

    Validates Requirements 5.1, 5.2, 5.3.
    """

    def test_nonexistent_preset_skipped_without_error(self) -> None:
        """An entry referencing a nonexistent preset is silently skipped."""
        entry = {"type": "strikeout", "presets": ["does_not_exist"]}
        result = _extract_preset_based_field(entry, {}, None, [0])
        assert result is None

    def test_missing_y_coordinates_after_resolution_skipped(self) -> None:
        """An entry missing y/y2 after preset resolution is silently skipped."""
        presets = {"strikeout_item": {"canvas": "items", "x": 0.5, "x2": 95}}
        entry = {"type": "strikeout", "presets": ["strikeout_item"]}
        result = _extract_preset_based_field(entry, presets, None, [0])
        assert result is None

    def test_nonexistent_canvas_still_produces_region(self) -> None:
        """Canvas validation happens downstream; a nonexistent canvas still yields a field."""
        presets = {
            "base": {"canvas": "nonexistent_canvas", "x": 0, "y": 0, "x2": 100, "y2": 100},
        }
        entry = {"type": "strikeout", "presets": ["base"]}
        result = _extract_preset_based_field(entry, presets, "test_label", [0])
        assert result is not None
        assert result.parent == "nonexistent_canvas"
