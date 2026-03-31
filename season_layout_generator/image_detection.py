"""Image-based region detection using pixel analysis.

Converts chronicle PDF pages to raster images and analyzes pixel
data to detect visual features such as black bars, thick borders,
and grey backgrounds that define canvas region boundaries.

The detection strategy:
1. Convert the PDF page to a grayscale raster image via PyMuPDF.
2. Scan rows for horizontal black bars (high fraction of dark pixels).
3. Scan columns for vertical black borders (sustained dark pixels).
4. Scan rows for grey background regions (session info).
5. Classify detected features into named canvas regions based on
   their spatial position and extent.

Requirements: season-layout-generator 16.1, 16.2, 16.3, 16.4
"""

from __future__ import annotations

import numpy as np
import fitz

from season_layout_generator.models import CanvasCoordinates


# --- Detection thresholds ---

# Maximum pixel value (0-255 grayscale) to classify as black.
BLACK_PIXEL_THRESHOLD: int = 40

# Minimum fraction of a row's pixels that must be black to count
# as a horizontal black bar.
BLACK_BAR_MIN_FRACTION: float = 0.5

# Grey background detection bounds (0-255 grayscale).
GREY_LOWER_BOUND: int = 170
GREY_UPPER_BOUND: int = 240

# Minimum height of a region as a fraction of page height to be
# considered valid (filters out noise).
MIN_REGION_HEIGHT_FRACTION: float = 0.02

# Minimum fraction of a column's pixels that must be black to
# count as a vertical border line.
_VERTICAL_BORDER_MIN_FRACTION: float = 0.25

# Minimum thickness in pixels for a vertical border to be
# considered a thick border (not just an edge artifact).
_MIN_BORDER_THICKNESS_PX: int = 3

# Minimum fraction of grey pixels in a row for grey region
# detection.
_GREY_ROW_MIN_FRACTION: float = 0.3

# Maximum gap in pixels between consecutive rows/columns before
# splitting into separate groups.
_GROUP_GAP_TOLERANCE: int = 3

# Maximum pixel value to classify as a thin grey/dark line (higher
# than BLACK_PIXEL_THRESHOLD to catch grey divider lines up to ~136).
_THIN_LINE_PIXEL_THRESHOLD: int = 150

# Minimum fraction of a column's pixels within the items band that
# must be dark to count as a thin vertical divider line.
_THIN_DIVIDER_MIN_FRACTION: float = 0.5


def _page_to_grayscale(page: fitz.Page) -> tuple[np.ndarray, int, int]:
    """Convert a PDF page to a grayscale numpy array.

    Args:
        page: A PyMuPDF page object.

    Returns:
        Tuple of (grayscale_array, width, height) where the array
        has shape (height, width) with values 0-255.
    """
    pix = page.get_pixmap()
    width, height = pix.width, pix.height
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        height, width, pix.n,
    )
    if pix.n >= 3:
        gray = arr[:, :, :3].mean(axis=2)
    else:
        gray = arr[:, :, 0].astype(np.float64)
    return gray, width, height


def _group_consecutive(
    indices: np.ndarray,
    gap: int = _GROUP_GAP_TOLERANCE,
) -> list[np.ndarray]:
    """Split sorted indices into groups of consecutive values.

    Consecutive values separated by more than ``gap`` pixels start
    a new group.

    Args:
        indices: Sorted 1-D array of integer indices.
        gap: Maximum gap between consecutive indices within a group.

    Returns:
        List of arrays, each containing one group of consecutive
        indices.
    """
    if len(indices) == 0:
        return []
    diffs = np.diff(indices)
    splits = np.nonzero(diffs > gap)[0]
    return list(np.split(indices, splits + 1))


def _find_horizontal_bars(
    gray: np.ndarray,
    height: int,
) -> list[tuple[float, float]]:
    """Find horizontal black bars spanning a significant page width.

    Args:
        gray: Grayscale image array of shape (height, width).
        height: Page height in pixels.

    Returns:
        List of (y_start_pct, y_end_pct) for each detected bar,
        as percentages of page height.
    """
    row_black_frac = (gray < BLACK_PIXEL_THRESHOLD).mean(axis=1)
    bar_rows = np.nonzero(row_black_frac > BLACK_BAR_MIN_FRACTION)[0]
    groups = _group_consecutive(bar_rows)

    bars: list[tuple[float, float]] = []
    for group in groups:
        if len(group) < 1:
            continue
        y_start = float(group[0]) / height * 100.0
        y_end = float(group[-1]) / height * 100.0
        bars.append((y_start, y_end))
    return bars


def _find_vertical_borders(
    gray: np.ndarray,
    width: int,
) -> list[tuple[float, float]]:
    """Find vertical black border lines.

    Args:
        gray: Grayscale image array of shape (height, width).
        width: Page width in pixels.

    Returns:
        List of (x_start_pct, x_end_pct) for each detected vertical
        border, as percentages of page width.
    """
    col_black_frac = (gray < BLACK_PIXEL_THRESHOLD).mean(axis=0)
    border_cols = np.nonzero(
        col_black_frac > _VERTICAL_BORDER_MIN_FRACTION,
    )[0]
    groups = _group_consecutive(border_cols, gap=5)

    borders: list[tuple[float, float]] = []
    for group in groups:
        if len(group) < _MIN_BORDER_THICKNESS_PX:
            continue
        x_start = float(group[0]) / width * 100.0
        x_end = float(group[-1]) / width * 100.0
        borders.append((x_start, x_end))
    return borders


def _find_grey_regions(
    gray: np.ndarray,
    height: int,
) -> list[tuple[float, float]]:
    """Find horizontal bands with a grey background.

    Args:
        gray: Grayscale image array of shape (height, width).
        height: Page height in pixels.

    Returns:
        List of (y_start_pct, y_end_pct) for each grey region,
        as percentages of page height. Only regions taller than
        MIN_REGION_HEIGHT_FRACTION of the page are returned.
    """
    row_grey_frac = (
        (gray >= GREY_LOWER_BOUND) & (gray <= GREY_UPPER_BOUND)
    ).mean(axis=1)
    grey_rows = np.nonzero(row_grey_frac > _GREY_ROW_MIN_FRACTION)[0]
    groups = _group_consecutive(grey_rows, gap=5)

    min_height_px = height * MIN_REGION_HEIGHT_FRACTION
    regions: list[tuple[float, float]] = []
    for group in groups:
        if len(group) < min_height_px:
            continue
        y_start = float(group[0]) / height * 100.0
        y_end = float(group[-1]) / height * 100.0
        regions.append((y_start, y_end))
    return regions


def _find_rewards_border(
    vertical_borders: list[tuple[float, float]],
) -> float | None:
    """Identify the left vertical border of the rewards box.

    The rewards box is on the right side of the page. Its left
    border is the rightmost vertical border that is not at the
    page edge (i.e., not the main content right edge).

    Args:
        vertical_borders: Detected vertical borders as
            (x_start_pct, x_end_pct) pairs.

    Returns:
        The x percentage of the rewards left border, or None if
        no suitable border is found.
    """
    # Filter to borders in the right half but not at the far edge
    candidates = [
        (x_start, x_end)
        for x_start, x_end in vertical_borders
        if 50.0 < x_start < 90.0
    ]
    if not candidates:
        return None
    # Take the leftmost candidate in the right half — this is the
    # rewards box left border
    best = min(candidates, key=lambda b: b[0])
    return best[0]


def _is_partial_width_bar(
    gray: np.ndarray,
    mid_row: int,
    rewards_left_x: float,
    width: int,
) -> bool:
    """Check if a bar is partial width (stops at the rewards border).

    A partial-width bar has high black fraction on the left side of
    the rewards border but low black fraction on the right side.
    This distinguishes the items bar from full-width bars that span
    across the rewards border.

    Args:
        gray: Grayscale image array.
        mid_row: Row index to check.
        rewards_left_x: X percentage of the rewards left border.
        width: Page width in pixels.

    Returns:
        True if the bar is partial width (items-like).
    """
    rewards_col = int(rewards_left_x / 100.0 * width)
    right_slice = gray[mid_row, rewards_col:]
    right_black_frac = (right_slice < BLACK_PIXEL_THRESHOLD).mean()
    # Full-width bars have >30% black on the right; partial bars <20%
    return right_black_frac < 0.20


def _classify_horizontal_bars(
    bars: list[tuple[float, float]],
    gray: np.ndarray,
    width: int,
) -> dict[str, CanvasCoordinates | None]:
    """Classify horizontal bars into named regions.

    Uses the vertical position of each bar to determine which canvas
    region it belongs to. Bars are processed top-to-bottom.

    The classification logic:
    - The first thick bar in the upper portion (<25%) is summary top.
    - The first thick bar above 70% is content bottom.
    - Thick bars in the middle (25-70%) use "last wins" for items_top
      and "first wins" for summary_bottom.

    Args:
        bars: Horizontal bars as (y_start_pct, y_end_pct) pairs.
        gray: Grayscale image array for checking bar extent.
        width: Page width in pixels.

    Returns:
        Dict with detected region coordinates. Keys may include
        ``summary_top``, ``summary_bottom``, ``items_top``,
        ``content_bottom``.
    """
    if not bars:
        return {}

    height = gray.shape[0]
    result: dict[str, CanvasCoordinates | None] = {}

    for y_start, y_end in bars:
        mid_row = int((y_start + y_end) / 2.0 / 100.0 * height)
        mid_row = min(mid_row, height - 1)
        row_data = gray[mid_row, :]
        black_pixels = np.nonzero(row_data < BLACK_PIXEL_THRESHOLD)[0]

        if len(black_pixels) == 0:
            continue

        bar_x_end_pct = float(black_pixels[-1]) / width * 100.0
        bar_x_start_pct = float(black_pixels[0]) / width * 100.0

        _classify_single_bar(
            result, y_start, y_end,
            bar_x_start_pct, bar_x_end_pct,
        )

    return result


def _classify_single_bar(
    result: dict[str, CanvasCoordinates | None],
    y_start: float,
    y_end: float,
    bar_x_start: float,
    bar_x_end: float,
) -> None:
    """Classify a single horizontal bar and add it to the result dict.

    Mutates ``result`` in place. Bars are processed top-to-bottom,
    so later calls can overwrite earlier classifications for keys
    that use the "last wins" strategy (like ``items_top``).

    Args:
        result: Accumulator dict for classified bars.
        y_start: Bar top edge as page percentage.
        y_end: Bar bottom edge as page percentage.
        bar_x_start: Bar left edge as page percentage.
        bar_x_end: Bar right edge as page percentage.
    """
    is_thick = (y_end - y_start) > 0.5

    # Thin line (< 0.5% of page height) — likely a separator
    if not is_thick:
        if y_start > 85.0 and "thin_separator" not in result:
            result["thin_separator"] = CanvasCoordinates(
                x=bar_x_start, y=y_start, x2=bar_x_end, y2=y_end,
            )
        return

    # Full-width thick bar in the upper portion — summary top
    if y_start < 25.0 and "summary_top" not in result:
        result["summary_top"] = CanvasCoordinates(
            x=bar_x_start, y=y_start, x2=bar_x_end, y2=y_end,
        )
        return

    # Full-width thick bar in the lower portion — content bottom
    if y_start > 70.0 and "content_bottom" not in result:
        result["content_bottom"] = CanvasCoordinates(
            x=bar_x_start, y=y_start, x2=bar_x_end, y2=y_end,
        )
        return

    # Thick bar in the middle (25-70%) — candidate for items_top.
    # Use "last wins" so the bar closest to content_bottom is chosen.
    # This handles S3 where a Reputation Gained bar sits above Items.
    # The first bar in this range also serves as the summary bottom.
    if 25.0 <= y_start <= 70.0:
        if "summary_bottom" not in result:
            result["summary_bottom"] = CanvasCoordinates(
                x=bar_x_start, y=y_start, x2=bar_x_end, y2=y_end,
            )
        result["items_top"] = CanvasCoordinates(
            x=bar_x_start, y=y_start, x2=bar_x_end, y2=y_end,
        )


def _find_items_notes_divider(
    gray: np.ndarray,
    items_top_y: float,
    content_bottom_y: float,
    left_x: float,
    rewards_left_x: float,
    width: int,
    height: int,
    vertical_borders: list[tuple[float, float]],
) -> float | None:
    """Find a vertical divider line marking the items right edge.

    Detects vertical lines within the items band that separate items
    from an adjacent region (notes in S4+, purchases in S1-S3). The
    line may be grey (~74-136 pixel value) or black (~0), but must
    not be a known thick page-level border.

    Args:
        gray: Grayscale image array of shape (height, width).
        items_top_y: Y percentage of the items top bar bottom edge.
        content_bottom_y: Y percentage of the content bottom bar.
        left_x: X percentage of the left content edge.
        rewards_left_x: X percentage of the rewards left border.
        width: Page width in pixels.
        height: Page height in pixels.
        vertical_borders: Known thick vertical borders to exclude.

    Returns:
        X percentage of the divider line, or None if not found.
    """
    y_top_px = int((items_top_y + 1.0) / 100.0 * height)
    y_bot_px = int((content_bottom_y - 1.0) / 100.0 * height)
    x_left_px = int((left_x + 2.0) / 100.0 * width)
    x_right_px = int((rewards_left_x - 2.0) / 100.0 * width)

    if y_top_px >= y_bot_px or x_left_px >= x_right_px:
        return None

    band = gray[y_top_px:y_bot_px, x_left_px:x_right_px]
    col_dark = (band < _THIN_LINE_PIXEL_THRESHOLD).mean(axis=0)

    candidates = np.nonzero(col_dark > _THIN_DIVIDER_MIN_FRACTION)[0]
    if len(candidates) == 0:
        return None

    # Filter out columns that overlap with known thick borders.
    border_ranges = [
        (int(x_start / 100.0 * width) - x_left_px,
         int(x_end / 100.0 * width) - x_left_px)
        for x_start, x_end in vertical_borders
    ]

    def _overlaps_border(col_idx: int) -> bool:
        return any(
            start - 3 <= col_idx <= end + 3
            for start, end in border_ranges
        )

    filtered = np.array([
        c for c in candidates if not _overlaps_border(c)
    ])
    if len(filtered) == 0:
        return None

    # Pick the leftmost group — this is the items right edge.
    groups = _group_consecutive(filtered, gap=3)
    if not groups:
        return None

    best_group = groups[0]
    mid_col = int(np.median(best_group)) + x_left_px
    return float(mid_col) / width * 100.0


def _build_notes_coords_side_by_side(
    items_top_y: float,
    content_bottom_y: float,
    divider_x: float,
    rewards_left_x: float,
) -> CanvasCoordinates:
    """Build notes coordinates for side-by-side layout (S4+).

    Notes sits to the right of the divider, sharing the same
    vertical extent as items.

    Args:
        items_top_y: Y percentage of the items top bar.
        content_bottom_y: Y percentage of the content bottom bar.
        divider_x: X percentage of the items/notes divider.
        rewards_left_x: X percentage of the rewards left border.

    Returns:
        CanvasCoordinates for the notes region.
    """
    return CanvasCoordinates(
        x=divider_x,
        y=items_top_y,
        x2=rewards_left_x,
        y2=content_bottom_y,
    )


def _build_notes_coords_stacked(
    content_bottom: CanvasCoordinates,
    session_info_top_y: float | None,
    divider_x: float | None = None,
) -> CanvasCoordinates | None:
    """Build notes coordinates for stacked layout (S1-S3, Bounties).

    Notes sits below items, directly above session info. When a
    vertical divider exists (separating notes from downtime in S2),
    notes is trimmed to the left of the divider. Otherwise it spans
    the full content width.

    Args:
        content_bottom: The content bottom bar coordinates, used
            for the notes top edge and horizontal extent.
        session_info_top_y: Y percentage of the session info top edge.
        divider_x: X percentage of the vertical divider, or None.

    Returns:
        CanvasCoordinates for the notes region, or None if
        session_info is not detected.
    """
    if session_info_top_y is None:
        return None

    right_x = divider_x if divider_x is not None else content_bottom.x2

    return CanvasCoordinates(
        x=content_bottom.x,
        y=content_bottom.y2,
        x2=right_x,
        y2=session_info_top_y,
    )


def _build_summary_coords(
    classified: dict[str, CanvasCoordinates | None],
) -> CanvasCoordinates | None:
    """Build summary region coordinates from classified bars.

    The summary region spans from the summary top bar down to the
    next structural element (secondary bar or items top).

    Args:
        classified: Dict of classified bar coordinates.

    Returns:
        CanvasCoordinates for the summary region, or None.
    """
    summary_top = classified.get("summary_top")
    if summary_top is None:
        return None

    # Bottom edge is the next bar below the summary top
    bottom_y = None
    for key in ("summary_bottom", "items_top", "content_bottom"):
        candidate = classified.get(key)
        if candidate is not None and candidate.y > summary_top.y2:
            bottom_y = candidate.y
            break

    if bottom_y is None:
        return None

    return CanvasCoordinates(
        x=summary_top.x,
        y=summary_top.y,
        x2=summary_top.x2,
        y2=bottom_y,
    )


def _build_items_coords(
    classified: dict[str, CanvasCoordinates | None],
    rewards_left_x: float | None,
    divider_x: float | None = None,
) -> CanvasCoordinates | None:
    """Build items region coordinates from classified bars.

    The items region spans from the items top bar down to the
    content bottom bar. The right edge is bounded by the
    items/notes divider (if present, S4+) or the rewards border.

    Args:
        classified: Dict of classified bar coordinates.
        rewards_left_x: X percentage of the rewards left border.
        divider_x: X percentage of the items/notes divider, or
            None if not detected (stacked layout).

    Returns:
        CanvasCoordinates for the items region, or None.
    """
    items_top = classified.get("items_top")
    content_bottom = classified.get("content_bottom")

    if items_top is None or content_bottom is None:
        return None

    if divider_x is not None:
        right_x = divider_x
    elif rewards_left_x is not None:
        right_x = rewards_left_x
    else:
        right_x = items_top.x2

    return CanvasCoordinates(
        x=items_top.x,
        y=items_top.y,
        x2=right_x,
        y2=content_bottom.y,
    )


def _find_rewards_bottom(
    gray: np.ndarray,
    top_y: float,
    rewards_left_x: float,
    right_edge_x: float,
    height: int,
    width: int,
) -> float | None:
    """Find the bottom bar of the rewards box by scanning its column.

    Scans the rewards column for the first thick horizontal bar
    below the rewards top edge. This bar sits below the last
    rewards field (e.g. Total GP).

    Args:
        gray: Grayscale image array.
        top_y: Y percentage of the rewards top edge.
        rewards_left_x: X percentage of the rewards left border.
        right_edge_x: X percentage of the rewards right edge.
        height: Page height in pixels.
        width: Page width in pixels.

    Returns:
        Y percentage of the bottom bar, or None if not found.
    """
    x_left = int(rewards_left_x / 100.0 * width)
    x_right = int(right_edge_x / 100.0 * width)
    # Start scanning below the top bar (skip 3% to clear it).
    y_start = int((top_y + 3.0) / 100.0 * height)
    y_end = int(0.90 * height)

    if x_left >= x_right or y_start >= y_end:
        return None

    band = gray[y_start:y_end, x_left:x_right]
    row_black = (band < BLACK_PIXEL_THRESHOLD).mean(axis=1)

    # Find the first row with >50% black (a thick bar).
    bar_rows = np.nonzero(row_black > 0.5)[0]
    if len(bar_rows) == 0:
        return None

    # Group consecutive rows and find the first thick group.
    groups = _group_consecutive(bar_rows, gap=3)
    for group in groups:
        bar_height_pct = len(group) / height * 100.0
        if bar_height_pct > 0.5:
            return float(group[-1] + y_start) / height * 100.0

    return None


def _build_rewards_coords(
    classified: dict[str, CanvasCoordinates | None],
    rewards_left_x: float | None,
    right_edge_x: float,
    gray: np.ndarray,
    height: int,
    width: int,
) -> CanvasCoordinates | None:
    """Build rewards region coordinates.

    The rewards box is bounded by the left vertical border, the
    right edge of the main content area, and the horizontal bars
    above and below it. The bottom edge is the first thick bar
    within the rewards column below the top edge.

    Args:
        classified: Dict of classified bar coordinates.
        rewards_left_x: X percentage of the rewards left border.
        right_edge_x: X percentage of the right edge of main content.
        gray: Grayscale image array for scanning the rewards column.
        height: Page height in pixels.
        width: Page width in pixels.

    Returns:
        CanvasCoordinates for the rewards region, or None.
    """
    if rewards_left_x is None:
        return None

    # Top edge: the first bar after summary.
    top_y = None
    for key in ("summary_bottom", "summary_top"):
        candidate = classified.get(key)
        if candidate is not None:
            top_y = candidate.y
            break

    if top_y is None:
        return None

    # Bottom edge: scan the rewards column for the first thick bar
    # below the top edge. This is the bar below Total GP.
    bottom_y = _find_rewards_bottom(
        gray, top_y, rewards_left_x, right_edge_x, height, width,
    )
    if bottom_y is None:
        content_bottom = classified.get("content_bottom")
        bottom_y = content_bottom.y if content_bottom is not None else None

    if bottom_y is None:
        return None

    return CanvasCoordinates(
        x=rewards_left_x,
        y=top_y,
        x2=right_edge_x,
        y2=bottom_y,
    )


def _build_session_info_coords(
    grey_regions: list[tuple[float, float]],
) -> CanvasCoordinates | None:
    """Build session info coordinates from grey background regions.

    The session info region is identified as a grey background band
    in the lower portion of the page (below 85%).

    Args:
        grey_regions: Detected grey regions as (y_start_pct, y_end_pct).

    Returns:
        CanvasCoordinates for the session info region, or None.
    """
    for y_start, y_end in grey_regions:
        if y_start > 85.0:
            return CanvasCoordinates(
                x=0.0, y=y_start, x2=100.0, y2=y_end,
            )
    return None


def _find_main_content_edges(
    bars: list[tuple[float, float]],
    gray: np.ndarray,
    width: int,
    height: int,
) -> float:
    """Determine the right edge of the main content area.

    Uses the horizontal extent of the widest black bar to infer
    the main content right boundary.

    Args:
        bars: Horizontal bars as (y_start_pct, y_end_pct) pairs.
        gray: Grayscale image array.
        width: Page width in pixels.
        height: Page height in pixels.

    Returns:
        The right edge percentage of the main content area.
    """
    best_width = 0.0
    right_edge = 100.0

    for y_start, y_end in bars:
        mid_row = int((y_start + y_end) / 2.0 / 100.0 * height)
        mid_row = min(mid_row, height - 1)
        row_data = gray[mid_row, :]
        black_pixels = np.nonzero(row_data < BLACK_PIXEL_THRESHOLD)[0]

        if len(black_pixels) == 0:
            continue

        bar_left = float(black_pixels[0]) / width * 100.0
        bar_right = float(black_pixels[-1]) / width * 100.0
        bar_width = bar_right - bar_left

        if bar_width > best_width:
            best_width = bar_width
            right_edge = bar_right

    return right_edge


def _build_notes(
    gray: np.ndarray,
    width: int,
    height: int,
    divider_x: float | None,
    items_top: CanvasCoordinates | None,
    items_coords: CanvasCoordinates | None,
    content_bottom: CanvasCoordinates | None,
    session_info: CanvasCoordinates | None,
    search_right_x: float,
    vertical_borders: list[tuple[float, float]],
) -> CanvasCoordinates | None:
    """Determine notes coordinates based on layout type.

    Side-by-side (S4+): notes is right of the grey divider, same
    height as items. Stacked (S1-S3, Bounties): notes is below
    items, above session info, optionally trimmed by a divider
    that extends into the notes band.

    Args:
        gray: Grayscale image array.
        width: Page width in pixels.
        height: Page height in pixels.
        divider_x: X percentage of the items divider, or None.
        items_top: Classified items top bar, or None.
        items_coords: Built items coordinates, or None.
        content_bottom: Classified content bottom bar, or None.
        session_info: Session info coordinates, or None.
        search_right_x: Right boundary for divider search.
        vertical_borders: Known thick vertical borders.

    Returns:
        CanvasCoordinates for the notes region, or None.
    """
    is_side_by_side = _is_side_by_side_layout(
        gray, width, height, divider_x, items_top, content_bottom,
    )

    if is_side_by_side and items_top and content_bottom:
        return _build_notes_coords_side_by_side(
            items_top_y=items_top.y,
            content_bottom_y=content_bottom.y,
            divider_x=divider_x,
            rewards_left_x=search_right_x,
        )

    if items_coords is None or session_info is None or content_bottom is None:
        return None

    # Stacked layout: check if the divider extends into the notes band.
    notes_divider_x = None
    if divider_x is not None:
        notes_divider_x = _find_items_notes_divider(
            gray,
            items_top_y=content_bottom.y2,
            content_bottom_y=session_info.y,
            left_x=content_bottom.x,
            rewards_left_x=search_right_x,
            width=width,
            height=height,
            vertical_borders=vertical_borders,
        )
    return _build_notes_coords_stacked(
        content_bottom=content_bottom,
        session_info_top_y=session_info.y,
        divider_x=notes_divider_x,
    )


def _is_side_by_side_layout(
    gray: np.ndarray,
    width: int,
    height: int,
    divider_x: float | None,
    items_top: CanvasCoordinates | None,
    content_bottom: CanvasCoordinates | None,
) -> bool:
    """Check if the items/notes layout is side-by-side (S4+).

    Distinguishes by checking the median dark pixel value along
    the divider column. Dark grey (40-105) indicates S4+ side-by-side;
    lighter grey (>105) or black (<40) indicates S1-S3 stacked.

    Args:
        gray: Grayscale image array.
        width: Page width in pixels.
        height: Page height in pixels.
        divider_x: X percentage of the divider, or None.
        items_top: Classified items top bar, or None.
        content_bottom: Classified content bottom bar, or None.

    Returns:
        True if the layout is side-by-side.
    """
    if divider_x is None or items_top is None or content_bottom is None:
        return False

    divider_col = int(divider_x / 100.0 * width)
    y_top_px = int((items_top.y2 + 2.0) / 100.0 * height)
    y_bot_px = int((content_bottom.y - 2.0) / 100.0 * height)
    col_vals = gray[y_top_px:y_bot_px, divider_col]
    dark_vals = col_vals[col_vals < _THIN_LINE_PIXEL_THRESHOLD]
    median_dark = (
        float(np.median(dark_vals)) if len(dark_vals) > 0 else 255.0
    )
    return BLACK_PIXEL_THRESHOLD <= median_dark <= 105.0


def extract_image_regions(
    page: fitz.Page,
) -> dict[str, CanvasCoordinates | None]:
    """Extract region boundaries from visual features in the page image.

    Converts the page to a raster image via page.get_pixmap(), then
    analyzes pixel data to detect:

    - Black horizontal bars (Summary top edge, Items top edge)
    - Thick black border lines (Rewards boundaries)
    - Light grey background regions (Session Info)

    Args:
        page: A PyMuPDF page object.

    Returns:
        Dict mapping region names to detected coordinates
        (percentage-based relative to page dimensions), or None
        for undetected regions.

    Requirements: season-layout-generator 16.1, 16.2, 16.3, 16.4
    """
    gray, width, height = _page_to_grayscale(page)

    bars = _find_horizontal_bars(gray, height)
    vertical_borders = _find_vertical_borders(gray, width)
    grey_regions = _find_grey_regions(gray, height)

    rewards_left_x = _find_rewards_border(vertical_borders)
    right_edge = _find_main_content_edges(
        bars, gray, width, height,
    )

    classified = _classify_horizontal_bars(
        bars, gray, width,
    )

    items_top = classified.get("items_top")
    content_bottom = classified.get("content_bottom")
    session_info = _build_session_info_coords(grey_regions)

    # Detect the thin vertical divider within the items band.
    # Works for all seasons: S4+ grey divider, S1-S3 items/purchases
    # border. Uses rewards_left_x or right_edge as the search bound.
    divider_x = None
    search_right_x = rewards_left_x if rewards_left_x is not None else right_edge
    if items_top is not None and content_bottom is not None:
        divider_x = _find_items_notes_divider(
            gray,
            items_top_y=items_top.y2,
            content_bottom_y=content_bottom.y,
            left_x=items_top.x,
            rewards_left_x=search_right_x,
            width=width,
            height=height,
            vertical_borders=vertical_borders,
        )

    items_coords = _build_items_coords(
        classified, rewards_left_x, divider_x,
    )

    notes_coords = _build_notes(
        gray, width, height,
        divider_x, items_top, items_coords, content_bottom,
        session_info, search_right_x, vertical_borders,
    )

    return {
        "summary": _build_summary_coords(classified),
        "items": items_coords,
        "rewards": _build_rewards_coords(
            classified, rewards_left_x, right_edge,
            gray, height, width,
        ),
        "session_info": session_info,
        "notes": notes_coords,
    }
