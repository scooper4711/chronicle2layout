"""Property-based tests for layout loading and inheritance resolution.

Uses Hypothesis to verify universal properties across randomized inputs.

Requirements: 2.1, 2.2, 2.3, 2.4
"""

import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from layout_visualizer.layout_loader import (
    _parse_canvas_object,
    build_layout_index,
    load_layout_with_inheritance,
)
from layout_visualizer.models import CanvasRegion


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_coord = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)

_canvas_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=12,
)

_canvas_entry = st.fixed_dictionaries(
    {"x": _coord, "y": _coord, "x2": _coord, "y2": _coord},
    optional={"parent": _canvas_name},
)

_canvas_dict = st.dictionaries(
    keys=_canvas_name,
    values=_canvas_entry,
    min_size=1,
    max_size=10,
)


def _layout_chain_strategy():
    """Build a strategy that produces a list of (id, parent_id, canvas_dict) tuples.

    Chain depth is 2-5. Each layout may define 1-4 canvases. At least one
    overlapping canvas name is guaranteed between adjacent layers.
    """
    return (
        st.integers(min_value=2, max_value=5)
        .flatmap(lambda depth: st.tuples(
            # shared canvas names that will appear in multiple layers
            st.lists(_canvas_name, min_size=1, max_size=3, unique=True),
            # per-layer unique canvas names (may be empty)
            st.lists(
                st.lists(_canvas_name, min_size=0, max_size=3, unique=True),
                min_size=depth,
                max_size=depth,
            ),
            # per-layer canvas entries for shared names
            st.lists(
                st.lists(_canvas_entry, min_size=1, max_size=3),
                min_size=depth,
                max_size=depth,
            ),
            # per-layer canvas entries for unique names
            st.lists(
                st.lists(_canvas_entry, min_size=0, max_size=3),
                min_size=depth,
                max_size=depth,
            ),
        ))
    )


def _pick_entry(entries: list[dict], index: int) -> dict | None:
    """Select an entry from the list by cycling index, stripping 'parent'."""
    if not entries:
        return None
    entry = dict(entries[index % len(entries)])
    entry.pop("parent", None)
    return entry


def _build_shared_canvases(
    shared_names: list[str],
    entries: list[dict],
    layer_index: int,
) -> tuple[dict[str, dict], set[str]]:
    """Build canvas entries for shared names at a given layer."""
    canvas: dict[str, dict] = {}
    overlapping: set[str] = set()
    for j, name in enumerate(shared_names):
        entry = _pick_entry(entries, j)
        if entry is not None:
            canvas[name] = entry
            if layer_index > 0:
                overlapping.add(name)
    return canvas, overlapping


def _add_unique_canvases(
    canvas: dict[str, dict],
    unique_names: list[str],
    shared_names: list[str],
    entries: list[dict],
) -> None:
    """Add layer-specific unique canvases that don't collide with shared ones."""
    for j, name in enumerate(unique_names):
        if name in canvas or name in shared_names:
            continue
        entry = _pick_entry(entries, j)
        if entry is not None:
            canvas[name] = entry


def _build_chain(draw_result):
    """Convert raw strategy output into a list of layout dicts.

    Returns list of (layout_id, parent_id_or_None, canvas_dict) tuples,
    plus a set of canvas names that appear in more than one layer.
    """
    shared_names, unique_names_per_layer, shared_entries, unique_entries = draw_result
    depth = len(unique_names_per_layer)
    layouts = []
    all_overlapping: set[str] = set()

    for i in range(depth):
        layout_id = f"layout_{i}"
        parent_id = f"layout_{i - 1}" if i > 0 else None

        canvas, overlapping = _build_shared_canvases(shared_names, shared_entries[i], i)
        all_overlapping.update(overlapping)
        _add_unique_canvases(canvas, unique_names_per_layer[i], shared_names, unique_entries[i])

        layouts.append((layout_id, parent_id, canvas))

    return layouts, all_overlapping


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_layout(path: Path, data: dict) -> Path:
    """Write a layout dict as JSON to the given path."""
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Property 2: Canvas extraction round-trip
# Feature: layout-visualizer, Property 2: Canvas extraction round-trip
# ---------------------------------------------------------------------------

class TestCanvasExtractionRoundTrip:
    """Validates: Requirements 2.1"""

    @given(canvas_data=_canvas_dict)
    @settings(max_examples=100)
    def test_parse_preserves_all_fields(self, canvas_data: dict) -> None:
        """For any valid canvas dict, parsing produces CanvasRegion instances
        with identical field values for every entry.

        Feature: layout-visualizer, Property 2: Canvas extraction round-trip
        """
        result = _parse_canvas_object(canvas_data)

        assert set(result.keys()) == set(canvas_data.keys())

        for name, props in canvas_data.items():
            region = result[name]
            assert isinstance(region, CanvasRegion)
            assert region.name == name
            assert region.x == float(props["x"])
            assert region.y == float(props["y"])
            assert region.x2 == float(props["x2"])
            assert region.y2 == float(props["y2"])
            assert region.parent == props.get("parent")


# ---------------------------------------------------------------------------
# Property 3: Inheritance chain merging with child override
# Feature: layout-visualizer, Property 3: Inheritance chain merging with child override
# ---------------------------------------------------------------------------

class TestInheritanceChainMerging:
    """Validates: Requirements 2.2, 2.3, 2.4"""

    @given(chain_data=_layout_chain_strategy())
    @settings(max_examples=100, deadline=None)
    def test_child_overrides_parent_for_same_canvas(
        self,
        tmp_path_factory,
        chain_data,
    ) -> None:
        """For any chain of layouts with overlapping canvas names, the merged
        result uses the child's definition for shared names and includes all
        canvases from every layer.

        Feature: layout-visualizer, Property 3: Inheritance chain merging with child override
        """
        layouts, overlapping = _build_chain(chain_data)
        if not layouts:
            return

        tmp_dir = tmp_path_factory.mktemp("chain")

        # Write all layout files
        paths = []
        for layout_id, parent_id, canvas in layouts:
            data: dict = {"id": layout_id, "canvas": canvas}
            if parent_id is not None:
                data["parent"] = parent_id
            path = _write_layout(tmp_dir / f"{layout_id}.json", data)
            paths.append(path)

        index = build_layout_index(tmp_dir)
        leaf_path = paths[-1]

        merged, file_paths = load_layout_with_inheritance(leaf_path, index)

        # All canvas names from every layer must be present
        all_names: set[str] = set()
        for _, _, canvas in layouts:
            all_names.update(canvas.keys())
        assert set(merged.keys()) == all_names

        # For overlapping names, the child (last layer defining it) wins
        for name in overlapping:
            # Find the last layout in the chain that defines this canvas
            last_canvas_data = None
            for _, _, canvas in layouts:
                if name in canvas:
                    last_canvas_data = canvas[name]

            if last_canvas_data is not None:
                region = merged[name]
                assert region.x == float(last_canvas_data["x"])
                assert region.y == float(last_canvas_data["y"])
                assert region.x2 == float(last_canvas_data["x2"])
                assert region.y2 == float(last_canvas_data["y2"])

        # File paths should match the chain length
        assert len(file_paths) == len(layouts)
