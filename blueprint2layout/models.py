"""Data models for the blueprint2layout pipeline.

Defines frozen dataclasses for detection results (HorizontalLine,
VerticalLine, GreyBox, DetectionResult) and Blueprint structures
(CanvasEntry, ResolvedCanvas, Blueprint).
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
    """

    y: float
    x: float
    x2: float
    thickness_px: int


@dataclass(frozen=True)
class VerticalLine:
    """A detected vertical line with absolute page percentages.

    Attributes:
        x: Left-edge x position as absolute page percentage.
        y: Top-edge y position as absolute page percentage.
        y2: Bottom-edge y position as absolute page percentage.
        thickness_px: Thickness in pixels at 150 DPI.
    """

    x: float
    y: float
    y2: float
    thickness_px: int


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
class Blueprint:
    """A parsed Blueprint with id, optional parent id, and canvas entries.

    Attributes:
        id: Unique identifier (e.g., "pfs2.season5.blueprint").
        canvases: Ordered list of canvas entries.
        parent: Optional parent Blueprint id for inheritance.
        description: Optional human-readable description.
        flags: Optional metadata flags (e.g., ["hidden"]).
        aspectratio: Optional aspect ratio string (e.g., "603:783").
    """

    id: str
    canvases: list[CanvasEntry]
    parent: str | None = None
    description: str | None = None
    flags: list[str] = field(default_factory=list)
    aspectratio: str | None = None
