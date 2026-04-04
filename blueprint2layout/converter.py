"""Parent-relative coordinate conversion.

Converts resolved absolute page percentages to parent-relative
percentages as required by LAYOUT_FORMAT.md. Canvases with a parent
are expressed relative to the parent's bounds; canvases without a
parent use absolute percentages directly.
"""

from blueprint2layout.models import ResolvedCanvas


def convert_to_parent_relative(
    canvas: ResolvedCanvas,
    all_canvases: dict[str, ResolvedCanvas],
) -> dict[str, float | str]:
    """Convert a resolved canvas to parent-relative percentages.

    If the canvas has a parent, computes x, y, x2, y2 relative to
    the parent's bounds. If no parent, uses absolute percentages
    directly. All values rounded to one decimal place.

    Args:
        canvas: The resolved canvas to convert.
        all_canvases: All resolved canvases (for parent lookup).

    Returns:
        Dictionary with keys: x, y, x2, y2 (floats), and optionally
        "parent" (string) if the canvas has a parent.

    Raises:
        ValueError: If the parent canvas name is not found.

    Requirements: chronicle-blueprints 11.1, 11.2, 11.3, 11.4,
        11.5, 11.6, 11.7, 11.8
    """
    if canvas.parent is None:
        return {
            "x": round(canvas.left, 1),
            "y": round(canvas.top, 1),
            "x2": round(canvas.right, 1),
            "y2": round(canvas.bottom, 1),
        }

    if canvas.parent not in all_canvases:
        raise ValueError(
            f"Unknown parent canvas '{canvas.parent}' "
            f"for canvas '{canvas.name}'"
        )

    parent = all_canvases[canvas.parent]
    parent_width = parent.right - parent.left
    parent_height = parent.bottom - parent.top

    x = round((canvas.left - parent.left) / parent_width * 100, 1)
    y = round((canvas.top - parent.top) / parent_height * 100, 1)
    x2 = round((canvas.right - parent.left) / parent_width * 100, 1)
    y2 = round((canvas.bottom - parent.top) / parent_height * 100, 1)

    return {"x": x, "y": y, "x2": x2, "y2": y2, "parent": canvas.parent}
