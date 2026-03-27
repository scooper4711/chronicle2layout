"""Region merging for text and image detection results.

Combines text-based and image-based region detections into final
percentage-based canvas coordinates, preferring image boundaries
for edge positions and using text for identity confirmation.
"""

from season_layout_generator.models import CanvasCoordinates, PageRegions

# Regions detected by image analysis (preferred for edge positions).
_IMAGE_REGIONS = frozenset({
    "summary", "items", "rewards", "session_info", "notes",
})

# All sub-regions that live inside the main canvas.
_SUB_REGIONS = (
    "player_info",
    "summary",
    "rewards",
    "items",
    "notes",
    "boons",
    "reputation",
    "session_info",
)


def _pick_region(
    name: str,
    text_regions: dict[str, CanvasCoordinates | None],
    image_regions: dict[str, CanvasCoordinates | None],
) -> CanvasCoordinates | None:
    """Select the best coordinates for a region from both sources.

    For regions where image analysis is available, prefer image-based
    boundaries (they capture visual edges more accurately). Fall back
    to text-based coordinates when image detection returns None.

    For regions only detected by text (player_info, notes, boons,
    reputation), use text coordinates directly.

    Args:
        name: Region name (e.g., "summary", "player_info").
        text_regions: Regions from text extraction.
        image_regions: Regions from image analysis.

    Returns:
        Best available coordinates, or None if neither source detected
        the region.
    """
    image_coords = image_regions.get(name)
    text_coords = text_regions.get(name)

    if name in _IMAGE_REGIONS:
        return image_coords if image_coords is not None else text_coords
    return text_coords


def _infer_main_canvas(
    text_regions: dict[str, CanvasCoordinates | None],
    image_regions: dict[str, CanvasCoordinates | None],
) -> CanvasCoordinates | None:
    """Infer the main content area from all detected regions.

    The main canvas is the bounding box that encloses all detected
    sub-regions. We take the minimum x/y and maximum x2/y2 across
    every non-None region from both sources.

    Args:
        text_regions: Regions from text extraction.
        image_regions: Regions from image analysis.

    Returns:
        Main canvas coordinates as page-relative percentages,
        or None if no regions were detected at all.
    """
    all_coords: list[CanvasCoordinates] = []
    for name in _SUB_REGIONS:
        picked = _pick_region(name, text_regions, image_regions)
        if picked is not None:
            all_coords.append(picked)

    if not all_coords:
        return None

    return CanvasCoordinates(
        x=min(c.x for c in all_coords),
        y=min(c.y for c in all_coords),
        x2=max(c.x2 for c in all_coords),
        y2=max(c.y2 for c in all_coords),
    )


def _to_main_relative(
    coords: CanvasCoordinates,
    main: CanvasCoordinates,
) -> CanvasCoordinates:
    """Convert page-relative coordinates to main-canvas-relative.

    Transforms percentage coordinates from page space into the
    main canvas coordinate system where main's top-left is (0, 0)
    and main's bottom-right is (100, 100).

    Args:
        coords: Page-relative coordinates to convert.
        main: Main canvas in page-relative coordinates.

    Returns:
        Coordinates as percentages relative to the main canvas.
    """
    main_width = main.x2 - main.x
    main_height = main.y2 - main.y

    if main_width <= 0 or main_height <= 0:
        return coords

    return CanvasCoordinates(
        x=_clamp((coords.x - main.x) / main_width * 100.0),
        y=_clamp((coords.y - main.y) / main_height * 100.0),
        x2=_clamp((coords.x2 - main.x) / main_width * 100.0),
        y2=_clamp((coords.y2 - main.y) / main_height * 100.0),
    )


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a value to the range [lo, hi].

    Args:
        value: Value to clamp.
        lo: Lower bound (default 0.0).
        hi: Upper bound (default 100.0).

    Returns:
        Clamped value.
    """
    return max(lo, min(hi, value))


def merge_regions(
    text_regions: dict[str, CanvasCoordinates | None],
    image_regions: dict[str, CanvasCoordinates | None],
    page_width: float,
    page_height: float,
) -> PageRegions:
    """Merge text-based and image-based region detections.

    For each region, combines evidence from both sources. Image-based
    boundaries (black bars, borders) are preferred for edge positions,
    while text-based detection confirms region identity and provides
    fallback coordinates.

    The main canvas is inferred as the bounding box of all detected
    sub-regions. All sub-region coordinates are then converted to
    percentages relative to the main canvas.

    Args:
        text_regions: Regions detected via text extraction.
        image_regions: Regions detected via image analysis.
        page_width: Page width in points (unused, reserved for
            future refinement).
        page_height: Page height in points (unused, reserved for
            future refinement).

    Returns:
        Merged PageRegions with percentage-based coordinates.
        The ``main`` field is relative to the page; all other
        fields are relative to main.

    Requirements: season-layout-generator 16.5, 4.1, 4.2, 5.1, 5.2,
        6.1, 6.2, 7.1, 7.2, 8.1, 8.2, 9.1, 9.2, 10.1, 10.2,
        11.1, 11.2, 11.3, 12.1, 12.2
    """
    main = _infer_main_canvas(text_regions, image_regions)
    if main is None:
        return PageRegions()

    merged: dict[str, CanvasCoordinates | None] = {}
    for name in _SUB_REGIONS:
        picked = _pick_region(name, text_regions, image_regions)
        if picked is not None:
            merged[name] = _to_main_relative(picked, main)
        else:
            merged[name] = None

    return PageRegions(main=main, **merged)

