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

LINE_REFERENCE_PATTERN = r"^(h_thin|h_bar|h_rule|v_thin|v_bar|grey_box)\[(\d+)\]$"
CANVAS_REFERENCE_PATTERN = r"^(\w+)\.(left|right|top|bottom)$"

_HORIZONTAL_CATEGORIES = {"h_thin", "h_bar", "h_rule"}
_VERTICAL_CATEGORIES = {"v_thin", "v_bar"}


def resolve_edge_value(
    edge_value: int | float | str,
    detection: DetectionResult,
    resolved_canvases: dict[str, ResolvedCanvas],
) -> float:
    """Resolve a single edge value to an absolute page percentage.

    Handles three cases:
    - Numeric literal: returned directly as float.
    - Line reference (e.g., "h_bar[0]"): looks up the detected line's
      primary-axis value (y for horizontal, x for vertical).
    - Canvas reference (e.g., "summary.bottom"): looks up the named
      canvas's resolved edge value.

    Args:
        edge_value: The raw edge value from the Blueprint.
        detection: The detection result for line reference lookups.
        resolved_canvases: Already-resolved canvases for canvas ref lookups.

    Returns:
        The resolved absolute page percentage.

    Raises:
        ValueError: If the reference is malformed, category unknown,
            index out of bounds, or canvas not yet resolved.

    Requirements: chronicle-blueprints 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
    """
    if isinstance(edge_value, (int, float)):
        return float(edge_value)

    line_match = re.match(LINE_REFERENCE_PATTERN, edge_value)
    if line_match:
        return _resolve_line_reference(line_match, detection)

    canvas_match = re.match(CANVAS_REFERENCE_PATTERN, edge_value)
    if canvas_match:
        return _resolve_canvas_reference(canvas_match, resolved_canvases)

    raise ValueError(
        f"Edge value '{edge_value}' is not a numeric literal, "
        f"line reference, or canvas reference"
    )


def _resolve_line_reference(match: re.Match, detection: DetectionResult) -> float:
    """Look up a line reference's primary-axis value from the detection result."""
    category = match.group(1)
    index = int(match.group(2))

    if category == "grey_box":
        raise ValueError(
            f"'{category}' is not a valid line reference category"
        )

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
