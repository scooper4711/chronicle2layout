"""Canvas coordinate resolution from percentages to pixels.

Topologically sorts canvas regions by parent-child relationships and
converts percentage-based coordinates to absolute pixel positions on
the rendered page.
"""

from layout_visualizer.colors import PALETTE
from layout_visualizer.models import CanvasRegion, PixelRect


def topological_sort_canvases(
    canvases: dict[str, CanvasRegion],
) -> list[str]:
    """Sort canvas names so parents come before children.

    Args:
        canvases: Map of canvas name to CanvasRegion.

    Returns:
        List of canvas names in dependency order.

    Raises:
        ValueError: If a canvas references a parent not in the dict.

    Requirements: layout-visualizer 4.4, 4.5
    """
    for canvas in canvases.values():
        if canvas.parent is not None and canvas.parent not in canvases:
            raise ValueError(
                f"Canvas '{canvas.name}' references parent "
                f"'{canvas.parent}' which does not exist"
            )

    roots: list[str] = []
    children_of: dict[str, list[str]] = {name: [] for name in canvases}

    for name, canvas in canvases.items():
        if canvas.parent is None:
            roots.append(name)
        else:
            children_of[canvas.parent].append(name)

    ordered: list[str] = []
    queue = list(roots)
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        queue.extend(children_of[current])

    return ordered


def _resolve_single_canvas(
    canvas: CanvasRegion,
    parent_x: float,
    parent_y: float,
    parent_width: float,
    parent_height: float,
) -> PixelRect:
    """Convert one canvas's percentage coordinates to pixels.

    Args:
        canvas: The canvas region to resolve.
        parent_x: Parent's left edge in pixels.
        parent_y: Parent's top edge in pixels.
        parent_width: Parent's width in pixels.
        parent_height: Parent's height in pixels.

    Returns:
        A PixelRect with absolute pixel coordinates.
    """
    return PixelRect(
        name=canvas.name,
        x=parent_x + (canvas.x / 100) * parent_width,
        y=parent_y + (canvas.y / 100) * parent_height,
        x2=parent_x + (canvas.x2 / 100) * parent_width,
        y2=parent_y + (canvas.y2 / 100) * parent_height,
        parent=canvas.parent,
    )


def resolve_canvas_pixels(
    canvases: dict[str, CanvasRegion],
    page_width: int,
    page_height: int,
) -> dict[str, PixelRect]:
    """Convert percentage-based canvas coordinates to pixel positions.

    Processes canvases in topological order. For each canvas:
    - If it has a parent, computes pixel coords relative to the
      parent's resolved pixel bounds.
    - If no parent, treats the full page as the parent.

    Args:
        canvases: Map of canvas name to CanvasRegion.
        page_width: Page width in pixels.
        page_height: Page height in pixels.

    Returns:
        Map of canvas name to PixelRect with absolute pixel coords.

    Raises:
        ValueError: If a canvas references a nonexistent parent.

    Requirements: layout-visualizer 4.1, 4.2, 4.3, 4.4, 4.5
    """
    ordered = topological_sort_canvases(canvases)
    resolved: dict[str, PixelRect] = {}

    for name in ordered:
        canvas = canvases[name]
        if canvas.parent is None:
            resolved[name] = _resolve_single_canvas(
                canvas, 0, 0, page_width, page_height,
            )
        else:
            parent_rect = resolved[canvas.parent]
            resolved[name] = _resolve_single_canvas(
                canvas,
                parent_rect.x,
                parent_rect.y,
                parent_rect.x2 - parent_rect.x,
                parent_rect.y2 - parent_rect.y,
            )

    return resolved


def assign_colors(
    canvas_names: list[str],
) -> dict[str, tuple[int, int, int]]:
    """Assign a color from the palette to each canvas name.

    Cycles through the predefined palette when the number of
    canvases exceeds the palette size.

    Args:
        canvas_names: Ordered list of canvas region names.

    Returns:
        Map of canvas name to RGB color tuple.

    Requirements: layout-visualizer 5.1, 5.3
    """
    return {
        name: PALETTE[i % len(PALETTE)]
        for i, name in enumerate(canvas_names)
    }


def resolve_field_pixels(
    fields: list[CanvasRegion],
    canvas_pixels: dict[str, PixelRect],
) -> dict[str, PixelRect]:
    """Convert field percentage coordinates to absolute pixel positions.

    Each field's coordinates are percentages relative to its parent
    canvas. Uses the already-resolved canvas pixel rects to compute
    absolute positions.

    Args:
        fields: List of content fields as CanvasRegion instances.
        canvas_pixels: Resolved canvas pixel rects.

    Returns:
        Ordered dict of field name to PixelRect. Duplicate names get
        a numeric suffix.

    Raises:
        ValueError: If a field references a canvas not in canvas_pixels.
    """
    result: dict[str, PixelRect] = {}
    name_counts: dict[str, int] = {}

    for field in fields:
        if field.parent not in canvas_pixels:
            raise ValueError(
                f"Field '{field.name}' references canvas '{field.parent}' "
                f"which does not exist"
            )

        parent = canvas_pixels[field.parent]
        parent_width = parent.x2 - parent.x
        parent_height = parent.y2 - parent.y

        # Deduplicate names
        base_name = field.name
        count = name_counts.get(base_name, 0)
        name_counts[base_name] = count + 1
        unique_name = base_name if count == 0 else f"{base_name}_{count}"

        result[unique_name] = PixelRect(
            name=unique_name,
            x=parent.x + (field.x / 100) * parent_width,
            y=parent.y + (field.y / 100) * parent_height,
            x2=parent.x + (field.x2 / 100) * parent_width,
            y2=parent.y + (field.y2 / 100) * parent_height,
            parent=field.parent,
        )

    return result
