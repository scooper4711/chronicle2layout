"""Unit tests for extended Blueprint parsing with parameters, fields, and styles.

Validates: Requirements 1.1, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.4,
    6.1, 6.8, 7.2, 10.4, 13.5, 13.6
"""

import json
from pathlib import Path

import pytest

from blueprint2layout.blueprint import (
    _merge_field_styles,
    _merge_parameters,
    _parse_field_entry,
    _validate_parameters,
    load_blueprint_with_inheritance,
    parse_blueprint,
)
from blueprint2layout.models import Blueprint, CanvasEntry, FieldEntry


def _write_blueprint(path: Path, data: dict) -> None:
    """Write a Blueprint dict as JSON to the given path."""
    path.write_text(json.dumps(data), encoding="utf-8")


def _minimal_blueprint(bp_id: str, **extras) -> dict:
    """Build a minimal Blueprint JSON dict with optional extras."""
    data: dict = {"id": bp_id, "canvases": [], **extras}
    return data


# ---------------------------------------------------------------------------
# parse_blueprint — new properties
# ---------------------------------------------------------------------------


class TestParseBlueprintParameters:
    """Tests for parse_blueprint with parameters property."""

    def test_valid_parameters_dict_of_dicts(self):
        """Validates: Requirement 1.1 — parameters accepted as dict-of-dicts."""
        data = _minimal_blueprint(
            "bp.params",
            parameters={
                "Event Info": {
                    "event": {"type": "text", "description": "Event name"},
                },
                "Player Info": {
                    "char": {"type": "text", "description": "Character name"},
                },
            },
        )
        result = parse_blueprint(data)

        assert result.parameters is not None
        assert "Event Info" in result.parameters
        assert "Player Info" in result.parameters
        assert result.parameters["Event Info"]["event"]["type"] == "text"

    def test_omitted_parameters_is_none(self):
        """Validates: Requirement 13.6 — omitted parameters stays None."""
        result = parse_blueprint(_minimal_blueprint("bp.no_params"))
        assert result.parameters is None


class TestParseBlueprintDefaultChronicleLocation:
    """Tests for parse_blueprint with defaultChronicleLocation."""

    def test_valid_string(self):
        """Validates: Requirement 3.1 — string defaultChronicleLocation accepted."""
        data = _minimal_blueprint(
            "bp.loc",
            defaultChronicleLocation="modules/pfs2e-chronicles/s5/",
        )
        result = parse_blueprint(data)
        assert result.default_chronicle_location == "modules/pfs2e-chronicles/s5/"

    def test_non_string_raises_error(self):
        """Validates: Requirement 3.4 — non-string raises descriptive error."""
        data = _minimal_blueprint("bp.bad_loc", defaultChronicleLocation=42)
        with pytest.raises(ValueError, match="defaultChronicleLocation.*string"):
            parse_blueprint(data)

    def test_omitted_is_none(self):
        """Validates: Requirement 3.1 — omitted stays None."""
        result = parse_blueprint(_minimal_blueprint("bp.no_loc"))
        assert result.default_chronicle_location is None


class TestParseBlueprintFieldStyles:
    """Tests for parse_blueprint with field_styles."""

    def test_valid_field_styles_dict(self):
        """Validates: Requirement 6.1 — field_styles accepted as dict."""
        data = _minimal_blueprint(
            "bp.styles",
            field_styles={
                "defaultfont": {"font": "Helvetica", "fontsize": 14},
                "bold": {"fontweight": "bold"},
            },
        )
        result = parse_blueprint(data)

        assert result.field_styles is not None
        assert result.field_styles["defaultfont"]["font"] == "Helvetica"
        assert result.field_styles["bold"]["fontweight"] == "bold"

    def test_omitted_is_none(self):
        result = parse_blueprint(_minimal_blueprint("bp.no_styles"))
        assert result.field_styles is None


class TestParseBlueprintFields:
    """Tests for parse_blueprint with fields."""

    def test_valid_fields_list(self):
        """Validates: Requirement 7.2, 13.4 — fields parsed as list of FieldEntry."""
        data = _minimal_blueprint(
            "bp.fields",
            fields=[
                {"name": "char", "type": "text", "canvas": "main", "param": "char"},
                {"name": "xp", "type": "text", "canvas": "main", "param": "xp"},
            ],
        )
        result = parse_blueprint(data)

        assert result.fields is not None
        assert len(result.fields) == 2
        assert result.fields[0].name == "char"
        assert result.fields[1].name == "xp"
        assert isinstance(result.fields[0], FieldEntry)

    def test_omitted_is_none(self):
        result = parse_blueprint(_minimal_blueprint("bp.no_fields"))
        assert result.fields is None


# ---------------------------------------------------------------------------
# _validate_parameters
# ---------------------------------------------------------------------------


class TestValidateParameters:
    """Tests for _validate_parameters validation logic."""

    def test_non_dict_raises_error(self):
        """Validates: Requirement 1.4 — non-dict raises ValueError."""
        with pytest.raises(ValueError, match="dict of dicts"):
            _validate_parameters("not a dict")

    def test_dict_with_non_dict_group_raises_error(self):
        """Validates: Requirement 1.4 — group value must be dict."""
        with pytest.raises(ValueError, match="group.*is.*str"):
            _validate_parameters({"Event Info": "bad"})

    def test_valid_dict_of_dicts_returns_same(self):
        params = {"Group": {"key": {"type": "text"}}}
        result = _validate_parameters(params)
        assert result is params


# ---------------------------------------------------------------------------
# _parse_field_entry
# ---------------------------------------------------------------------------


class TestParseFieldEntry:
    """Tests for _parse_field_entry validation and conversion."""

    def test_missing_name_raises_error(self):
        """Validates: Requirement 7.2 — name is required."""
        with pytest.raises(ValueError, match="missing required field 'name'"):
            _parse_field_entry({"type": "text"})

    def test_non_string_name_raises_error(self):
        """Validates: Requirement 7.2 — name must be a string."""
        with pytest.raises(ValueError, match="'name' must be a string"):
            _parse_field_entry({"name": 123})

    def test_valid_entry_returns_field_entry(self):
        """Validates: Requirement 13.5 — valid entry produces FieldEntry."""
        entry = {"name": "char", "type": "text", "canvas": "main", "param": "char"}
        result = _parse_field_entry(entry)

        assert isinstance(result, FieldEntry)
        assert result.name == "char"
        assert result.type == "text"
        assert result.canvas == "main"
        assert result.param == "char"

    def test_fontsize_must_be_numeric(self):
        """Validates: Requirement 13.5 — property type validation."""
        with pytest.raises(ValueError, match="fontsize.*int or float"):
            _parse_field_entry({"name": "f", "fontsize": "big"})

    def test_lines_must_be_int(self):
        """Validates: Requirement 13.5 — lines must be int, not float."""
        with pytest.raises(ValueError, match="lines.*int"):
            _parse_field_entry({"name": "f", "lines": 3.5})

    def test_styles_list_parsed(self):
        """Validates: Requirement 7.2 — styles array parsed correctly."""
        entry = {"name": "f", "styles": ["base", "bold"]}
        result = _parse_field_entry(entry)
        assert result.styles == ["base", "bold"]

    def test_edge_properties_accepted(self):
        """Validates: Requirement 7.2 — edge values stored as-is."""
        entry = {
            "name": "f",
            "left": "main.left",
            "right": 95.5,
            "top": 0,
            "bottom": "h_bar[2]",
        }
        result = _parse_field_entry(entry)
        assert result.left == "main.left"
        assert result.right == pytest.approx(95.5)
        assert result.top == 0
        assert result.bottom == "h_bar[2]"

    def test_boolean_edge_rejected(self):
        """Validates: Requirement 13.5 — booleans are not valid edge types."""
        with pytest.raises(ValueError, match="left.*int or float or str"):
            _parse_field_entry({"name": "f", "left": True})


# ---------------------------------------------------------------------------
# _merge_parameters
# ---------------------------------------------------------------------------


class TestMergeParameters:
    """Tests for _merge_parameters merging logic."""

    def test_parent_only_groups_preserved(self):
        """Validates: Requirement 2.1 — parent-only groups included."""
        parent = {"Player Info": {"char": {"type": "text"}}}
        child: dict = {}
        result = _merge_parameters(parent, child)

        assert "Player Info" in result
        assert result["Player Info"]["char"]["type"] == "text"

    def test_child_only_groups_added(self):
        """Validates: Requirement 2.2 — child-only groups added."""
        parent: dict = {}
        child = {"Rewards": {"xp": {"type": "text"}}}
        result = _merge_parameters(parent, child)

        assert "Rewards" in result
        assert result["Rewards"]["xp"]["type"] == "text"

    def test_shared_groups_child_overrides(self):
        """Validates: Requirement 2.3 — child overrides parent in shared groups."""
        parent = {
            "Event Info": {
                "event": {"type": "text", "description": "Parent event"},
                "date": {"type": "text", "description": "Date"},
            },
        }
        child = {
            "Event Info": {
                "event": {"type": "text", "description": "Child event"},
            },
        }
        result = _merge_parameters(parent, child)

        assert result["Event Info"]["event"]["description"] == "Child event"
        assert result["Event Info"]["date"]["description"] == "Date"

    def test_both_none_returns_none(self):
        """Validates: Requirement 2.4 — both None yields None."""
        assert _merge_parameters(None, None) is None

    def test_parent_none_returns_child(self):
        child = {"G": {"k": {}}}
        assert _merge_parameters(None, child) == child

    def test_child_none_returns_parent(self):
        parent = {"G": {"k": {}}}
        assert _merge_parameters(parent, None) == parent


# ---------------------------------------------------------------------------
# _merge_field_styles
# ---------------------------------------------------------------------------


class TestMergeFieldStyles:
    """Tests for _merge_field_styles merging logic."""

    def test_child_overrides_parent_same_name(self):
        """Validates: Requirement 6.8 — child definition wins for same name."""
        parent = {"bold": {"fontweight": "bold", "fontsize": 12}}
        child = {"bold": {"fontweight": "bold", "fontsize": 14}}
        result = _merge_field_styles(parent, child)

        assert result["bold"]["fontsize"] == 14

    def test_both_none_returns_none(self):
        assert _merge_field_styles(None, None) is None

    def test_parent_none_returns_child(self):
        child = {"s": {"font": "Arial"}}
        assert _merge_field_styles(None, child) == child

    def test_child_none_returns_parent(self):
        parent = {"s": {"font": "Arial"}}
        assert _merge_field_styles(parent, None) == parent

    def test_disjoint_styles_merged(self):
        """Both parent-only and child-only styles appear in result."""
        parent = {"base": {"font": "Helvetica"}}
        child = {"bold": {"fontweight": "bold"}}
        result = _merge_field_styles(parent, child)

        assert "base" in result
        assert "bold" in result


# ---------------------------------------------------------------------------
# Field name uniqueness across inheritance
# ---------------------------------------------------------------------------


class TestFieldNameUniqueness:
    """Tests for duplicate field name detection across inheritance."""

    def test_duplicate_field_name_raises_error(self, tmp_path: Path):
        """Validates: Requirement 10.4 — duplicate field name across chain."""
        parent_data = {
            "id": "parent.bp",
            "canvases": [
                {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
            ],
            "fields": [{"name": "char", "type": "text", "canvas": "page"}],
        }
        child_data = {
            "id": "child.bp",
            "parent": "parent.bp",
            "canvases": [
                {
                    "name": "main",
                    "parent": "page",
                    "left": 5,
                    "right": 95,
                    "top": 5,
                    "bottom": 95,
                },
            ],
            "fields": [{"name": "char", "type": "text", "canvas": "main"}],
        }
        _write_blueprint(tmp_path / "parent.json", parent_data)
        _write_blueprint(tmp_path / "child.json", child_data)

        from blueprint2layout.blueprint import build_blueprint_index

        index = build_blueprint_index(tmp_path)

        with pytest.raises(ValueError, match="[Dd]uplicate field name.*char"):
            load_blueprint_with_inheritance(tmp_path / "child.json", index)


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Tests that canvas-only Blueprints parse identically to before."""

    def test_canvas_only_blueprint_unchanged(self):
        """Validates: Requirement 13.6 — no new fields when not declared."""
        data = {
            "id": "legacy.bp",
            "canvases": [
                {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
            ],
        }
        result = parse_blueprint(data)

        assert result.id == "legacy.bp"
        assert len(result.canvases) == 1
        assert result.parameters is None
        assert result.default_chronicle_location is None
        assert result.field_styles is None
        assert result.fields is None

    def test_canvas_only_inheritance_returns_none_params_styles(self, tmp_path: Path):
        """Validates: Requirement 13.6 — inheritance with no new properties."""
        parent_data = {
            "id": "parent.bp",
            "canvases": [
                {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
            ],
        }
        child_data = {
            "id": "child.bp",
            "parent": "parent.bp",
            "canvases": [
                {
                    "name": "main",
                    "parent": "page",
                    "left": 5,
                    "right": 95,
                    "top": 5,
                    "bottom": 95,
                },
            ],
        }
        _write_blueprint(tmp_path / "parent.json", parent_data)
        _write_blueprint(tmp_path / "child.json", child_data)

        from blueprint2layout.blueprint import build_blueprint_index

        index = build_blueprint_index(tmp_path)
        _, _, merged_params, merged_styles, _ = load_blueprint_with_inheritance(
            tmp_path / "child.json", index,
        )

        assert merged_params is None
        assert merged_styles is None
