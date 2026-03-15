"""Shared utility functions for the chronicle2layout package.

Consolidates functions that were previously duplicated across multiple modules
into a single source of truth. All layout file resolution and canvas coordinate
transformation should use these functions.

Public functions:
    find_layout_file: Resolve a layout ID to a filesystem Path.
    transform_canvas_coordinates: Transform canvas coordinates to absolute page percentages.

Requirements: refactor-chronicle2layout 1.1, 1.2, 1.6, 1.7, 1.8, 5.1, 5.2, 8.1, 10.1
"""

import re
from pathlib import Path


def find_layout_file(layout_dir: str, layout_id: str) -> Path:
    """Resolve a layout ID string to the corresponding layout JSON file path.

    Supports several layout ID patterns:
      - Single-part ID: ``pfs2`` → ``<layout_dir>/pfs2/pfs2.json``
      - Season parent: ``pfs2.season5`` → ``<layout_dir>/pfs2/s5/Season 5.json``
      - Season variant: ``pfs2.season4a`` → ``<layout_dir>/pfs2/s4/Season4a.json``
        (checks for ``.generated.json`` first, falls back to ``.json``)
      - Scenario reference: ``pfs2.s5-07`` → ``<layout_dir>/pfs2/s5/s5-07.json``
      - Generic fallback: ``pfs2.foo`` → ``<layout_dir>/pfs2/foo/foo.json``

    Args:
        layout_dir: Base layouts directory (e.g. ``'layouts'``).
        layout_id: Dot-separated layout identifier (e.g. ``'pfs2.season5'``).

    Returns:
        Resolved ``Path`` to the layout JSON file.

    Raises:
        ValueError: If the resolved layout file does not exist on disk.
    """
    base_path = Path(layout_dir)
    parts = layout_id.split(".")

    if len(parts) == 1:
        layout_file = base_path / parts[0] / f"{parts[0]}.json"
    else:
        search_base = base_path / parts[0]
        ident = parts[1]
        match = re.match(r"^season(\d+)([a-z])?$", ident)

        if match:
            season_num = match.group(1)
            variant = match.group(2)
            season_dir = search_base / f"s{season_num}"

            if variant:
                # Check for .generated.json first, fall back to regular .json
                generated = season_dir / f"Season{season_num}{variant}.generated.json"
                if generated.exists():
                    return generated
                layout_file = season_dir / f"Season{season_num}{variant}.json"
            else:
                layout_file = season_dir / f"Season {season_num}.json"
        elif ident.startswith("s") and "-" in ident:
            season_num = ident.split("-")[0][1:]
            layout_file = search_base / f"s{season_num}" / f"{ident}.json"
        else:
            layout_file = search_base / ident / f"{ident}.json"

    if not layout_file.exists():
        raise ValueError(f"Layout file not found: {layout_file}")

    return layout_file


def transform_canvas_coordinates(layout_json: dict, canvas_name: str) -> list[float]:
    """Transform canvas coordinates to absolute page percentages by following the parent chain.

    Each canvas entry in the layout JSON defines coordinates as percentages of its
    parent canvas (or the full page if no parent is specified). This function
    recursively resolves parent references to produce absolute page-level
    percentage coordinates.

    Args:
        layout_json: The loaded layout JSON object containing a ``"canvas"`` key.
        canvas_name: Name of the canvas to transform (e.g. ``"items"``).

    Returns:
        A list ``[x, y, x2, y2]`` of absolute page percentage coordinates.

    Raises:
        ValueError: If *canvas_name* is not found in the layout's ``"canvas"`` dict.
    """
    if "canvas" not in layout_json or canvas_name not in layout_json["canvas"]:
        raise ValueError(f"Canvas {canvas_name} not found in layout")

    def transform(name: str) -> list[float]:
        canvas = layout_json["canvas"][name]
        x, y, x2, y2 = canvas["x"], canvas["y"], canvas["x2"], canvas["y2"]

        if "parent" in canvas:
            px, py, px2, py2 = transform(canvas["parent"])
            pw = px2 - px
            ph = py2 - py
            x = px + (x / 100.0) * pw
            y = py + (y / 100.0) * ph
            x2 = px + (x2 / 100.0) * pw
            y2 = py + (y2 / 100.0) * ph

        return [x, y, x2, y2]

    return transform(canvas_name)
