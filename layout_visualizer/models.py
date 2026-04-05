"""Data models for canvas regions and resolved pixel rectangles."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CanvasRegion:
    """A canvas region with percentage-based coordinates.

    Attributes:
        name: Unique canvas name (e.g., "main", "summary").
        x: Left edge as percentage of parent (0-100).
        y: Top edge as percentage of parent (0-100).
        x2: Right edge as percentage of parent (0-100).
        y2: Bottom edge as percentage of parent (0-100).
        parent: Name of parent canvas, or None for page-level.
    """

    name: str
    x: float
    y: float
    x2: float
    y2: float
    parent: str | None = None


@dataclass(frozen=True)
class PixelRect:
    """A rectangle in absolute pixel coordinates.

    Attributes:
        name: Canvas region name.
        x: Left edge in pixels.
        y: Top edge in pixels.
        x2: Right edge in pixels.
        y2: Bottom edge in pixels.
        parent: Name of parent canvas, or None.
    """

    name: str
    x: float
    y: float
    x2: float
    y2: float
    parent: str | None = None
