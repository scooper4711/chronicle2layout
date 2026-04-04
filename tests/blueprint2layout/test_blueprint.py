"""Unit tests for blueprint parsing."""

import pytest

from blueprint2layout.blueprint import parse_blueprint
from blueprint2layout.models import Blueprint, CanvasEntry


class TestParseBlueprint:
    """Tests for parse_blueprint."""

    def test_valid_blueprint_with_numeric_edges(self):
        data = {
            "id": "test.blueprint",
            "canvases": [
                {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
            ],
        }
        result = parse_blueprint(data)
        assert result == Blueprint(
            id="test.blueprint",
            canvases=[CanvasEntry(name="page", left=0, right=100, top=0, bottom=100)],
            parent=None,
        )

    def test_valid_blueprint_with_string_edges(self):
        data = {
            "id": "child.blueprint",
            "parent": "parent.blueprint",
            "canvases": [
                {
                    "name": "summary",
                    "parent": "main",
                    "left": "main.left",
                    "right": "main.right",
                    "top": "h_bar[0]",
                    "bottom": "h_bar[1]",
                },
            ],
        }
        result = parse_blueprint(data)
        assert result.id == "child.blueprint"
        assert result.parent == "parent.blueprint"
        assert len(result.canvases) == 1
        assert result.canvases[0].name == "summary"
        assert result.canvases[0].parent == "main"
        assert result.canvases[0].left == "main.left"
        assert result.canvases[0].top == "h_bar[0]"

    def test_valid_blueprint_with_float_edges(self):
        data = {
            "id": "float.blueprint",
            "canvases": [
                {"name": "box", "left": 1.5, "right": 98.5, "top": 2.0, "bottom": 97.0},
            ],
        }
        result = parse_blueprint(data)
        assert result.canvases[0].left == 1.5
        assert result.canvases[0].right == 98.5

    def test_valid_blueprint_with_mixed_edge_types(self):
        data = {
            "id": "mixed.blueprint",
            "canvases": [
                {"name": "canvas", "left": 0, "right": "v_thin[0]", "top": 5.5, "bottom": "h_bar[2]"},
            ],
        }
        result = parse_blueprint(data)
        canvas = result.canvases[0]
        assert canvas.left == 0
        assert canvas.right == "v_thin[0]"
        assert canvas.top == 5.5
        assert canvas.bottom == "h_bar[2]"

    def test_multiple_canvases(self):
        data = {
            "id": "multi.blueprint",
            "canvases": [
                {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
                {"name": "main", "parent": "page", "left": 5, "right": 95, "top": 10, "bottom": 90},
            ],
        }
        result = parse_blueprint(data)
        assert len(result.canvases) == 2
        assert result.canvases[0].name == "page"
        assert result.canvases[1].name == "main"
        assert result.canvases[1].parent == "page"

    def test_empty_canvases_list(self):
        data = {"id": "empty.blueprint", "canvases": []}
        result = parse_blueprint(data)
        assert result.canvases == []

    def test_canvas_without_parent(self):
        data = {
            "id": "no-parent.blueprint",
            "canvases": [
                {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
            ],
        }
        result = parse_blueprint(data)
        assert result.canvases[0].parent is None

    def test_missing_id_raises_error(self):
        data = {"canvases": []}
        with pytest.raises(ValueError, match="missing required field 'id'"):
            parse_blueprint(data)

    def test_missing_canvases_raises_error(self):
        data = {"id": "test.blueprint"}
        with pytest.raises(ValueError, match="missing required field 'canvases'"):
            parse_blueprint(data)

    def test_non_dict_data_raises_error(self):
        with pytest.raises(ValueError, match="must be a dict"):
            parse_blueprint("not a dict")

    def test_non_string_id_raises_error(self):
        data = {"id": 123, "canvases": []}
        with pytest.raises(ValueError, match="'id' must be a string"):
            parse_blueprint(data)

    def test_non_list_canvases_raises_error(self):
        data = {"id": "test", "canvases": "not a list"}
        with pytest.raises(ValueError, match="'canvases' must be a list"):
            parse_blueprint(data)

    def test_non_string_parent_raises_error(self):
        data = {"id": "test", "parent": 42, "canvases": []}
        with pytest.raises(ValueError, match="'parent' must be a string or null"):
            parse_blueprint(data)

    def test_canvas_missing_name_raises_error(self):
        data = {
            "id": "test",
            "canvases": [{"left": 0, "right": 100, "top": 0, "bottom": 100}],
        }
        with pytest.raises(ValueError, match="missing required field 'name'"):
            parse_blueprint(data)

    def test_canvas_missing_edge_raises_error(self):
        data = {
            "id": "test",
            "canvases": [{"name": "page", "left": 0, "right": 100, "top": 0}],
        }
        with pytest.raises(ValueError, match="missing required edge 'bottom'"):
            parse_blueprint(data)

    def test_canvas_invalid_edge_type_raises_error(self):
        data = {
            "id": "test",
            "canvases": [
                {"name": "page", "left": [1, 2], "right": 100, "top": 0, "bottom": 100},
            ],
        }
        with pytest.raises(ValueError, match="must be int, float, or str"):
            parse_blueprint(data)

    def test_canvas_non_dict_entry_raises_error(self):
        data = {"id": "test", "canvases": ["not a dict"]}
        with pytest.raises(ValueError, match="Canvas entry must be a dict"):
            parse_blueprint(data)

    def test_canvas_non_string_name_raises_error(self):
        data = {
            "id": "test",
            "canvases": [
                {"name": 42, "left": 0, "right": 100, "top": 0, "bottom": 100},
            ],
        }
        with pytest.raises(ValueError, match="'name' must be a string"):
            parse_blueprint(data)

    def test_canvas_non_string_parent_raises_error(self):
        data = {
            "id": "test",
            "canvases": [
                {"name": "page", "parent": 99, "left": 0, "right": 100, "top": 0, "bottom": 100},
            ],
        }
        with pytest.raises(ValueError, match="parent must be a string or null"):
            parse_blueprint(data)

    def test_edge_value_none_raises_error(self):
        data = {
            "id": "test",
            "canvases": [
                {"name": "page", "left": None, "right": 100, "top": 0, "bottom": 100},
            ],
        }
        with pytest.raises(ValueError, match="must be int, float, or str"):
            parse_blueprint(data)

    def test_edge_value_bool_raises_error(self):
        data = {
            "id": "test",
            "canvases": [
                {"name": "page", "left": True, "right": 100, "top": 0, "bottom": 100},
            ],
        }
        with pytest.raises(ValueError, match="must be int, float, or str"):
            parse_blueprint(data)

import json
from pathlib import Path

from blueprint2layout.blueprint import build_blueprint_index, load_blueprint_with_inheritance
from blueprint2layout.models import CanvasEntry


def _write_blueprint_json(path: Path, data: dict) -> None:
    """Write a Blueprint dict as JSON to the given path."""
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_blueprint_data(
    bp_id: str,
    parent: str | None = None,
    canvases: list[dict] | None = None,
) -> dict:
    """Build a minimal Blueprint JSON dict."""
    data: dict = {"id": bp_id, "canvases": canvases or []}
    if parent is not None:
        data["parent"] = parent
    return data


class TestBuildBlueprintIndex:
    """Tests for build_blueprint_index."""

    def test_index_single_file(self, tmp_path: Path):
        data = {"id": "test.bp", "canvases": []}
        _write_blueprint_json(tmp_path / "test.json", data)

        index = build_blueprint_index(tmp_path)

        assert len(index) == 1
        assert "test.bp" in index
        assert index["test.bp"] == tmp_path / "test.json"

    def test_index_multiple_files(self, tmp_path: Path):
        _write_blueprint_json(tmp_path / "a.json", {"id": "alpha.bp", "canvases": []})
        _write_blueprint_json(tmp_path / "b.json", {"id": "beta.bp", "canvases": []})

        index = build_blueprint_index(tmp_path)

        assert len(index) == 2
        assert "alpha.bp" in index
        assert "beta.bp" in index

    def test_index_skips_invalid_json(self, tmp_path: Path):
        (tmp_path / "bad.json").write_text("not valid json {{{", encoding="utf-8")

        index = build_blueprint_index(tmp_path)

        assert index == {}

    def test_index_skips_file_without_id(self, tmp_path: Path):
        _write_blueprint_json(tmp_path / "no_id.json", {"canvases": []})

        index = build_blueprint_index(tmp_path)

        assert index == {}

    def test_index_empty_directory(self, tmp_path: Path):
        index = build_blueprint_index(tmp_path)

        assert index == {}

    def test_index_recursive(self, tmp_path: Path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        _write_blueprint_json(sub / "nested.json", {"id": "nested.bp", "canvases": []})

        index = build_blueprint_index(tmp_path)

        assert len(index) == 1
        assert "nested.bp" in index
        assert index["nested.bp"] == sub / "nested.json"


class TestLoadBlueprintNoParent:
    """Tests for load_blueprint_with_inheritance with no parent."""

    def test_load_single_blueprint(self, tmp_path: Path):
        data = _make_blueprint_data("solo.bp", canvases=[
            {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
        ])
        bp_path = tmp_path / "solo.json"
        _write_blueprint_json(bp_path, data)

        blueprint, inherited, merged_params, merged_styles, _ = load_blueprint_with_inheritance(bp_path, {})

        assert blueprint.id == "solo.bp"
        assert blueprint.parent is None
        assert len(blueprint.canvases) == 1
        assert blueprint.canvases[0].name == "page"
        assert inherited == []
        assert merged_params is None
        assert merged_styles is None


class TestLoadBlueprintWithParent:
    """Tests for load_blueprint_with_inheritance with a parent-child chain."""

    def test_load_parent_child_chain(self, tmp_path: Path):
        parent_data = _make_blueprint_data("parent.bp", canvases=[
            {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
        ])
        child_data = _make_blueprint_data("child.bp", parent="parent.bp", canvases=[
            {"name": "summary", "parent": "page", "left": 5, "right": 95, "top": 10, "bottom": 90},
        ])
        parent_path = tmp_path / "parent.json"
        child_path = tmp_path / "child.json"
        _write_blueprint_json(parent_path, parent_data)
        _write_blueprint_json(child_path, child_data)

        index = build_blueprint_index(tmp_path)
        blueprint, inherited, _, _, _ = load_blueprint_with_inheritance(child_path, index)

        assert blueprint.id == "child.bp"
        assert blueprint.parent == "parent.bp"
        assert len(blueprint.canvases) == 1
        assert blueprint.canvases[0].name == "summary"

        assert len(inherited) == 1
        assert inherited[0].name == "page"
        assert inherited[0] == CanvasEntry(
            name="page", left=0, right=100, top=0, bottom=100,
        )


class TestLoadBlueprintGrandparentChain:
    """Tests for load_blueprint_with_inheritance with a three-level chain."""

    def test_load_three_level_chain(self, tmp_path: Path):
        root_data = _make_blueprint_data("root.bp", canvases=[
            {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
        ])
        mid_data = _make_blueprint_data("mid.bp", parent="root.bp", canvases=[
            {"name": "main", "parent": "page", "left": 5, "right": 95, "top": 5, "bottom": 95},
        ])
        leaf_data = _make_blueprint_data("leaf.bp", parent="mid.bp", canvases=[
            {"name": "detail", "parent": "main", "left": 10, "right": 90, "top": 10, "bottom": 90},
        ])
        _write_blueprint_json(tmp_path / "root.json", root_data)
        _write_blueprint_json(tmp_path / "mid.json", mid_data)
        _write_blueprint_json(tmp_path / "leaf.json", leaf_data)

        index = build_blueprint_index(tmp_path)
        blueprint, inherited, _, _, _ = load_blueprint_with_inheritance(
            tmp_path / "leaf.json", index,
        )

        assert blueprint.id == "leaf.bp"
        assert len(inherited) == 2
        # Root-first order: root's canvas first, then mid's canvas
        assert inherited[0].name == "page"
        assert inherited[1].name == "main"


class TestLoadBlueprintCircularReference:
    """Tests for circular parent reference detection."""

    def test_circular_reference_raises_error(self, tmp_path: Path):
        a_data = _make_blueprint_data("a.bp", parent="b.bp", canvases=[
            {"name": "canvas_a", "left": 0, "right": 100, "top": 0, "bottom": 100},
        ])
        b_data = _make_blueprint_data("b.bp", parent="a.bp", canvases=[
            {"name": "canvas_b", "left": 0, "right": 100, "top": 0, "bottom": 100},
        ])
        _write_blueprint_json(tmp_path / "a.json", a_data)
        _write_blueprint_json(tmp_path / "b.json", b_data)

        index = build_blueprint_index(tmp_path)

        with pytest.raises(ValueError, match="[Cc]ircular"):
            load_blueprint_with_inheritance(tmp_path / "a.json", index)


class TestLoadBlueprintDuplicateCanvasName:
    """Tests for duplicate canvas name detection across inheritance."""

    def test_duplicate_canvas_name_raises_error(self, tmp_path: Path):
        parent_data = _make_blueprint_data("parent.bp", canvases=[
            {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
        ])
        child_data = _make_blueprint_data("child.bp", parent="parent.bp", canvases=[
            {"name": "page", "left": 5, "right": 95, "top": 5, "bottom": 95},
        ])
        _write_blueprint_json(tmp_path / "parent.json", parent_data)
        _write_blueprint_json(tmp_path / "child.json", child_data)

        index = build_blueprint_index(tmp_path)

        with pytest.raises(ValueError, match="[Dd]uplicate canvas name.*page"):
            load_blueprint_with_inheritance(tmp_path / "child.json", index)


class TestLoadBlueprintUnknownParent:
    """Tests for unknown parent id detection."""

    def test_unknown_parent_raises_error(self, tmp_path: Path):
        child_data = _make_blueprint_data("child.bp", parent="nonexistent.bp", canvases=[
            {"name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100},
        ])
        _write_blueprint_json(tmp_path / "child.json", child_data)

        index = build_blueprint_index(tmp_path)

        with pytest.raises(ValueError, match="[Uu]nknown parent"):
            load_blueprint_with_inheritance(tmp_path / "child.json", index)
