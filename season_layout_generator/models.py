"""Data models for the season layout generator.

Defines frozen dataclasses for canvas coordinates, page regions,
PDF analysis results, and variant groups used throughout the
detection and layout generation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanvasCoordinates:
    """Percentage-based coordinates for a canvas region.

    All values are percentages (0-100) relative to the parent canvas.

    Attributes:
        x: Left edge percentage.
        y: Top edge percentage.
        x2: Right edge percentage.
        y2: Bottom edge percentage.

    Requirements: season-layout-generator 4.2, 5.2, 6.2, 7.2, 8.2,
        9.2, 10.2, 11.2, 12.2
    """

    x: float
    y: float
    x2: float
    y2: float


@dataclass(frozen=True)
class PageRegions:
    """Detected canvas regions for a single chronicle PDF page.

    Each region is optional because detection may fail for individual
    regions on individual PDFs.

    Attributes:
        main: Main content area relative to page.
        player_info: Player info area relative to main.
        summary: Adventure summary area relative to main.
        rewards: Rewards/XP/GP area relative to main.
        items: Items list area relative to main.
        notes: Notes area relative to main.
        boons: Boons area relative to main.
        reputation: Reputation area relative to main (may be absent).
        session_info: Session info area relative to main.
    """

    main: CanvasCoordinates | None = None
    player_info: CanvasCoordinates | None = None
    summary: CanvasCoordinates | None = None
    rewards: CanvasCoordinates | None = None
    items: CanvasCoordinates | None = None
    notes: CanvasCoordinates | None = None
    boons: CanvasCoordinates | None = None
    reputation: CanvasCoordinates | None = None
    session_info: CanvasCoordinates | None = None


@dataclass(frozen=True)
class PdfAnalysisResult:
    """Analysis result for a single chronicle PDF.

    Attributes:
        filename: The PDF filename (not full path).
        regions: Detected canvas regions.
    """

    filename: str
    regions: PageRegions


@dataclass(frozen=True)
class VariantGroup:
    """A group of PDFs sharing the same layout template.

    Attributes:
        results: List of PdfAnalysisResult in this variant group.
        consensus: Consensus PageRegions computed from the group.
        first_scenario: Scenario identifier from the first PDF in
            the group (e.g., "4-09"). Used in description for
            non-first variants.
    """

    results: list[PdfAnalysisResult]
    consensus: PageRegions
    first_scenario: str
