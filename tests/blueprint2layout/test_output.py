"""Unit tests for layout assembly and JSON output.

Tests assemble_layout and write_layout from blueprint2layout.output,
verifying canvas scoping (target-only, not inherited), parent id
inclusion, coordinate values, JSON formatting, and round-trip
consistency.

Validates: Requirements 12.1–12.8, 14.1, 14.2, 14.3
"""

import json

import pytest

from blueprint2layout.models import Blueprint, CanvasEntry, ResolvedCanvas
from blueprint2layout.output import assemble_layout, write_layout


def test_assemble_layout_includes_only_target_canvases():
    """Layout canvas section contains only the target Blueprint's canvases."""
    blueprint = Blueprint(
        id="child.bp",
        canvases=[
            CanvasEntry(name="summary", left=10.0, right=90.0, top=30.0, bottom=60.0),
        ],
        parent="parent.bp",
    )
    resolved = {
        "page": ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
        "summary": ResolvedCanvas(name="summary", left=10.0, right=90.0, top=30.0, bottom=60.0),
    }

    layout = assemble_layout(blueprint, resolved, resolved)

    assert "summary" in layout["canvas"]
    assert "page" not in layout["canvas"]
    assert len(layout["canvas"]) == 1


def test_assemble_layout_includes_parent_id():
    """Layout includes 'parent' key when Blueprint has a parent."""
    blueprint = Blueprint(
        id="child.bp",
        canvases=[
            CanvasEntry(name="detail", left=0.0, right=100.0, top=0.0, bottom=100.0),
        ],
        parent="parent.bp",
    )
    resolved = {
        "detail": ResolvedCanvas(name="detail", left=0.0, right=100.0, top=0.0, bottom=100.0),
    }

    layout = assemble_layout(blueprint, resolved, resolved)

    assert layout["parent"] == "parent.bp"


def test_assemble_layout_no_parent_id():
    """Layout does NOT include 'parent' key when Blueprint has no parent."""
    blueprint = Blueprint(
        id="root.bp",
        canvases=[
            CanvasEntry(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
        ],
    )
    resolved = {
        "page": ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
    }

    layout = assemble_layout(blueprint, resolved, resolved)

    assert "parent" not in layout
    assert layout["id"] == "root.bp"


def test_assemble_layout_canvas_coordinates():
    """Canvas entries have correct x, y, x2, y2 values from conversion."""
    blueprint = Blueprint(
        id="test.bp",
        canvases=[
            CanvasEntry(
                name="inner",
                left=25.0,
                right=75.0,
                top=10.0,
                bottom=50.0,
                parent="page",
            ),
        ],
    )
    page = ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0)
    inner = ResolvedCanvas(
        name="inner", left=25.0, right=75.0, top=10.0, bottom=50.0, parent="page"
    )
    resolved = {"page": page, "inner": inner}

    layout = assemble_layout(blueprint, resolved, resolved)

    canvas = layout["canvas"]["inner"]
    assert canvas["x"] == 25.0
    assert canvas["y"] == 10.0
    assert canvas["x2"] == 75.0
    assert canvas["y2"] == 50.0
    assert canvas["parent"] == "page"


def test_write_layout_valid_json(tmp_path):
    """write_layout produces a file that json.loads can parse."""
    layout = {
        "id": "test.bp",
        "canvas": {
            "page": {"x": 0.0, "y": 0.0, "x2": 100.0, "y2": 100.0},
        },
    }
    output_file = tmp_path / "layout.json"

    write_layout(layout, output_file)

    parsed = json.loads(output_file.read_text())
    assert parsed["id"] == "test.bp"
    assert parsed["canvas"]["page"]["x"] == 0.0


def test_write_layout_two_space_indent(tmp_path):
    """write_layout uses 2-space indentation in the JSON output."""
    layout = {
        "id": "test.bp",
        "canvas": {
            "page": {"x": 0.0, "y": 0.0, "x2": 100.0, "y2": 100.0},
        },
    }
    output_file = tmp_path / "layout.json"

    write_layout(layout, output_file)

    raw_text = output_file.read_text()
    lines = raw_text.splitlines()
    indented_lines = [line for line in lines if line.startswith("  ")]
    assert len(indented_lines) > 0
    # No lines should use 4-space indent without a preceding 2-space level
    for line in lines:
        stripped = line.lstrip(" ")
        indent_count = len(line) - len(stripped)
        if indent_count > 0:
            assert indent_count % 2 == 0, f"Indent not a multiple of 2: {line!r}"


def test_round_trip(tmp_path):
    """Assemble layout, write to file, read back — dicts are equal."""
    blueprint = Blueprint(
        id="roundtrip.bp",
        canvases=[
            CanvasEntry(name="page", left=5.0, right=95.0, top=3.0, bottom=97.0),
            CanvasEntry(
                name="main",
                left=10.0,
                right=90.0,
                top=15.0,
                bottom=85.0,
                parent="page",
            ),
        ],
    )
    page = ResolvedCanvas(name="page", left=5.0, right=95.0, top=3.0, bottom=97.0)
    main = ResolvedCanvas(
        name="main", left=10.0, right=90.0, top=15.0, bottom=85.0, parent="page"
    )
    resolved = {"page": page, "main": main}

    layout = assemble_layout(blueprint, resolved, resolved)
    output_file = tmp_path / "roundtrip.json"
    write_layout(layout, output_file)

    reloaded = json.loads(output_file.read_text())
    assert reloaded == layout

def test_assemble_layout_passthrough_description():
    """Layout includes 'description' when Blueprint has one."""
    blueprint = Blueprint(
        id="test.bp",
        canvases=[
            CanvasEntry(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
        ],
        description="A test layout",
    )
    resolved = {
        "page": ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
    }

    layout = assemble_layout(blueprint, resolved, resolved)

    assert layout["description"] == "A test layout"


def test_assemble_layout_passthrough_flags():
    """Layout includes 'flags' when Blueprint has them."""
    blueprint = Blueprint(
        id="test.bp",
        canvases=[
            CanvasEntry(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
        ],
        flags=["hidden"],
    )
    resolved = {
        "page": ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
    }

    layout = assemble_layout(blueprint, resolved, resolved)

    assert layout["flags"] == ["hidden"]


def test_assemble_layout_passthrough_aspectratio():
    """Layout includes 'aspectratio' when Blueprint has one."""
    blueprint = Blueprint(
        id="test.bp",
        canvases=[
            CanvasEntry(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
        ],
        aspectratio="603:783",
    )
    resolved = {
        "page": ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
    }

    layout = assemble_layout(blueprint, resolved, resolved)

    assert layout["aspectratio"] == "603:783"


def test_assemble_layout_omits_empty_passthrough_fields():
    """Layout omits description, flags, aspectratio when not set."""
    blueprint = Blueprint(
        id="minimal.bp",
        canvases=[
            CanvasEntry(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
        ],
    )
    resolved = {
        "page": ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
    }

    layout = assemble_layout(blueprint, resolved, resolved)

    assert "description" not in layout
    assert "flags" not in layout
    assert "aspectratio" not in layout
