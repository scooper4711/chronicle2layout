"""Unit tests for parent-relative coordinate conversion.

Tests convert_to_parent_relative from blueprint2layout.converter,
verifying the formula for parent-relative percentages, absolute
pass-through, rounding, error handling, and parent key inclusion.

Validates: Requirements 11.1–11.8
"""

import pytest

from blueprint2layout.converter import convert_to_parent_relative
from blueprint2layout.models import ResolvedCanvas


def test_convert_without_parent():
    """Canvas with no parent passes absolute percentages through directly."""
    canvas = ResolvedCanvas(
        name="page",
        left=5.0,
        right=95.0,
        top=10.0,
        bottom=90.0,
        parent=None,
    )
    result = convert_to_parent_relative(canvas, {})

    assert result == {"x": 5.0, "y": 10.0, "x2": 95.0, "y2": 90.0}


def test_convert_with_parent():
    """Canvas filling parent exactly produces 0–100 relative coordinates."""
    parent = ResolvedCanvas(
        name="page",
        left=10.0,
        right=90.0,
        top=20.0,
        bottom=80.0,
        parent=None,
    )
    canvas = ResolvedCanvas(
        name="main",
        left=10.0,
        right=90.0,
        top=20.0,
        bottom=80.0,
        parent="page",
    )
    all_canvases = {"page": parent, "main": canvas}
    result = convert_to_parent_relative(canvas, all_canvases)

    assert result == {
        "x": 0.0,
        "y": 0.0,
        "x2": 100.0,
        "y2": 100.0,
        "parent": "page",
    }


def test_convert_with_parent_partial():
    """Canvas partially inside parent produces correct relative percentages."""
    parent = ResolvedCanvas(
        name="page",
        left=0.0,
        right=100.0,
        top=0.0,
        bottom=100.0,
        parent=None,
    )
    canvas = ResolvedCanvas(
        name="summary",
        left=25.0,
        right=75.0,
        top=10.0,
        bottom=50.0,
        parent="page",
    )
    all_canvases = {"page": parent, "summary": canvas}
    result = convert_to_parent_relative(canvas, all_canvases)

    assert result == {
        "x": 25.0,
        "y": 10.0,
        "x2": 75.0,
        "y2": 50.0,
        "parent": "page",
    }


def test_convert_rounding():
    """Values are rounded to 1 decimal place."""
    parent = ResolvedCanvas(
        name="page",
        left=0.0,
        right=100.0,
        top=0.0,
        bottom=100.0,
        parent=None,
    )
    canvas = ResolvedCanvas(
        name="detail",
        left=33.333,
        right=66.667,
        top=11.111,
        bottom=88.889,
        parent="page",
    )
    all_canvases = {"page": parent, "detail": canvas}
    result = convert_to_parent_relative(canvas, all_canvases)

    assert result == {
        "x": 33.3,
        "y": 11.1,
        "x2": 66.7,
        "y2": 88.9,
        "parent": "page",
    }


def test_convert_unknown_parent_raises_error():
    """Canvas referencing an unknown parent raises ValueError."""
    canvas = ResolvedCanvas(
        name="orphan",
        left=0.0,
        right=100.0,
        top=0.0,
        bottom=100.0,
        parent="nonexistent",
    )
    with pytest.raises(ValueError, match="Unknown parent canvas 'nonexistent'"):
        convert_to_parent_relative(canvas, {})


def test_convert_includes_parent_key():
    """Result dict includes 'parent' key when canvas has a parent."""
    parent = ResolvedCanvas(
        name="page",
        left=0.0,
        right=100.0,
        top=0.0,
        bottom=100.0,
        parent=None,
    )
    canvas = ResolvedCanvas(
        name="main",
        left=0.0,
        right=100.0,
        top=0.0,
        bottom=100.0,
        parent="page",
    )
    all_canvases = {"page": parent, "main": canvas}
    result = convert_to_parent_relative(canvas, all_canvases)

    assert "parent" in result
    assert result["parent"] == "page"


def test_convert_no_parent_key_when_none():
    """Result dict does NOT include 'parent' key when canvas has no parent."""
    canvas = ResolvedCanvas(
        name="page",
        left=0.0,
        right=100.0,
        top=0.0,
        bottom=100.0,
        parent=None,
    )
    result = convert_to_parent_relative(canvas, {})

    assert "parent" not in result
