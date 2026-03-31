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

    The horizontal extent is derived from the summary bar (which
    spans the full content width within the page margins). The
    vertical extent is the bounding box of all detected sub-regions.

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

    # Use summary bar for horizontal extent (it spans the content
    # area within margins). Fall back to bounding box if no summary.
    summary = _pick_region("summary", text_regions, image_regions)
    if summary is not None:
        x = summary.x
        x2 = summary.x2
    else:
        x = min(c.x for c in all_coords)
        x2 = max(c.x2 for c in all_coords)

    return CanvasCoordinates(
        x=x,
        y=min(c.y for c in all_coords),
        x2=x2,
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


def _refine_boons(
    merged: dict[str, CanvasCoordinates | None],
    text_regions: dict[str, CanvasCoordinates | None],
    image_regions: dict[str, CanvasCoordinates | None],
    main: CanvasCoordinates,
) -> None:
    """Expand boons width and height using structural regions.

    The boons text detection only captures the label. The actual
    boons canvas spans from the content left edge to the rewards
    left border. The bottom edge extends to whichever region sits
    directly below boons: reputation (Bounties, S2, S3) or items
    (Quests, S1, S4+).

    Args:
        merged: Merged regions dict (main-relative). Modified in place.
        text_regions: Text-detected regions (page-relative).
        image_regions: Image-detected regions (page-relative).
        main: Main canvas coordinates (page-relative).
    """
    boons = merged.get("boons")
    if boons is None:
        return

    summary_img = image_regions.get("summary")
    rewards_img = image_regions.get("rewards")

    # Left edge: summary left or content left.
    left_x = summary_img.x if summary_img is not None else main.x

    # Right edge: rewards left border from image detection when
    # available (S4+). Otherwise use the items divider/border which
    # marks the right edge of the left content column (S1-S3, Bounties).
    if rewards_img is not None:
        right_x = rewards_img.x
    else:
        items_img = image_regions.get("items")
        if items_img is not None:
            right_x = items_img.x2
        elif summary_img is not None:
            right_x = summary_img.x2
        else:
            return

    main_width = main.x2 - main.x
    main_height = main.y2 - main.y
    if main_width <= 0 or main_height <= 0:
        return

    rel_left = _clamp((left_x - main.x) / main_width * 100.0)
    rel_right = _clamp((right_x - main.x) / main_width * 100.0)

    # Bottom edge: extend to the top of the next region below boons.
    # Use raw text positions to find reputation or items, whichever
    # is closer below the boons label.
    bottom_y = boons.y2
    items_img = image_regions.get("items")
    rep_txt = text_regions.get("reputation")

    candidates: list[float] = []
    if items_img is not None:
        candidates.append(
            _clamp((items_img.y - main.y) / main_height * 100.0),
        )
    if rep_txt is not None:
        rep_top_rel = _clamp(
            (rep_txt.y - main.y) / main_height * 100.0,
        )
        # Only use reputation if it's below boons.
        if rep_top_rel > boons.y:
            candidates.append(rep_top_rel)

    # Pick the closest region below boons.
    below = [c for c in candidates if c > boons.y]
    if below:
        bottom_y = min(below)

    merged["boons"] = CanvasCoordinates(
        x=rel_left,
        y=boons.y,
        x2=rel_right,
        y2=bottom_y,
    )


def _refine_reputation(
    merged: dict[str, CanvasCoordinates | None],
    image_regions: dict[str, CanvasCoordinates | None],
    main: CanvasCoordinates,
) -> None:
    """Expand reputation width and height using structural regions.

    The reputation text detection only captures the label. The actual
    canvas depends on position:
    - Above items (S1-S3, Bounties): same width as boons, extends
      down to items top.
    - Below items (S4+, Quests): spans full content width, extends
      down to session info top.

    Args:
        merged: Merged regions dict (main-relative). Modified in place.
        image_regions: Image-detected regions (page-relative).
        main: Main canvas coordinates (page-relative).
    """
    reputation = merged.get("reputation")
    if reputation is None:
        return

    boons = merged.get("boons")
    items_img = image_regions.get("items")
    session_info_img = image_regions.get("session_info")

    main_height = main.y2 - main.y
    main_width = main.x2 - main.x
    if main_height <= 0 or main_width <= 0:
        return

    items_top_rel = None
    if items_img is not None:
        items_top_rel = _clamp(
            (items_img.y - main.y) / main_height * 100.0,
        )

    # Determine if reputation is in the boons area (between summary
    # bottom and items top) or elsewhere. Only extend when it's
    # clearly in the boons band.
    summary_img = image_regions.get("summary")
    summary_bottom_rel = None
    if summary_img is not None:
        summary_bottom_rel = _clamp(
            (summary_img.y2 - main.y) / main_height * 100.0,
        )

    is_in_boons_band = (
        items_top_rel is not None
        and summary_bottom_rel is not None
        and reputation.y >= summary_bottom_rel - 2.0
        and reputation.y < items_top_rel
    )

    is_below_items = (
        items_top_rel is not None
        and reputation.y >= items_top_rel
    )

    if is_in_boons_band:
        # Between boons and items: match boons width, extend to items.
        left_x = boons.x if boons is not None else reputation.x
        right_x = boons.x2 if boons is not None else reputation.x2
        bottom_y = items_top_rel
    elif is_below_items:
        # Below items: span full content width, extend to session info.
        left_x = 0.0
        right_x = 100.0
        if session_info_img is not None:
            bottom_y = _clamp(
                (session_info_img.y - main.y) / main_height * 100.0,
            )
        else:
            bottom_y = reputation.y2
    else:
        # Player info band (S1): left edge at player_info right,
        # right edge at main right. Keep text-detected height.
        player_info = merged.get("player_info")
        left_x = player_info.x2 if player_info is not None else reputation.x
        right_x = 100.0
        bottom_y = reputation.y2

    merged["reputation"] = CanvasCoordinates(
        x=left_x,
        y=reputation.y,
        x2=right_x,
        y2=bottom_y,
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

    _refine_boons(merged, text_regions, image_regions, main)
    _refine_reputation(merged, image_regions, main)

    return PageRegions(main=main, **merged)

