"""Property-based tests for coordinate resolution.

Uses Hypothesis to verify universal properties across randomized inputs.

Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.3
"""

import pytest

from hypothesis import given, settings
from hypothesis import strategies as st

from layout_visualizer.colors import PALETTE
from layout_visualizer.coordinate_resolver import (
    assign_colors,
    resolve_canvas_pixels,
    topological_sort_canvases,
)
from layout_visualizer.models import CanvasRegion


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_coord = st.floats(
    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False,
)

_page_dim = st.integers(min_value=100, max_value=5000)

_canvas_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=12,
)


def _root_canvas_region_strategy():
    """Generate a single root CanvasRegion (no parent) with random coords."""
    return st.builds(
        lambda name, x, y, x2, y2: CanvasRegion(
            name=name, x=x, y=y, x2=x2, y2=y2, parent=None,
        ),
        name=st.just("root"),
        x=_coord,
        y=_coord,
        x2=_coord,
        y2=_coord,
    )


def _canvas_forest_strategy():
    """Generate a random forest of parent-child canvas relationships.

    Produces a dict[str, CanvasRegion] where parent references form
    a valid forest (no cycles). Each canvas either has no parent (root)
    or references a canvas that appears earlier in the list.
    """
    return st.integers(min_value=1, max_value=15).flatmap(_build_forest)


def _build_forest(size: int):
    """Build a forest of `size` canvases with valid parent references."""
    return st.lists(
        st.tuples(
            _coord, _coord, _coord, _coord,
            st.booleans(),
        ),
        min_size=size,
        max_size=size,
    ).map(lambda entries: _entries_to_canvases(entries))


def _entries_to_canvases(
    entries: list[tuple[float, float, float, float, bool]],
) -> dict[str, CanvasRegion]:
    """Convert raw entries into a canvas dict with valid parent references."""
    canvases: dict[str, CanvasRegion] = {}
    names: list[str] = []

    for i, (x, y, x2, y2, has_parent) in enumerate(entries):
        name = f"canvas_{i}"
        parent = None
        if has_parent and names:
            # Pick a parent from previously created canvases
            parent = names[i % len(names)]
        canvases[name] = CanvasRegion(
            name=name, x=x, y=y, x2=x2, y2=y2, parent=parent,
        )
        names.append(name)

    return canvases


# ---------------------------------------------------------------------------
# Property 4: Percentage-to-pixel coordinate conversion
# Feature: layout-visualizer, Property 4: Percentage-to-pixel coordinate conversion
# ---------------------------------------------------------------------------

class TestPercentageToPixelConversion:
    """Validates: Requirements 4.1, 4.2, 4.3"""

    @given(
        canvas=_root_canvas_region_strategy(),
        page_width=_page_dim,
        page_height=_page_dim,
    )
    @settings(max_examples=100)
    def test_pixel_equals_percentage_times_page_dimension(
        self,
        canvas: CanvasRegion,
        page_width: int,
        page_height: int,
    ) -> None:
        """For any root canvas with percentage coordinates and page dimensions,
        the pixel coordinates equal (percentage / 100) * page_dimension.

        Feature: layout-visualizer, Property 4: Percentage-to-pixel coordinate conversion
        """
        canvases = {canvas.name: canvas}
        result = resolve_canvas_pixels(canvases, page_width, page_height)
        rect = result[canvas.name]

        assert rect.x == pytest.approx((canvas.x / 100) * page_width)
        assert rect.y == pytest.approx((canvas.y / 100) * page_height)
        assert rect.x2 == pytest.approx((canvas.x2 / 100) * page_width)
        assert rect.y2 == pytest.approx((canvas.y2 / 100) * page_height)


# ---------------------------------------------------------------------------
# Property 5: Topological ordering preserves parent-before-child
# Feature: layout-visualizer, Property 5: Topological ordering preserves parent-before-child
# ---------------------------------------------------------------------------

class TestTopologicalOrdering:
    """Validates: Requirements 4.4"""

    @given(canvases=_canvas_forest_strategy())
    @settings(max_examples=100)
    def test_parent_appears_before_child_in_ordering(
        self,
        canvases: dict[str, CanvasRegion],
    ) -> None:
        """For any canvas forest, the topological sort places every canvas's
        parent before the canvas itself.

        Feature: layout-visualizer, Property 5: Topological ordering preserves parent-before-child
        """
        ordered = topological_sort_canvases(canvases)

        # All canvases must be present
        assert set(ordered) == set(canvases.keys())

        # Every canvas with a parent must appear after its parent
        index_of = {name: i for i, name in enumerate(ordered)}
        for name, canvas in canvases.items():
            if canvas.parent is not None:
                assert index_of[canvas.parent] < index_of[name], (
                    f"Parent '{canvas.parent}' (index {index_of[canvas.parent]}) "
                    f"should appear before child '{name}' (index {index_of[name]})"
                )


# ---------------------------------------------------------------------------
# Property 6: Color assignment with palette cycling
# Feature: layout-visualizer, Property 6: Color assignment with palette cycling
# ---------------------------------------------------------------------------

class TestColorAssignmentPaletteCycling:
    """Validates: Requirements 5.1, 5.3"""

    @given(
        names=st.lists(
            _canvas_name,
            min_size=1,
            max_size=30,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_canvas_at_index_i_gets_palette_i_mod_len(
        self,
        names: list[str],
    ) -> None:
        """For any list of unique canvas names, the canvas at index i
        is assigned PALETTE[i % len(PALETTE)].

        Feature: layout-visualizer, Property 6: Color assignment with palette cycling
        """
        result = assign_colors(names)

        assert len(result) == len(names)
        for i, name in enumerate(names):
            expected_color = PALETTE[i % len(PALETTE)]
            assert result[name] == expected_color, (
                f"Canvas '{name}' at index {i} should get "
                f"PALETTE[{i % len(PALETTE)}]={expected_color}, "
                f"got {result[name]}"
            )
