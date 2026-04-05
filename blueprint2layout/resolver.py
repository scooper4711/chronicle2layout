"""Edge value resolution for Blueprint canvas entries.

Resolves canvas edge values (numeric literals, line references, and
canvas references) to absolute page percentages using the detection
result and previously resolved canvases. Enforces backward-only
canvas references for deterministic, cycle-free resolution.
"""

import re

from blueprint2layout.models import (
    CanvasEntry,
    DetectionResult,
    ResolvedCanvas,
)

LINE_REFERENCE_PATTERN = r"^(h_thin|h_bar|h_rule|v_thin|v_bar)\[(\d+)\]$"
SECONDARY_AXIS_PATTERN = (
    r"^(h_thin|h_bar|h_rule|v_thin|v_bar|grey_box)\[(\d+)\]\.(left|right|top|bottom)$"
)
CANVAS_REFERENCE_PATTERN = r"^(\w+)\.(left|right|top|bottom)$"

_HORIZONTAL_CATEGORIES = {"h_thin", "h_bar", "h_rule"}
_VERTICAL_CATEGORIES = {"v_thin", "v_bar"}
_HORIZONTAL_SECONDARY_EDGES = {"left", "right", "top", "bottom"}
_VERTICAL_SECONDARY_EDGES = {"top", "bottom"}
_GREY_BOX_SECONDARY_EDGES = {"left", "right", "top", "bottom"}


def resolve_edge_value(
    edge_value: int | float | str,
    detection: DetectionResult,
    resolved_canvases: dict[str, ResolvedCanvas],
) -> float:
    """Resolve a single edge value to an absolute page percentage.

    Resolution order:
    1. Numeric literal — returned directly as float.
    2. Secondary axis reference (e.g., "h_thin[3].left") — resolves
       to the element's secondary-axis attribute.
    3. Plain line reference (e.g., "h_bar[0]") — resolves to the
       detected line's primary-axis value (y for horizontal, x for
       vertical).
    4. Canvas reference (e.g., "summary.bottom") — resolves to the
       named canvas's resolved edge value.
    5. Error — unrecognized pattern.

    Args:
        edge_value: The raw edge value from the Blueprint.
        detection: The detection result for line reference lookups.
        resolved_canvases: Already-resolved canvases for canvas ref lookups.

    Returns:
        The resolved absolute page percentage.

    Raises:
        ValueError: If the reference is malformed, category unknown,
            index out of bounds, canvas not yet resolved, or invalid
            secondary edge for the element category.

    Requirements: chronicle-blueprints 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
                  blueprint-fields 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 12.1, 12.3, 12.4, 12.5
    """
    if isinstance(edge_value, (int, float)):
        return float(edge_value)

    secondary_match = re.match(SECONDARY_AXIS_PATTERN, edge_value)
    if secondary_match:
        return _resolve_secondary_axis_reference(secondary_match, detection)

    line_match = re.match(LINE_REFERENCE_PATTERN, edge_value)
    if line_match:
        return _resolve_line_reference(line_match, detection)

    canvas_match = re.match(CANVAS_REFERENCE_PATTERN, edge_value)
    if canvas_match:
        return _resolve_canvas_reference(canvas_match, resolved_canvases)

    raise ValueError(
        f"Edge value '{edge_value}' is not a recognized pattern"
    )


def _resolve_line_reference(match: re.Match, detection: DetectionResult) -> float:
    """Look up a line reference's primary-axis value from the detection result."""
    category = match.group(1)
    index = int(match.group(2))

    lines = getattr(detection, category)
    if index >= len(lines):
        raise ValueError(
            f"Index {index} out of bounds for '{category}' "
            f"(has {len(lines)} element{'s' if len(lines) != 1 else ''})"
        )

    line = lines[index]
    if category in _HORIZONTAL_CATEGORIES:
        return line.y
    return line.x


def _resolve_secondary_axis_reference(
    match: re.Match,
    detection: DetectionResult,
) -> float:
    """Resolve a secondary axis reference to the element's attribute.

    Horizontal lines support `.left` (x) and `.right` (x2).
    Vertical lines support `.top` (y) and `.bottom` (y2).
    Grey boxes support all four edges.

    Raises:
        ValueError: If the edge is invalid for the category or index
            is out of bounds.
    """
    category = match.group(1)
    index = int(match.group(2))
    edge = match.group(3)

    if category in _HORIZONTAL_CATEGORIES:
        valid_edges = _HORIZONTAL_SECONDARY_EDGES
    elif category in _VERTICAL_CATEGORIES:
        valid_edges = _VERTICAL_SECONDARY_EDGES
    else:
        valid_edges = _GREY_BOX_SECONDARY_EDGES

    if edge not in valid_edges:
        raise ValueError(
            f"Invalid secondary edge '.{edge}' for '{category}'; "
            f"valid edges are {sorted(valid_edges)}"
        )

    elements = getattr(detection, category)
    if index >= len(elements):
        raise ValueError(
            f"Index {index} out of bounds for '{category}' "
            f"(has {len(elements)} element{'s' if len(elements) != 1 else ''})"
        )

    element = elements[index]
    edge_attr_map = {"left": "x", "right": "x2", "top": "y", "bottom": "y2"}
    return getattr(element, edge_attr_map[edge])


def _resolve_canvas_reference(
    match: re.Match,
    resolved_canvases: dict[str, ResolvedCanvas],
) -> float:
    """Look up a canvas reference's edge value from already-resolved canvases."""
    canvas_name = match.group(1)
    edge = match.group(2)

    if canvas_name not in resolved_canvases:
        raise ValueError(
            f"Canvas '{canvas_name}' has not been resolved yet; "
            f"canvas references must refer to previously resolved canvases"
        )

    return getattr(resolved_canvases[canvas_name], edge)


def resolve_canvases(
    inherited_canvases: list[CanvasEntry],
    target_canvases: list[CanvasEntry],
    detection: DetectionResult,
) -> dict[str, ResolvedCanvas]:
    """Resolve all canvases in order: inherited first, then target.

    Processes canvases sequentially. Each canvas's four edges are
    resolved via resolve_edge_value. Only backward canvas references
    are permitted.

    Args:
        inherited_canvases: Canvas entries from parent Blueprints.
        target_canvases: Canvas entries from the target Blueprint.
        detection: Detection result for line reference resolution.

    Returns:
        Dictionary mapping canvas names to ResolvedCanvas instances,
        containing both inherited and target canvases.

    Raises:
        ValueError: If a forward canvas reference is encountered.

    Requirements: chronicle-blueprints 10.1, 10.2, 10.3, 10.4
    """
    resolved: dict[str, ResolvedCanvas] = {}
    all_canvases = list(inherited_canvases) + list(target_canvases)

    for canvas in all_canvases:
        left = resolve_edge_value(canvas.left, detection, resolved)
        right = resolve_edge_value(canvas.right, detection, resolved)
        top = resolve_edge_value(canvas.top, detection, resolved)
        bottom = resolve_edge_value(canvas.bottom, detection, resolved)

        resolved[canvas.name] = ResolvedCanvas(
            name=canvas.name,
            left=left,
            right=right,
            top=top,
            bottom=bottom,
            parent=canvas.parent,
        )

    return resolved
