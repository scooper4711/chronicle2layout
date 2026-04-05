"""Unit tests for coordinate resolution.

Tests topological sorting, percentage-to-pixel conversion,
orphaned canvas error handling, and color assignment with cycling.
"""

import pytest

from layout_visualizer.colors import PALETTE
from layout_visualizer.coordinate_resolver import (
    assign_colors,
    resolve_canvas_pixels,
    topological_sort_canvases,
)
from layout_visualizer.models import CanvasRegion, PixelRect


class TestTopologicalSortCanvases:
    """Tests for topological_sort_canvases."""

    def test_single_root_canvas(self):
        canvases = {
            "page": CanvasRegion(name="page", x=0, y=0, x2=100, y2=100),
        }

        result = topological_sort_canvases(canvases)

        assert result == ["page"]

    def test_parent_appears_before_child(self):
        canvases = {
            "child": CanvasRegion(
                name="child", x=10, y=10, x2=90, y2=90, parent="page",
            ),
            "page": CanvasRegion(name="page", x=0, y=0, x2=100, y2=100),
        }

        result = topological_sort_canvases(canvases)

        assert result.index("page") < result.index("child")

    def test_three_level_nesting(self):
        canvases = {
            "inner": CanvasRegion(
                name="inner", x=5, y=5, x2=95, y2=95, parent="main",
            ),
            "page": CanvasRegion(name="page", x=0, y=0, x2=100, y2=100),
            "main": CanvasRegion(
                name="main", x=10, y=10, x2=90, y2=90, parent="page",
            ),
        }

        result = topological_sort_canvases(canvases)

        assert result.index("page") < result.index("main")
        assert result.index("main") < result.index("inner")

    def test_multiple_roots_with_children(self):
        canvases = {
            "header": CanvasRegion(name="header", x=0, y=0, x2=100, y2=10),
            "body": CanvasRegion(name="body", x=0, y=10, x2=100, y2=100),
            "title": CanvasRegion(
                name="title", x=5, y=5, x2=95, y2=95, parent="header",
            ),
            "content": CanvasRegion(
                name="content", x=5, y=5, x2=95, y2=95, parent="body",
            ),
        }

        result = topological_sort_canvases(canvases)

        assert result.index("header") < result.index("title")
        assert result.index("body") < result.index("content")

    def test_all_results_present(self):
        canvases = {
            "a": CanvasRegion(name="a", x=0, y=0, x2=100, y2=100),
            "b": CanvasRegion(
                name="b", x=10, y=10, x2=90, y2=90, parent="a",
            ),
            "c": CanvasRegion(
                name="c", x=20, y=20, x2=80, y2=80, parent="a",
            ),
        }

        result = topological_sort_canvases(canvases)

        assert set(result) == {"a", "b", "c"}

    def test_orphaned_canvas_raises_value_error(self):
        canvases = {
            "child": CanvasRegion(
                name="child", x=10, y=10, x2=90, y2=90, parent="missing",
            ),
        }

        with pytest.raises(ValueError, match="missing"):
            topological_sort_canvases(canvases)


class TestResolveCanvasPixels:
    """Tests for resolve_canvas_pixels."""

    def test_root_canvas_full_page(self):
        canvases = {
            "page": CanvasRegion(
                name="page", x=0, y=0, x2=100, y2=100,
            ),
        }

        result = resolve_canvas_pixels(canvases, 1000, 800)

        rect = result["page"]
        assert rect == PixelRect(
            name="page", x=0, y=0, x2=1000, y2=800,
        )

    def test_root_canvas_partial_page(self):
        canvases = {
            "main": CanvasRegion(
                name="main", x=10, y=20, x2=90, y2=80,
            ),
        }

        result = resolve_canvas_pixels(canvases, 1000, 500)

        rect = result["main"]
        assert rect.x == pytest.approx(100.0)
        assert rect.y == pytest.approx(100.0)
        assert rect.x2 == pytest.approx(900.0)
        assert rect.y2 == pytest.approx(400.0)

    def test_child_relative_to_parent(self):
        canvases = {
            "page": CanvasRegion(
                name="page", x=0, y=0, x2=100, y2=100,
            ),
            "main": CanvasRegion(
                name="main", x=10, y=10, x2=60, y2=60, parent="page",
            ),
        }

        result = resolve_canvas_pixels(canvases, 1000, 1000)

        page = result["page"]
        main = result["main"]
        assert page == PixelRect(name="page", x=0, y=0, x2=1000, y2=1000)
        assert main.x == pytest.approx(100.0)
        assert main.y == pytest.approx(100.0)
        assert main.x2 == pytest.approx(600.0)
        assert main.y2 == pytest.approx(600.0)

    def test_nested_child_coordinates(self):
        """A grandchild's pixels are relative to its parent, not the page."""
        canvases = {
            "page": CanvasRegion(
                name="page", x=0, y=0, x2=100, y2=100,
            ),
            "main": CanvasRegion(
                name="main", x=10, y=10, x2=60, y2=60, parent="page",
            ),
            "inner": CanvasRegion(
                name="inner", x=0, y=0, x2=50, y2=50, parent="main",
            ),
        }

        result = resolve_canvas_pixels(canvases, 1000, 1000)

        inner = result["inner"]
        # main spans 100..600 (width=500, height=500)
        # inner is 0%..50% of main → 100..350
        assert inner.x == pytest.approx(100.0)
        assert inner.y == pytest.approx(100.0)
        assert inner.x2 == pytest.approx(350.0)
        assert inner.y2 == pytest.approx(350.0)

    def test_preserves_parent_field(self):
        canvases = {
            "page": CanvasRegion(
                name="page", x=0, y=0, x2=100, y2=100,
            ),
            "child": CanvasRegion(
                name="child", x=0, y=0, x2=100, y2=100, parent="page",
            ),
        }

        result = resolve_canvas_pixels(canvases, 800, 600)

        assert result["page"].parent is None
        assert result["child"].parent == "page"

    def test_orphaned_canvas_raises_value_error(self):
        canvases = {
            "orphan": CanvasRegion(
                name="orphan", x=0, y=0, x2=100, y2=100, parent="ghost",
            ),
        }

        with pytest.raises(ValueError, match="ghost"):
            resolve_canvas_pixels(canvases, 1000, 1000)

    def test_all_canvases_resolved(self):
        canvases = {
            "a": CanvasRegion(name="a", x=0, y=0, x2=100, y2=100),
            "b": CanvasRegion(
                name="b", x=10, y=10, x2=90, y2=90, parent="a",
            ),
            "c": CanvasRegion(
                name="c", x=20, y=20, x2=80, y2=80, parent="a",
            ),
        }

        result = resolve_canvas_pixels(canvases, 500, 500)

        assert set(result.keys()) == {"a", "b", "c"}


class TestAssignColors:
    """Tests for assign_colors."""

    def test_single_canvas_gets_first_color(self):
        result = assign_colors(["page"])

        assert result["page"] == PALETTE[0]

    def test_colors_follow_palette_order(self):
        names = ["a", "b", "c"]

        result = assign_colors(names)

        assert result["a"] == PALETTE[0]
        assert result["b"] == PALETTE[1]
        assert result["c"] == PALETTE[2]

    def test_cycling_wraps_around_palette(self):
        names = [f"canvas_{i}" for i in range(len(PALETTE) + 3)]

        result = assign_colors(names)

        assert result["canvas_0"] == PALETTE[0]
        assert result[f"canvas_{len(PALETTE)}"] == PALETTE[0]
        assert result[f"canvas_{len(PALETTE) + 1}"] == PALETTE[1]
        assert result[f"canvas_{len(PALETTE) + 2}"] == PALETTE[2]

    def test_empty_list_returns_empty_dict(self):
        result = assign_colors([])

        assert result == {}

    def test_all_names_assigned(self):
        names = ["header", "body", "footer", "sidebar"]

        result = assign_colors(names)

        assert set(result.keys()) == set(names)
