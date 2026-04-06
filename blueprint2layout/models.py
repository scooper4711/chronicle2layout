"""Data models for the blueprint2layout pipeline.

Defines frozen dataclasses for detection results (HorizontalLine,
VerticalLine, GreyBox, DetectionResult), Blueprint structures
(CanvasEntry, ResolvedCanvas, Blueprint), and field models
(FieldEntry, ResolvedField).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HorizontalLine:
    """A detected horizontal line with absolute page percentages.

    Attributes:
        y: Top-edge y position as absolute page percentage.
        x: Left-edge x position as absolute page percentage.
        x2: Right-edge x position as absolute page percentage.
        thickness_px: Thickness in pixels at 150 DPI.
        y2: Bottom-edge y position as absolute page percentage.
    """

    y: float
    x: float
    x2: float
    thickness_px: int
    y2: float = 0.0


@dataclass(frozen=True)
class VerticalLine:
    """A detected vertical line with absolute page percentages.

    Attributes:
        x: Left-edge x position as absolute page percentage.
        y: Top-edge y position as absolute page percentage.
        y2: Bottom-edge y position as absolute page percentage.
        thickness_px: Thickness in pixels at 150 DPI.
        x2: Right-edge x position as absolute page percentage.
    """

    x: float
    y: float
    y2: float
    thickness_px: int
    x2: float = 0.0


@dataclass(frozen=True)
class GreyBox:
    """A detected grey filled rectangle with absolute page percentages.

    Attributes:
        x: Left-edge x position as absolute page percentage.
        y: Top-edge y position as absolute page percentage.
        x2: Right-edge x position as absolute page percentage.
        y2: Bottom-edge y position as absolute page percentage.
    """

    x: float
    y: float
    x2: float
    y2: float


@dataclass(frozen=True)
class DetectionResult:
    """Complete detection output with six keyed arrays.

    Each array is sorted by its primary axis and uses zero-based indexing.

    Attributes:
        h_thin: Horizontal thin lines (thickness <= 5px), sorted by y.
        h_bar: Horizontal thick bars (thickness > 5px), sorted by y.
        h_rule: Grey horizontal rules, sorted by y.
        v_thin: Vertical thin lines (thickness <= 5px), sorted by x.
        v_bar: Vertical thick bars (thickness > 5px), sorted by x.
        grey_box: Grey filled rectangles, sorted by y then x.
    """

    h_thin: list[HorizontalLine] = field(default_factory=list)
    h_bar: list[HorizontalLine] = field(default_factory=list)
    h_rule: list[HorizontalLine] = field(default_factory=list)
    v_thin: list[VerticalLine] = field(default_factory=list)
    v_bar: list[VerticalLine] = field(default_factory=list)
    grey_box: list[GreyBox] = field(default_factory=list)


@dataclass(frozen=True)
class CanvasEntry:
    """A single canvas entry from a Blueprint file.

    Edge values are stored as-is from JSON: either a numeric literal
    (int/float) or a string (line reference or canvas reference).

    Attributes:
        name: Unique canvas name (e.g., "main", "summary").
        left: Left edge value (numeric, line ref, or canvas ref).
        right: Right edge value.
        top: Top edge value.
        bottom: Bottom edge value.
        parent: Optional parent canvas name for coordinate conversion.
    """

    name: str
    left: int | float | str
    right: int | float | str
    top: int | float | str
    bottom: int | float | str
    parent: str | None = None


@dataclass(frozen=True)
class ResolvedCanvas:
    """A canvas with all edges resolved to absolute page percentages.

    Attributes:
        name: Canvas name.
        left: Left edge as absolute page percentage.
        right: Right edge as absolute page percentage.
        top: Top edge as absolute page percentage.
        bottom: Bottom edge as absolute page percentage.
        parent: Optional parent canvas name.
    """

    name: str
    left: float
    right: float
    top: float
    bottom: float
    parent: str | None = None


@dataclass(frozen=True)
class FieldEntry:
    """A single field entry from a Blueprint file.

    Binds a parameter (or static value) to a positioned region
    within a canvas. Edge values may include em offset expressions.

    Attributes:
        name: Unique field name within the Blueprint.
        canvas: Canvas name this field renders in (after style resolution).
        type: Element type: text, multiline, line, rectangle (after style resolution).
        param: Parameter name this field renders (mutually exclusive with value).
        value: Static text value (mutually exclusive with param).
        left: Left edge value (numeric, line ref, canvas ref, or em offset).
        right: Right edge value.
        top: Top edge value (may be None for auto-default).
        bottom: Bottom edge value.
        font: Font family.
        fontsize: Font size in points.
        fontweight: Font weight (e.g., "bold").
        align: Alignment code (e.g., "CM", "LB").
        color: Color for line/rectangle elements.
        linewidth: Line width for line elements.
        size: Size for checkbox-like elements.
        lines: Number of lines for multiline elements.
        styles: List of field style names to inherit from.
        trigger: Optional trigger parameter for conditional rendering.
    """

    name: str
    canvas: str | None = None
    type: str | None = None
    param: str | None = None
    value: str | None = None
    left: int | float | str | None = None
    right: int | float | str | None = None
    top: int | float | str | None = None
    bottom: int | float | str | None = None
    font: str | None = None
    fontsize: int | float | None = None
    fontweight: str | None = None
    align: str | None = None
    color: str | None = None
    linewidth: int | float | None = None
    size: int | float | None = None
    lines: int | None = None
    styles: list[str] = field(default_factory=list)
    trigger: str | None = None


@dataclass(frozen=True)
class ResolvedField:
    """A field with all edges resolved to parent-relative percentages.

    Contains the fully resolved properties ready for content element
    generation. All edge values are parent-relative percentages within
    the field's canvas.

    Attributes:
        name: Field name.
        canvas: Canvas name.
        type: Element type.
        param: Parameter name (or None).
        value: Static text (or None).
        x: Left edge as parent-relative percentage.
        y: Top edge as parent-relative percentage.
        x2: Right edge as parent-relative percentage.
        y2: Bottom edge as parent-relative percentage.
        font: Font family (or None).
        fontsize: Font size (or None).
        fontweight: Font weight (or None).
        align: Alignment code (or None).
        color: Color (or None).
        linewidth: Line width (or None).
        size: Size (or None).
        lines: Line count (or None).
        trigger: Trigger parameter (or None).
    """

    name: str
    canvas: str
    type: str
    param: str | None = None
    value: str | None = None
    x: float | None = None
    y: float | None = None
    x2: float | None = None
    y2: float | None = None
    font: str | None = None
    fontsize: int | float | None = None
    fontweight: str | None = None
    align: str | None = None
    color: str | None = None
    linewidth: int | float | None = None
    size: int | float | None = None
    lines: int | None = None
    trigger: str | None = None


@dataclass(frozen=True)
class Blueprint:
    """A parsed Blueprint with id, optional parent id, and canvas entries.

    Attributes:
        id: Unique identifier (e.g., "pfs2.season5.blueprint").
        canvases: Ordered list of canvas entries.
        parent: Optional parent Blueprint id for inheritance.
        description: Optional human-readable description.
        flags: Optional metadata flags (e.g., ["hidden"]).
        aspectratio: Optional aspect ratio string (e.g., "603:783").
        parameters: Optional parameter groups dict.
        default_chronicle_location: Optional Foundry VTT path.
        field_styles: Optional dict of style name to style properties.
        fields: Optional ordered list of field entries.
    """

    id: str
    canvases: list[CanvasEntry]
    parent: str | None = None
    description: str | None = None
    flags: list[str] = field(default_factory=list)
    aspectratio: str | None = None
    parameters: dict | None = None
    default_chronicle_location: str | None = None
    field_styles: dict[str, dict] | None = None
    fields: list[FieldEntry] | None = None
