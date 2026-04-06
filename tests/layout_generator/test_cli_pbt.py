"""Property-based tests for layout_generator.__main__ module.

Uses hypothesis to verify universal properties of canvas coordinate
resolution across randomly generated nested canvas hierarchies.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from layout_generator.__main__ import _compose_absolute_coordinates


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Canvas coordinate values in [0, 100] as floats.
_coord = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)

# A single canvas entry with x, y, x2, y2 coordinates.
_canvas_coords = st.fixed_dictionaries({
    "x": _coord,
    "y": _coord,
    "x2": _coord,
    "y2": _coord,
})


@st.composite
def _nested_canvas_chain(draw: st.DrawFn) -> tuple[str, dict[str, dict]]:
    """Generate a chain of 1-3 nested canvases with parent references.

    Returns the target canvas name and the canvases dict. Each child's
    coordinates are percentages relative to its parent canvas. The
    outermost canvas has no parent (relative to the full page).
    """
    depth = draw(st.integers(min_value=1, max_value=3))
    canvases: dict[str, dict] = {}

    for level in range(depth):
        name = f"canvas_{level}"
        coords = draw(_canvas_coords)
        props: dict = dict(coords)
        if level > 0:
            props["parent"] = f"canvas_{level - 1}"
        canvases[name] = props

    target = f"canvas_{depth - 1}"
    return target, canvases


def _manually_compose(canvases: dict[str, dict], target: str) -> list[float]:
    """Manually compute absolute coordinates by composing transformations.

    Walks from the target canvas up to the root, collecting the chain,
    then applies each transformation from root to target using the
    formula from the property statement:
        abs = parent_origin + (relative / 100) * parent_size
    """
    chain: list[dict] = []
    current: str | None = target
    while current is not None and current in canvases:
        chain.append(canvases[current])
        current = canvases[current].get("parent")

    # Start with the full page as the absolute reference
    px, py, px2, py2 = 0.0, 0.0, 100.0, 100.0

    # Walk from root canvas down to target, composing coordinates
    for props in reversed(chain):
        pw = px2 - px
        ph = py2 - py
        rx = float(props["x"])
        ry = float(props["y"])
        rx2 = float(props["x2"])
        ry2 = float(props["y2"])
        new_x0 = px + rx / 100.0 * pw
        new_y0 = py + ry / 100.0 * ph
        new_x2 = px + rx2 / 100.0 * pw
        new_y2 = py + ry2 / 100.0 * ph
        px, py, px2, py2 = new_x0, new_y0, new_x2, new_y2

    return [px, py, px2, py2]


# ---------------------------------------------------------------------------
# Property 2: Canvas coordinate resolution composes correctly
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 2: Canvas coordinate resolution composes correctly
@given(chain_data=_nested_canvas_chain())
@settings(max_examples=100)
def test_canvas_coordinate_resolution(
    chain_data: tuple[str, dict[str, dict]],
) -> None:
    """Resolving nested canvas coordinates composes all relative transformations.

    Validates: Requirements 3.2, 3.3

    Strategy:
    - Generate a chain of 1-3 nested canvases, each with x, y, x2, y2
      in [0, 100] as percentages relative to its parent.
    - Manually compute expected absolute coordinates by composing the
      formula: abs = parent_origin + relative / 100 * parent_size
      at each level from root to target.
    - Call _compose_absolute_coordinates and verify the result matches
      the manual computation within floating-point tolerance.
    """
    target, canvases = chain_data
    expected = _manually_compose(canvases, target)
    actual = _compose_absolute_coordinates(target, canvases)

    assert len(actual) == 4
    for i in range(4):
        assert abs(actual[i] - expected[i]) < 1e-9, (
            f"Coordinate {i} mismatch: expected {expected[i]}, "
            f"got {actual[i]} for canvases={canvases}, target={target}"
        )
