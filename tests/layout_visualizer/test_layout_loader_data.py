"""Unit tests for data-mode layout loading functions.

Tests cover merge_parameters, merge_presets, resolve_entry_presets,
and load_data_content including edge cases and warning paths.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3,
              7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.1, 9.2, 9.3
"""

import json
import logging
from pathlib import Path

import pytest

from layout_visualizer.layout_loader import (
    build_layout_index,
    load_data_content,
    merge_parameters,
    merge_presets,
    resolve_entry_presets,
)
from layout_visualizer.models import DataContentEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_layout(path: Path, data: dict) -> Path:
    """Write a layout dict as JSON to the given path."""
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _make_chain(layouts: list[dict]) -> list[tuple[Path, dict]]:
    """Build a fake chain from a list of layout dicts (no real files)."""
    return [(Path(f"/fake/{i}.json"), data) for i, data in enumerate(layouts)]


# ---------------------------------------------------------------------------
# merge_parameters
# ---------------------------------------------------------------------------

class TestMergeParameters:
    """Tests for merge_parameters."""

    def test_single_layout_flattens_groups(self) -> None:
        """Parameters from different groups are flattened into one dict."""
        chain = _make_chain([{
            "parameters": {
                "Group A": {"p1": {"type": "text", "example": "a"}},
                "Group B": {"p2": {"type": "text", "example": "b"}},
            },
        }])

        result = merge_parameters(chain)

        assert "p1" in result
        assert "p2" in result
        assert result["p1"]["example"] == "a"

    def test_two_layout_chain_child_overrides(self) -> None:
        """Child definition overrides parent for the same parameter name."""
        chain = _make_chain([
            {"parameters": {"G": {"p1": {"type": "text", "example": "parent"}}}},
            {"parameters": {"G": {"p1": {"type": "text", "example": "child"}}}},
        ])

        result = merge_parameters(chain)

        assert result["p1"]["example"] == "child"

    def test_parameter_in_different_groups(self) -> None:
        """A child can override a parameter even if it's in a different group."""
        chain = _make_chain([
            {"parameters": {"Group A": {"p1": {"type": "text", "example": "old"}}}},
            {"parameters": {"Group Z": {"p1": {"type": "text", "example": "new"}}}},
        ])

        result = merge_parameters(chain)

        assert result["p1"]["example"] == "new"

    def test_empty_parameters(self) -> None:
        """A layout with no parameters section produces an empty dict."""
        chain = _make_chain([{"id": "empty"}])

        result = merge_parameters(chain)

        assert result == {}


# ---------------------------------------------------------------------------
# merge_presets
# ---------------------------------------------------------------------------

class TestMergePresets:
    """Tests for merge_presets."""

    def test_single_layout(self) -> None:
        """Presets from a single layout are returned as-is."""
        chain = _make_chain([{
            "presets": {"defaultfont": {"font": "Helvetica", "fontsize": 14}},
        }])

        result = merge_presets(chain)

        assert result["defaultfont"]["font"] == "Helvetica"

    def test_chain_with_override(self) -> None:
        """Child preset overrides parent preset with the same name."""
        chain = _make_chain([
            {"presets": {"style": {"font": "Courier", "fontsize": 10}}},
            {"presets": {"style": {"font": "Arial", "fontsize": 12}}},
        ])

        result = merge_presets(chain)

        assert result["style"]["font"] == "Arial"
        assert result["style"]["fontsize"] == 12

    def test_parent_only_presets_preserved(self) -> None:
        """Presets defined only in the parent survive the merge."""
        chain = _make_chain([
            {"presets": {"base": {"font": "Helvetica"}}},
            {"presets": {"extra": {"fontsize": 8}}},
        ])

        result = merge_presets(chain)

        assert "base" in result
        assert "extra" in result


# ---------------------------------------------------------------------------
# resolve_entry_presets
# ---------------------------------------------------------------------------

class TestResolveEntryPresets:
    """Tests for resolve_entry_presets."""

    def test_entry_with_no_presets(self) -> None:
        """An entry without presets returns its own properties."""
        entry = {"type": "text", "font": "Courier", "fontsize": 10}

        result = resolve_entry_presets(entry, {})

        assert result["font"] == "Courier"
        assert result["fontsize"] == 10

    def test_entry_with_one_preset(self) -> None:
        """Preset properties are applied as defaults."""
        presets = {"base": {"font": "Helvetica", "fontsize": 14}}
        entry = {"type": "text", "presets": ["base"]}

        result = resolve_entry_presets(entry, presets)

        assert result["font"] == "Helvetica"
        assert result["fontsize"] == 14
        assert result["type"] == "text"

    def test_nested_presets(self) -> None:
        """Nested preset references are resolved depth-first."""
        presets = {
            "grandparent": {"font": "Courier", "fontsize": 8},
            "parent_preset": {"presets": ["grandparent"], "fontsize": 12},
        }
        entry = {"type": "text", "presets": ["parent_preset"]}

        result = resolve_entry_presets(entry, presets)

        assert result["font"] == "Courier"
        assert result["fontsize"] == 12

    def test_inline_override(self) -> None:
        """Inline entry properties override preset values."""
        presets = {"base": {"font": "Helvetica", "fontsize": 14, "align": "LB"}}
        entry = {"type": "text", "presets": ["base"], "fontsize": 10}

        result = resolve_entry_presets(entry, presets)

        assert result["font"] == "Helvetica"
        assert result["fontsize"] == 10
        assert result["align"] == "LB"

    def test_multiple_presets_later_wins(self) -> None:
        """When multiple presets are listed, later ones override earlier."""
        presets = {
            "a": {"font": "Courier", "fontsize": 8},
            "b": {"font": "Arial"},
        }
        entry = {"type": "text", "presets": ["a", "b"]}

        result = resolve_entry_presets(entry, presets)

        assert result["font"] == "Arial"
        assert result["fontsize"] == 8


# ---------------------------------------------------------------------------
# load_data_content
# ---------------------------------------------------------------------------

class TestLoadDataContent:
    """Tests for load_data_content with real layout files on disk."""

    def _write_single_layout(
        self,
        tmp_path: Path,
        *,
        parameters: dict | None = None,
        content: list | None = None,
        presets: dict | None = None,
        canvas: dict | None = None,
    ) -> tuple[Path, dict[str, Path]]:
        """Write a single layout file and return (path, index)."""
        data: dict = {
            "id": "test_layout",
            "canvas": canvas or {
                "page": {"x": 0, "y": 0, "x2": 100, "y2": 100},
            },
        }
        if parameters is not None:
            data["parameters"] = parameters
        if content is not None:
            data["content"] = content
        if presets is not None:
            data["presets"] = presets

        layout_path = write_layout(tmp_path / "layout.json", data)
        index = build_layout_index(tmp_path)
        return layout_path, index

    def test_text_entry_extraction(self, tmp_path: Path) -> None:
        """A text entry with a valid parameter produces a DataContentEntry."""
        path, index = self._write_single_layout(
            tmp_path,
            parameters={"G": {"name": {"type": "text", "example": "Alice"}}},
            content=[{
                "value": "param:name",
                "type": "text",
                "canvas": "page",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 14,
                "align": "LB",
            }],
        )

        entries, _, _, _, canvases, paths = load_data_content(path, index)

        assert len(entries) == 1
        assert entries[0].param_name == "name"
        assert entries[0].example_value == "Alice"
        assert entries[0].entry_type == "text"
        assert entries[0].canvas == "page"

    def test_multiline_entry_extraction(self, tmp_path: Path) -> None:
        """A multiline entry preserves the lines count."""
        path, index = self._write_single_layout(
            tmp_path,
            parameters={"G": {"notes": {
                "type": "multiline", "example": "Note text", "lines": 4,
            }}},
            content=[{
                "value": "param:notes",
                "type": "multiline",
                "canvas": "page",
                "x": 0, "y": 0, "x2": 100, "y2": 50,
                "font": "Helvetica", "fontsize": 11,
                "align": "LB", "lines": 4,
            }],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert len(entries) == 1
        assert entries[0].entry_type == "multiline"
        assert entries[0].lines == 4

    def test_skip_checkbox(self, tmp_path: Path) -> None:
        """Checkbox entries are skipped."""
        path, index = self._write_single_layout(
            tmp_path,
            parameters={"G": {"cb": {"type": "choice", "example": "1"}}},
            content=[{"type": "checkbox", "canvas": "page", "x": 0, "y": 0, "x2": 5, "y2": 5}],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []

    def test_skip_strikeout(self, tmp_path: Path) -> None:
        """Strikeout entries are skipped."""
        path, index = self._write_single_layout(
            tmp_path,
            content=[{"type": "strikeout", "canvas": "page", "x": 0, "y": 0, "x2": 100, "y2": 5}],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []

    def test_skip_line(self, tmp_path: Path) -> None:
        """Line entries are skipped."""
        path, index = self._write_single_layout(
            tmp_path,
            content=[{"type": "line", "canvas": "page", "x": 0, "y": 50, "x2": 100, "y2": 50}],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []

    def test_skip_rectangle(self, tmp_path: Path) -> None:
        """Rectangle entries are skipped."""
        path, index = self._write_single_layout(
            tmp_path,
            content=[{"type": "rectangle", "canvas": "page", "x": 0, "y": 0, "x2": 50, "y2": 50}],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []

    def test_trigger_nesting(self, tmp_path: Path) -> None:
        """Text entries nested inside a trigger are extracted."""
        path, index = self._write_single_layout(
            tmp_path,
            parameters={"G": {"val": {"type": "text", "example": "triggered"}}},
            content=[{
                "type": "trigger",
                "trigger": "some_param",
                "content": [{
                    "value": "param:val",
                    "type": "text",
                    "canvas": "page",
                    "x": 0, "y": 0, "x2": 50, "y2": 10,
                    "font": "Helvetica", "fontsize": 12, "align": "LB",
                }],
            }],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert len(entries) == 1
        assert entries[0].example_value == "triggered"

    def test_choice_nesting(self, tmp_path: Path) -> None:
        """Text entries nested inside choice branches are extracted."""
        path, index = self._write_single_layout(
            tmp_path,
            parameters={"G": {"item": {"type": "text", "example": "sword"}}},
            content=[{
                "type": "choice",
                "choices": "some_param",
                "content": {
                    "option_a": [{
                        "value": "param:item",
                        "type": "text",
                        "canvas": "page",
                        "x": 0, "y": 0, "x2": 50, "y2": 10,
                        "font": "Helvetica", "fontsize": 12, "align": "LB",
                    }],
                },
            }],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert len(entries) == 1
        assert entries[0].example_value == "sword"


# ---------------------------------------------------------------------------
# Example value loading
# ---------------------------------------------------------------------------

class TestExampleValueLoading:
    """Tests for example value stringification and warning paths."""

    def test_string_example(self, tmp_path: Path) -> None:
        """A string example value is used as-is."""
        path, index = TestLoadDataContent()._write_single_layout(
            tmp_path,
            parameters={"G": {"name": {"type": "text", "example": "Alice"}}},
            content=[{
                "value": "param:name", "type": "text", "canvas": "page",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 12, "align": "LB",
            }],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries[0].example_value == "Alice"

    def test_integer_example(self, tmp_path: Path) -> None:
        """An integer example value is converted to string."""
        path, index = TestLoadDataContent()._write_single_layout(
            tmp_path,
            parameters={"G": {"xp": {"type": "text", "example": 42}}},
            content=[{
                "value": "param:xp", "type": "text", "canvas": "page",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 12, "align": "LB",
            }],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries[0].example_value == "42"

    def test_float_example(self, tmp_path: Path) -> None:
        """A float example value is converted to string."""
        path, index = TestLoadDataContent()._write_single_layout(
            tmp_path,
            parameters={"G": {"gp": {"type": "text", "example": 1.8}}},
            content=[{
                "value": "param:gp", "type": "text", "canvas": "page",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 12, "align": "LB",
            }],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries[0].example_value == "1.8"

    def test_missing_parameter_warns(self, tmp_path: Path, caplog) -> None:
        """A reference to a nonexistent parameter logs a warning."""
        path, index = TestLoadDataContent()._write_single_layout(
            tmp_path,
            parameters={"G": {}},
            content=[{
                "value": "param:missing", "type": "text", "canvas": "page",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 12, "align": "LB",
            }],
        )

        with caplog.at_level(logging.WARNING):
            entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []
        assert "missing" in caplog.text

    def test_missing_example_field_warns(self, tmp_path: Path, caplog) -> None:
        """A parameter without an example field logs a warning."""
        path, index = TestLoadDataContent()._write_single_layout(
            tmp_path,
            parameters={"G": {"name": {"type": "text", "description": "No example"}}},
            content=[{
                "value": "param:name", "type": "text", "canvas": "page",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 12, "align": "LB",
            }],
        )

        with caplog.at_level(logging.WARNING):
            entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []
        assert "name" in caplog.text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases in load_data_content."""

    def test_empty_content_array(self, tmp_path: Path) -> None:
        """An empty content array produces no entries."""
        path, index = TestLoadDataContent()._write_single_layout(
            tmp_path,
            parameters={"G": {"p": {"type": "text", "example": "x"}}},
            content=[],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []

    def test_empty_parameters(self, tmp_path: Path) -> None:
        """No parameters section produces no entries (all refs fail)."""
        path, index = TestLoadDataContent()._write_single_layout(
            tmp_path,
            content=[{
                "value": "param:anything", "type": "text", "canvas": "page",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 12, "align": "LB",
            }],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []

    def test_entry_referencing_nonexistent_canvas(self, tmp_path: Path) -> None:
        """An entry referencing a canvas not in the layout is skipped."""
        path, index = TestLoadDataContent()._write_single_layout(
            tmp_path,
            parameters={"G": {"p": {"type": "text", "example": "val"}}},
            content=[{
                "value": "param:p", "type": "text", "canvas": "nonexistent",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 12, "align": "LB",
            }],
        )

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []

    def test_no_content_key(self, tmp_path: Path) -> None:
        """A layout with no content key produces no entries."""
        path, index = TestLoadDataContent()._write_single_layout(tmp_path)

        entries, _, _, _, _, _ = load_data_content(path, index)

        assert entries == []
