"""Field resolution for Blueprint field entries.

Resolves field styles (composition chains), field edge values
(including em offset expressions), top-edge defaults, and
parent-relative coordinate conversion. Produces ResolvedField
instances ready for content element generation.
"""

import re

from blueprint2layout.converter import convert_to_parent_relative
from blueprint2layout.models import (
    DetectionResult,
    FieldEntry,
    ResolvedCanvas,
    ResolvedField,
)
from blueprint2layout.resolver import resolve_edge_value

EM_OFFSET_PATTERN = r"^(.+?)\s*([+-])\s*(\d+(?:\.\d+)?)em$"

# Pattern for canvas-scoped references: @category[index] or @category[index].edge
CANVAS_SCOPED_PREFIX = "@"

_HORIZONTAL_CATEGORIES = {"h_thin", "h_bar", "h_rule"}
_VERTICAL_CATEGORIES = {"v_thin", "v_bar"}
_ALL_DETECTION_CATEGORIES = (
    "h_thin", "h_bar", "h_rule", "v_thin", "v_bar", "grey_box",
)

# Properties that can be inherited from field styles
STYLE_PROPERTIES = (
    "canvas", "type", "font", "fontsize", "fontweight", "align",
    "color", "linewidth", "size", "lines", "left", "right", "top", "bottom",
)

VALID_FIELD_TYPES = {"text", "multiline", "line", "rectangle"}


def _build_scoped_detection(
    detection: DetectionResult,
    canvas: ResolvedCanvas,
) -> DetectionResult:
    """Build a DetectionResult containing only elements within a canvas.

    Filters each detection category to elements whose primary axis
    falls within the canvas bounds. Horizontal lines are filtered by
    y (between canvas top and bottom), vertical lines by x (between
    canvas left and right), and grey boxes by both axes.

    Args:
        detection: The full-page detection result.
        canvas: The resolved canvas to scope to.

    Returns:
        A new DetectionResult with only in-canvas elements, preserving
        the original sort order within each category.
    """
    def h_in_bounds(line):
        return (canvas.top <= line.y <= canvas.bottom
                and line.x2 >= canvas.left and line.x <= canvas.right)

    def v_in_bounds(line):
        return (canvas.left <= line.x <= canvas.right
                and line.y2 >= canvas.top and line.y <= canvas.bottom)

    def box_in_bounds(box):
        return (canvas.left <= box.x <= canvas.right
                and canvas.top <= box.y <= canvas.bottom)

    return DetectionResult(
        h_thin=[e for e in detection.h_thin if h_in_bounds(e)],
        h_bar=[e for e in detection.h_bar if h_in_bounds(e)],
        h_rule=[e for e in detection.h_rule if h_in_bounds(e)],
        v_thin=[e for e in detection.v_thin if v_in_bounds(e)],
        v_bar=[e for e in detection.v_bar if v_in_bounds(e)],
        grey_box=[e for e in detection.grey_box if box_in_bounds(e)],
    )


def _resolve_style_chain(
    style_name: str,
    field_styles: dict[str, dict],
    visited: set[str],
    field_name: str,
) -> dict:
    """Resolve a single style and its base styles recursively.

    Depth-first resolution: base styles are resolved first, then
    the current style's own properties override them.

    Args:
        style_name: The style to resolve.
        field_styles: All available style definitions.
        visited: Set of already-visited style names for cycle detection.
        field_name: The originating field name (for error messages).

    Returns:
        Dictionary of resolved properties from this style chain.

    Raises:
        ValueError: If the style is undefined or circular.
    """
    if style_name not in field_styles:
        raise ValueError(
            f"Field '{field_name}' references undefined style '{style_name}'"
        )

    if style_name in visited:
        raise ValueError(
            f"Circular style reference detected: '{style_name}' already visited"
        )

    visited.add(style_name)
    style_def = field_styles[style_name]

    effective: dict = {}

    # Resolve base styles first (depth-first, left-to-right)
    for base_name in style_def.get("styles", []):
        base_props = _resolve_style_chain(base_name, field_styles, visited, field_name)
        effective.update(base_props)

    # Apply this style's own properties (override base styles)
    for prop in STYLE_PROPERTIES:
        if prop in style_def and style_def[prop] is not None:
            effective[prop] = style_def[prop]

    return effective


def resolve_field_styles(
    field_entry: FieldEntry,
    field_styles: dict[str, dict],
) -> dict:
    """Resolve the effective properties for a field after style composition.

    Applies styles in order: base styles first (recursively), then
    the field's own styles, then the field's direct properties.
    Later values override earlier ones.

    Args:
        field_entry: The field entry to resolve.
        field_styles: All available field style definitions.

    Returns:
        Dictionary of effective property values.

    Raises:
        ValueError: If a referenced style is undefined or circular.

    Requirements: blueprint-fields 6.3, 6.4, 6.5, 6.6, 6.7, 6.9
    """
    effective: dict = {}

    # Resolve each style in the field's styles list (left-to-right)
    for style_name in field_entry.styles:
        visited: set[str] = set()
        style_props = _resolve_style_chain(
            style_name, field_styles, visited, field_entry.name,
        )
        effective.update(style_props)

    # Apply the field's own direct properties (override everything from styles)
    for prop in STYLE_PROPERTIES:
        value = getattr(field_entry, prop)
        if value is not None:
            effective[prop] = value

    return effective


def _parse_aspectratio(aspectratio: str) -> tuple[float, float]:
    """Parse an aspectratio string into (width, height) in points.

    Args:
        aspectratio: String like "603:783".

    Returns:
        Tuple of (width, height) as floats.
    """
    width_str, height_str = aspectratio.split(":")
    return float(width_str), float(height_str)


def resolve_field_edge(
    edge_value: int | float | str,
    edge_name: str,
    fontsize: float | None,
    aspectratio: str,
    detection: DetectionResult,
    resolved_canvases: dict[str, ResolvedCanvas],
    scoped_detection: DetectionResult | None = None,
    context: str = "",
) -> float:
    """Resolve a field edge value, including em offset expressions.

    Handles all edge value types plus em offsets. For em offsets,
    computes: offset_pct = em_count * fontsize / page_dimension * 100
    where page_dimension is height for top/bottom, width for left/right.

    Canvas-scoped references (prefixed with @) use scoped_detection
    which contains only elements within the field's canvas bounds.

    Args:
        edge_value: The raw edge value.
        edge_name: Which edge (left/right/top/bottom) for axis selection.
        fontsize: Effective font size for em computation.
        aspectratio: Blueprint aspect ratio string (e.g., "603:783").
        detection: Full detection result for global line reference lookups.
        resolved_canvases: Resolved canvases for canvas ref lookups.
        scoped_detection: Canvas-scoped detection for @ references.

    Returns:
        The resolved absolute page percentage.

    Raises:
        ValueError: If em offset used without fontsize, or invalid expression.

    Requirements: blueprint-fields 5.1, 5.2, 5.3, 5.4, 5.5, 5.8, 5.9, 12.2
    """
    if isinstance(edge_value, (int, float)):
        return resolve_edge_value(edge_value, detection, resolved_canvases, context)

    # Handle @ prefix for canvas-scoped references
    is_scoped = edge_value.startswith(CANVAS_SCOPED_PREFIX)
    if is_scoped:
        edge_value = edge_value[len(CANVAS_SCOPED_PREFIX):]
        if scoped_detection is None:
            raise ValueError(
                f"Canvas-scoped reference '@{edge_value}' used but "
                f"no scoped detection available"
            )

    active_detection = scoped_detection if is_scoped else detection

    em_match = re.match(EM_OFFSET_PATTERN, edge_value)
    if em_match:
        base_ref = em_match.group(1).strip()
        operator = em_match.group(2)
        em_count = float(em_match.group(3))

        if fontsize is None:
            raise ValueError(
                f"Em offset expression '{edge_value}' requires a fontsize, "
                f"but no fontsize is available"
            )

        base_value = resolve_edge_value(base_ref, active_detection, resolved_canvases, context)
        width, height = _parse_aspectratio(aspectratio)
        page_dimension = height if edge_name in ("top", "bottom") else width
        offset_percentage = em_count * fontsize / page_dimension * 100

        if operator == "+":
            return base_value + offset_percentage
        return base_value - offset_percentage

    return resolve_edge_value(edge_value, active_detection, resolved_canvases, context)


def compute_top_default(
    bottom_abs: float,
    fontsize: float,
    aspectratio: str,
) -> float:
    """Compute the default top edge as bottom - 1em.

    Args:
        bottom_abs: Resolved bottom edge in absolute page percentage.
        fontsize: Effective font size in points.
        aspectratio: Blueprint aspect ratio string.

    Returns:
        The computed top edge in absolute page percentage.

    Requirements: blueprint-fields 8.1, 8.3
    """
    _width, height = _parse_aspectratio(aspectratio)
    return bottom_abs - (fontsize / height * 100)


def resolve_fields(
    fields: list[FieldEntry],
    field_styles: dict[str, dict],
    resolved_canvases: dict[str, ResolvedCanvas],
    detection: DetectionResult,
    aspectratio: str,
) -> list[ResolvedField]:
    """Resolve all fields to parent-relative coordinates.

    For each field:
    1. Resolve styles to get effective properties
    2. Validate required properties (canvas, type)
    3. Resolve edge values (including em offsets)
    4. Apply top-edge default if needed
    5. Convert to parent-relative coordinates

    Args:
        fields: Ordered list of field entries.
        field_styles: Merged field style definitions.
        resolved_canvases: All resolved canvases.
        detection: Detection result for edge resolution.
        aspectratio: Blueprint aspect ratio for em computation.

    Returns:
        Ordered list of resolved fields with parent-relative coordinates.

    Raises:
        ValueError: If fields have missing required properties,
            invalid references, or resolution errors.

    Requirements: blueprint-fields 7.3, 7.4, 7.10, 7.11, 7.12, 8.1, 8.2, 8.3, 9.6
    """
    resolved: list[ResolvedField] = []

    for field_entry in fields:
        effective = resolve_field_styles(field_entry, field_styles)
        try:
            resolved_field = _resolve_single_field(
                field_entry, effective, resolved_canvases, detection, aspectratio,
            )
        except ValueError as exc:
            raise ValueError(
                f"Field '{field_entry.name}': {exc}",
            ) from exc
        resolved.append(resolved_field)

    return resolved


def _resolve_single_field(
    field_entry: FieldEntry,
    effective: dict,
    resolved_canvases: dict[str, ResolvedCanvas],
    detection: DetectionResult,
    aspectratio: str,
) -> ResolvedField:
    """Resolve a single field entry to a ResolvedField."""
    canvas_name = effective.get("canvas")
    field_type = effective.get("type")

    _validate_field_properties(field_entry.name, canvas_name, field_type, resolved_canvases)

    scoped_detection = _build_scoped_detection(
        detection, resolved_canvases[canvas_name],
    )

    fontsize = effective.get("fontsize")
    edges = _resolve_field_edges(
        field_entry.name, effective, fontsize, aspectratio,
        detection, resolved_canvases, scoped_detection,
    )

    _validate_field_within_canvas(
        field_entry.name, edges, resolved_canvases[canvas_name],
        {k: effective.get(k) for k in ("left", "right", "top", "bottom")},
        detection,
    )

    coords = _convert_field_to_parent_relative(
        field_entry.name, canvas_name, edges, resolved_canvases,
    )

    return ResolvedField(
        name=field_entry.name,
        canvas=canvas_name,
        type=field_type,
        param=field_entry.param,
        value=field_entry.value,
        x=coords["x"],
        y=coords["y"],
        x2=coords.get("x2"),
        y2=coords.get("y2"),
        font=effective.get("font"),
        fontsize=fontsize,
        fontweight=effective.get("fontweight"),
        align=effective.get("align"),
        color=effective.get("color"),
        linewidth=effective.get("linewidth"),
        size=effective.get("size"),
        lines=effective.get("lines"),
        trigger=field_entry.trigger,
    )


def _validate_field_properties(
    field_name: str,
    canvas_name: str | None,
    field_type: str | None,
    resolved_canvases: dict[str, ResolvedCanvas],
) -> None:
    """Validate required field properties after style resolution."""
    if canvas_name is None:
        raise ValueError(
            f"Field '{field_name}' has no effective 'canvas' after style resolution"
        )
    if field_type is None:
        raise ValueError(
            f"Field '{field_name}' has no effective 'type' after style resolution"
        )
    if field_type not in VALID_FIELD_TYPES:
        raise ValueError(
            f"Field '{field_name}' has invalid type '{field_type}'; "
            f"valid types are {sorted(VALID_FIELD_TYPES)}"
        )
    if canvas_name not in resolved_canvases:
        raise ValueError(
            f"Field '{field_name}' references undefined canvas '{canvas_name}'"
        )


def _resolve_field_edges(
    field_name: str,
    effective: dict,
    fontsize: float | None,
    aspectratio: str,
    detection: DetectionResult,
    resolved_canvases: dict[str, ResolvedCanvas],
    scoped_detection: DetectionResult | None = None,
) -> dict[str, float]:
    """Resolve all four edges for a field, applying top-edge default."""
    edges: dict[str, float] = {}

    for edge_name in ("left", "right", "bottom"):
        raw = effective.get(edge_name)
        if raw is not None:
            edges[edge_name] = resolve_field_edge(
                raw, edge_name, fontsize, aspectratio,
                detection, resolved_canvases, scoped_detection,
                context=f"field '{field_name}', edge '{edge_name}'",
            )

    raw_top = effective.get("top")
    if raw_top is not None:
        edges["top"] = resolve_field_edge(
            raw_top, "top", fontsize, aspectratio,
            detection, resolved_canvases, scoped_detection,
            context=f"field '{field_name}', edge 'top'",
        )
    else:
        if "bottom" not in edges or fontsize is None:
            raise ValueError(
                f"Field '{field_name}' omits 'top' but lacks "
                f"'bottom' or 'fontsize'"
            )
        edges["top"] = compute_top_default(edges["bottom"], fontsize, aspectratio)

    return edges


def _find_elements_within_canvas(
    category: str,
    detection: DetectionResult,
    canvas: ResolvedCanvas,
) -> list[str]:
    """List elements of a detection category that fall within a canvas.

    Returns formatted strings like 'h_rule[3]: y=93.6%' for each
    element whose primary axis value is within the canvas bounds.
    """
    elements = getattr(detection, category, [])
    horizontal_categories = {"h_thin", "h_bar", "h_rule"}
    results = []

    for i, elem in enumerate(elements):
        if category in horizontal_categories:
            if (canvas.top <= elem.y <= canvas.bottom
                    and elem.x2 >= canvas.left and elem.x <= canvas.right):
                results.append(
                    f"  {category}[{i}]: y={elem.y:.1f}%, "
                    f"x={elem.x:.1f}%..x2={elem.x2:.1f}%"
                )
        elif category == "grey_box":
            if (canvas.left <= elem.x <= canvas.right
                    and canvas.top <= elem.y <= canvas.bottom):
                results.append(
                    f"  {category}[{i}]: x={elem.x:.1f}%..x2={elem.x2:.1f}%, "
                    f"y={elem.y:.1f}%..y2={elem.y2:.1f}%"
                )
        else:
            if (canvas.left <= elem.x <= canvas.right
                    and elem.y2 >= canvas.top and elem.y <= canvas.bottom):
                results.append(
                    f"  {category}[{i}]: x={elem.x:.1f}%, "
                    f"y={elem.y:.1f}%..y2={elem.y2:.1f}%"
                )

    return results


def _extract_reference_category(raw_edge: int | float | str | None) -> str | None:
    """Extract the detection category from a raw edge value string.

    Returns the category name (e.g., 'h_rule') or None if the edge
    is numeric, a canvas reference, or None.
    """
    if raw_edge is None or isinstance(raw_edge, (int, float)):
        return None
    edge_str = str(raw_edge)
    # Strip em offset: "h_rule[0] - 1em" → "h_rule[0]"
    em_match = re.match(EM_OFFSET_PATTERN, edge_str)
    if em_match:
        edge_str = em_match.group(1).strip()
    # Match line/secondary axis reference
    line_match = re.match(
        r"^(h_thin|h_bar|h_rule|v_thin|v_bar|grey_box)\[", edge_str,
    )
    if line_match:
        return line_match.group(1)
    return None


def _validate_field_within_canvas(
    field_name: str,
    edges: dict[str, float],
    canvas: ResolvedCanvas,
    raw_edges: dict[str, int | float | str | None],
    detection: DetectionResult,
) -> None:
    """Raise ValueError if any resolved field edge falls outside its canvas.

    Compares the field's absolute-percentage edges against the canvas
    bounds. A small tolerance (0.1%) accounts for floating-point
    rounding in em offset computations.

    When a violation is detected and the offending edge references a
    detection element (e.g., h_rule[0]), the error message lists all
    elements of that category that fall within the canvas bounds.

    Args:
        field_name: The field name (for error messages).
        edges: Resolved absolute-percentage edges (left, right, top, bottom).
        canvas: The resolved canvas the field belongs to.
        raw_edges: The raw (pre-resolution) edge values for hint extraction.
        detection: The detection result for listing in-canvas elements.

    Raises:
        ValueError: If any field edge is outside the canvas bounds.
    """
    tolerance = 0.1
    checks = [
        ("left", edges.get("left"), canvas.left, "left of"),
        ("right", edges.get("right"), canvas.right, "right of"),
        ("top", edges.get("top"), canvas.top, "above"),
        ("bottom", edges.get("bottom"), canvas.bottom, "below"),
    ]
    for edge_name, field_val, canvas_val, direction in checks:
        if field_val is None:
            continue
        out_of_bounds = False
        if edge_name in ("left", "top"):
            out_of_bounds = field_val < canvas_val - tolerance
        else:
            out_of_bounds = field_val > canvas_val + tolerance

        if out_of_bounds:
            msg = (
                f"Field '{field_name}' edge '{edge_name}' ({field_val:.1f}%) "
                f"is {direction} canvas '{canvas.name}' "
                f"({edge_name}={canvas_val:.1f}%)"
            )
            category = _extract_reference_category(raw_edges.get(edge_name))
            if category is not None:
                within = _find_elements_within_canvas(category, detection, canvas)
                if within:
                    msg += (
                        f"\n{category} elements within '{canvas.name}' "
                        f"(y={canvas.top:.1f}%..{canvas.bottom:.1f}%):\n"
                        + "\n".join(within)
                    )
                else:
                    msg += (
                        f"\nNo {category} elements found within "
                        f"'{canvas.name}' bounds"
                    )
            raise ValueError(msg)


def _convert_field_to_parent_relative(
    field_name: str,
    canvas_name: str,
    edges: dict[str, float],
    resolved_canvases: dict[str, ResolvedCanvas],
) -> dict[str, float | str]:
    """Convert absolute field edges to parent-relative coordinates."""
    temp_canvas = ResolvedCanvas(
        name=field_name,
        left=edges.get("left", 0.0),
        right=edges.get("right", 0.0),
        top=edges.get("top", 0.0),
        bottom=edges.get("bottom", 0.0),
        parent=canvas_name,
    )
    return convert_to_parent_relative(temp_canvas, resolved_canvases)
