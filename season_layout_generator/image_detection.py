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
_VERTICAL_BORDER_MIN_FRACTION: float = 0.3

# Minimum thickness in pixels for a vertical border to be
# considered a thick border (not just an edge artifact).
_MIN_BORDER_THICKNESS_PX: int = 3

# Minimum fraction of grey pixels in a row for grey region
# detection.
_GREY_ROW_MIN_FRACTION: float = 0.3

# Maximum gap in pixels between consecutive rows/columns before
# splitting into separate groups.
_GROUP_GAP_TOLERANCE: int = 3


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
    rewards_left_x: float | None,
    gray: np.ndarray,
    width: int,
) -> dict[str, CanvasCoordinates | None]:
    """Classify horizontal bars into named regions.

    Uses the vertical position and horizontal extent of each bar
    to determine which canvas region it belongs to.

    The classification logic:
    - The first thick bar in the upper portion is the summary top.
    - A bar that stops at the rewards border (partial width) is the
      items top.
    - The last thick bar before the session info area is the bottom
      boundary of the rewards/items area.

    Args:
        bars: Horizontal bars as (y_start_pct, y_end_pct) pairs.
        rewards_left_x: X percentage of the rewards left border.
        gray: Grayscale image array for checking bar extent.
        width: Page width in pixels.

    Returns:
        Dict with detected region coordinates. Keys may include
        ``summary_top``, ``items_top``, ``content_bottom``.
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

        is_partial = False
        if rewards_left_x is not None and 40.0 < y_start < 70.0:
            is_partial = _is_partial_width_bar(
                gray, mid_row, rewards_left_x, width,
            )

        _classify_single_bar(
            result, y_start, y_end,
            bar_x_start_pct, bar_x_end_pct,
            is_partial=is_partial,
        )

    return result


def _classify_single_bar(
    result: dict[str, CanvasCoordinates | None],
    y_start: float,
    y_end: float,
    bar_x_start: float,
    bar_x_end: float,
    *,
    is_partial: bool = False,
) -> None:
    """Classify a single horizontal bar and add it to the result dict.

    Mutates ``result`` in place.

    Args:
        result: Accumulator dict for classified bars.
        y_start: Bar top edge as page percentage.
        y_end: Bar bottom edge as page percentage.
        bar_x_start: Bar left edge as page percentage.
        bar_x_end: Bar right edge as page percentage.
        is_partial: Whether the bar is partial width (stops at
            the rewards border).
    """
    is_thick = (y_end - y_start) > 0.5

    # Thin line (< 0.5% of page height) — likely a separator
    if not is_thick:
        if y_start > 85.0 and "thin_separator" not in result:
            result["thin_separator"] = CanvasCoordinates(
                x=bar_x_start, y=y_start, x2=bar_x_end, y2=y_end,
            )
        return

    # Partial-width bar stopping at rewards border — items top
    if is_partial and "items_top" not in result:
        result["items_top"] = CanvasCoordinates(
            x=bar_x_start, y=y_start, x2=bar_x_end, y2=y_end,
        )
        return

    # Full-width thick bar in the upper portion — summary top
    if y_start < 30.0 and "summary_top" not in result:
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

    # Full-width thick bar in the middle — secondary bar
    # (could be items/boons boundary or another section)
    if "secondary_bar" not in result:
        result["secondary_bar"] = CanvasCoordinates(
            x=bar_x_start, y=y_start, x2=bar_x_end, y2=y_end,
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
    for key in ("secondary_bar", "items_top", "content_bottom"):
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
) -> CanvasCoordinates | None:
    """Build items region coordinates from classified bars.

    The items region spans from the items top bar down to the
    content bottom bar, bounded on the right by the rewards border.

    Args:
        classified: Dict of classified bar coordinates.
        rewards_left_x: X percentage of the rewards left border.

    Returns:
        CanvasCoordinates for the items region, or None.
    """
    items_top = classified.get("items_top")
    content_bottom = classified.get("content_bottom")

    if items_top is None or content_bottom is None:
        return None

    right_x = rewards_left_x if rewards_left_x is not None else items_top.x2

    return CanvasCoordinates(
        x=items_top.x,
        y=items_top.y,
        x2=right_x,
        y2=content_bottom.y,
    )


def _build_rewards_coords(
    classified: dict[str, CanvasCoordinates | None],
    rewards_left_x: float | None,
    right_edge_x: float,
) -> CanvasCoordinates | None:
    """Build rewards region coordinates.

    The rewards box is bounded by the left vertical border, the
    right edge of the main content area, and the horizontal bars
    above and below it.

    Args:
        classified: Dict of classified bar coordinates.
        rewards_left_x: X percentage of the rewards left border.
        right_edge_x: X percentage of the right edge of main content.

    Returns:
        CanvasCoordinates for the rewards region, or None.
    """
    if rewards_left_x is None:
        return None

    # Top edge: the secondary bar or summary top (whichever is the
    # first full-width bar that aligns with the rewards box top)
    top_y = None
    for key in ("secondary_bar", "summary_top"):
        candidate = classified.get(key)
        if candidate is not None:
            top_y = candidate.y
            break

    # Bottom edge: content bottom bar
    content_bottom = classified.get("content_bottom")
    bottom_y = content_bottom.y if content_bottom is not None else None

    if top_y is None or bottom_y is None:
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
        bars, rewards_left_x, gray, width,
    )

    return {
        "summary": _build_summary_coords(classified),
        "items": _build_items_coords(classified, rewards_left_x),
        "rewards": _build_rewards_coords(
            classified, rewards_left_x, right_edge,
        ),
        "session_info": _build_session_info_coords(grey_regions),
    }
