"""Structural element detection via pixel analysis.

Detects six categories of structural elements from a cleaned chronicle
page image: horizontal thin lines, horizontal thick bars, grey horizontal
rules, vertical thin lines, vertical thick bars, and grey filled boxes.
Each category is sorted by its primary axis and uses zero-based indexing.
"""

import numpy as np

from collections import deque

from blueprint2layout.models import DetectionResult, GreyBox, HorizontalLine, VerticalLine

# Detection thresholds as named constants
BLACK_PIXEL_THRESHOLD = 50
THIN_LINE_MAX_THICKNESS = 5
HORIZONTAL_MIN_WIDTH_RATIO = 0.05
VERTICAL_MIN_HEIGHT_RATIO = 0.03
LINE_GROUPING_TOLERANCE = 5
GREY_RULE_GROUPING_TOLERANCE = 3
GREY_RULE_MIN_VALUE = 50
GREY_RULE_MAX_VALUE = 200
GREY_RULE_DEDUP_TOLERANCE = 0.5
GREY_BOX_MIN_CHANNEL = 220
GREY_BOX_MAX_CHANNEL = 240
GREY_BOX_CHANNEL_DIFF_LIMIT = 8
GREY_BOX_BLOCK_SIZE = 10
GREY_BOX_BLOCK_FILL_THRESHOLD = 0.5
GREY_BOX_MIN_BLOCKS = 3
GREY_BOX_MIN_AREA = 500


def _find_all_grey_runs(
    row: np.ndarray, min_value: int, max_value: int, min_length: int
) -> list[tuple[int, int, int]]:
    """Find all runs of consecutive grey pixels in a row exceeding min_length.

    Args:
        row: 1D grayscale pixel array for a single row.
        min_value: Minimum grayscale value (inclusive) for grey.
        max_value: Maximum grayscale value (inclusive) for grey.
        min_length: Minimum run length to include.

    Returns:
        List of (run_length, leftmost_pixel, rightmost_pixel) tuples.
        Empty list if no qualifying runs exist.
    """
    is_grey = (row >= min_value) & (row <= max_value)
    if not np.any(is_grey):
        return []

    runs = []
    current_length = 0
    current_start = 0

    for i, grey in enumerate(is_grey):
        if grey:
            if current_length == 0:
                current_start = i
            current_length += 1
        else:
            if current_length > min_length:
                runs.append((current_length, current_start, i - 1))
            current_length = 0

    if current_length > min_length:
        runs.append((current_length, current_start, current_start + current_length - 1))

    return runs


def _find_longest_grey_run(
    row: np.ndarray, min_value: int, max_value: int
) -> tuple[int, int, int]:
    """Find the longest run of consecutive grey pixels in a row.

    Args:
        row: 1D grayscale pixel array for a single row.
        min_value: Minimum grayscale value (inclusive) for grey.
        max_value: Maximum grayscale value (inclusive) for grey.

    Returns:
        Tuple of (run_length, leftmost_pixel, rightmost_pixel).
        Returns (0, 0, 0) if no qualifying grey pixels exist.
    """
    is_grey = (row >= min_value) & (row <= max_value)
    if not np.any(is_grey):
        return (0, 0, 0)

    best_length = 0
    best_start = 0
    current_length = 0
    current_start = 0

    for i, grey in enumerate(is_grey):
        if grey:
            if current_length == 0:
                current_start = i
            current_length += 1
        else:
            if current_length > best_length:
                best_length = current_length
                best_start = current_start
            current_length = 0

    if current_length > best_length:
        best_length = current_length
        best_start = current_start

    return (best_length, best_start, best_start + best_length - 1)


def _find_longest_black_run(row: np.ndarray, threshold: int) -> tuple[int, int, int]:
    """Find the longest run of consecutive black pixels in a row.

    Args:
        row: 1D grayscale pixel array for a single row.
        threshold: Grayscale value below which a pixel is black.

    Returns:
        Tuple of (run_length, leftmost_pixel, rightmost_pixel).
        Returns (0, 0, 0) if no black pixels exist.
    """
    is_black = row < threshold
    if not np.any(is_black):
        return (0, 0, 0)

    best_length = 0
    best_start = 0
    current_length = 0
    current_start = 0

    for i, black in enumerate(is_black):
        if black:
            if current_length == 0:
                current_start = i
            current_length += 1
        else:
            if current_length > best_length:
                best_length = current_length
                best_start = current_start
            current_length = 0

    if current_length > best_length:
        best_length = current_length
        best_start = current_start

    return (best_length, best_start, best_start + best_length - 1)


def detect_horizontal_black_lines(
    grayscale: np.ndarray,
) -> tuple[list[HorizontalLine], list[HorizontalLine]]:
    """Detect horizontal black lines and classify as thin or bar.

    Scans each row for runs of black pixels (grayscale < 50) spanning
    more than 5% of page width. Groups consecutive qualifying rows
    within 5px tolerance. Classifies by thickness: <= 5px is thin,
    > 5px is bar.

    Args:
        grayscale: Grayscale image array, shape (height, width).

    Returns:
        A tuple of (h_thin, h_bar) lists, each sorted by y ascending.

    Requirements: chronicle-blueprints 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    """
    height, width = grayscale.shape
    min_run_length = int(width * HORIZONTAL_MIN_WIDTH_RATIO)

    qualifying_rows = _scan_qualifying_rows(grayscale, min_run_length)
    groups = _group_consecutive_rows(qualifying_rows)
    return _classify_line_groups(groups, height, width)


def _scan_qualifying_rows(
    grayscale: np.ndarray, min_run_length: int
) -> list[tuple[int, int, int]]:
    """Scan all rows and return those with a black run exceeding the minimum.

    Args:
        grayscale: Grayscale image array, shape (height, width).
        min_run_length: Minimum consecutive black pixel count.

    Returns:
        List of (row_index, leftmost_pixel, rightmost_pixel) tuples
        for rows that qualify.
    """
    height = grayscale.shape[0]
    qualifying = []

    for row_idx in range(height):
        run_length, left, right = _find_longest_black_run(
            grayscale[row_idx], BLACK_PIXEL_THRESHOLD
        )
        if run_length > min_run_length:
            qualifying.append((row_idx, left, right))

    return qualifying


def _group_consecutive_rows(
    qualifying_rows: list[tuple[int, int, int]],
) -> list[list[tuple[int, int, int]]]:
    """Group qualifying rows where gaps are within the grouping tolerance.

    Args:
        qualifying_rows: Sorted list of (row_index, left, right) tuples.

    Returns:
        List of groups, where each group is a list of row tuples.
    """
    if not qualifying_rows:
        return []

    groups: list[list[tuple[int, int, int]]] = []
    current_group = [qualifying_rows[0]]

    for row_data in qualifying_rows[1:]:
        previous_row_idx = current_group[-1][0]
        current_row_idx = row_data[0]

        if current_row_idx - previous_row_idx <= LINE_GROUPING_TOLERANCE:
            current_group.append(row_data)
        else:
            groups.append(current_group)
            current_group = [row_data]

    groups.append(current_group)
    return groups


def _classify_line_groups(
    groups: list[list[tuple[int, int, int]]], height: int, width: int
) -> tuple[list[HorizontalLine], list[HorizontalLine]]:
    """Classify grouped rows into thin lines or thick bars.

    Args:
        groups: List of row groups from _group_consecutive_rows.
        height: Image height in pixels.
        width: Image width in pixels.

    Returns:
        Tuple of (h_thin, h_bar) sorted by y ascending.
    """
    h_thin: list[HorizontalLine] = []
    h_bar: list[HorizontalLine] = []

    for group in groups:
        top_row = group[0][0]
        bottom_row = group[-1][0]
        leftmost = min(entry[1] for entry in group)
        rightmost = max(entry[2] for entry in group)
        thickness = bottom_row - top_row + 1

        line = HorizontalLine(
            y=round(top_row / height * 100, 1),
            x=round(leftmost / width * 100, 1),
            x2=round(rightmost / width * 100, 1),
            thickness_px=thickness,
            y2=round((bottom_row + 1) / height * 100, 1),
        )

        if thickness <= THIN_LINE_MAX_THICKNESS:
            h_thin.append(line)
        else:
            h_bar.append(line)

    h_thin.sort(key=lambda line: line.y)
    h_bar.sort(key=lambda line: line.y)

    return (h_thin, h_bar)


def _find_longest_black_run_column(
    column: np.ndarray, threshold: int
) -> tuple[int, int, int]:
    """Find the longest run of consecutive black pixels in a column.

    Args:
        column: 1D grayscale pixel array for a single column.
        threshold: Grayscale value below which a pixel is black.

    Returns:
        Tuple of (run_length, topmost_pixel, bottommost_pixel).
        Returns (0, 0, 0) if no black pixels exist.
    """
    is_black = column < threshold
    if not np.any(is_black):
        return (0, 0, 0)

    best_length = 0
    best_start = 0
    current_length = 0
    current_start = 0

    for i, black in enumerate(is_black):
        if black:
            if current_length == 0:
                current_start = i
            current_length += 1
        else:
            if current_length > best_length:
                best_length = current_length
                best_start = current_start
            current_length = 0

    if current_length > best_length:
        best_length = current_length
        best_start = current_start

    return (best_length, best_start, best_start + best_length - 1)


def _scan_qualifying_columns(
    grayscale: np.ndarray, min_run_length: int
) -> list[tuple[int, int, int]]:
    """Scan all columns and return those with a black run exceeding the minimum.

    Args:
        grayscale: Grayscale image array, shape (height, width).
        min_run_length: Minimum consecutive black pixel count.

    Returns:
        List of (col_index, topmost_pixel, bottommost_pixel) tuples
        for columns that qualify.
    """
    width = grayscale.shape[1]
    qualifying = []

    for col_idx in range(width):
        run_length, top, bottom = _find_longest_black_run_column(
            grayscale[:, col_idx], BLACK_PIXEL_THRESHOLD
        )
        if run_length > min_run_length:
            qualifying.append((col_idx, top, bottom))

    return qualifying


def _group_consecutive_columns(
    qualifying_columns: list[tuple[int, int, int]],
) -> list[list[tuple[int, int, int]]]:
    """Group qualifying columns where gaps are within the grouping tolerance.

    Args:
        qualifying_columns: Sorted list of (col_index, top, bottom) tuples.

    Returns:
        List of groups, where each group is a list of column tuples.
    """
    if not qualifying_columns:
        return []

    groups: list[list[tuple[int, int, int]]] = []
    current_group = [qualifying_columns[0]]

    for col_data in qualifying_columns[1:]:
        previous_col_idx = current_group[-1][0]
        current_col_idx = col_data[0]

        if current_col_idx - previous_col_idx <= LINE_GROUPING_TOLERANCE:
            current_group.append(col_data)
        else:
            groups.append(current_group)
            current_group = [col_data]

    groups.append(current_group)
    return groups


def _classify_vertical_line_groups(
    groups: list[list[tuple[int, int, int]]], height: int, width: int
) -> tuple[list[VerticalLine], list[VerticalLine]]:
    """Classify grouped columns into thin lines or thick bars.

    Args:
        groups: List of column groups from _group_consecutive_columns.
        height: Image height in pixels.
        width: Image width in pixels.

    Returns:
        Tuple of (v_thin, v_bar) sorted by x ascending.
    """
    v_thin: list[VerticalLine] = []
    v_bar: list[VerticalLine] = []

    for group in groups:
        leftmost_col = group[0][0]
        rightmost_col = group[-1][0]
        topmost = min(entry[1] for entry in group)
        bottommost = max(entry[2] for entry in group)
        thickness = rightmost_col - leftmost_col + 1

        line = VerticalLine(
            x=round(leftmost_col / width * 100, 1),
            y=round(topmost / height * 100, 1),
            y2=round(bottommost / height * 100, 1),
            thickness_px=thickness,
            x2=round((rightmost_col + 1) / width * 100, 1),
        )

        if thickness <= THIN_LINE_MAX_THICKNESS:
            v_thin.append(line)
        else:
            v_bar.append(line)

    v_thin.sort(key=lambda line: line.x)
    v_bar.sort(key=lambda line: line.x)

    return (v_thin, v_bar)


def detect_vertical_black_lines(
    grayscale: np.ndarray,
) -> tuple[list[VerticalLine], list[VerticalLine]]:
    """Detect vertical black lines and classify as thin or bar.

    Scans each column for runs of black pixels (grayscale < 50) spanning
    more than 3% of page height. Groups consecutive qualifying columns
    within 5px tolerance. Classifies by thickness: <= 5px is thin,
    > 5px is bar.

    Args:
        grayscale: Grayscale image array, shape (height, width).

    Returns:
        A tuple of (v_thin, v_bar) lists, each sorted by x ascending.

    Requirements: chronicle-blueprints 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """
    height, width = grayscale.shape
    min_run_length = int(height * VERTICAL_MIN_HEIGHT_RATIO)

    qualifying_columns = _scan_qualifying_columns(grayscale, min_run_length)
    groups = _group_consecutive_columns(qualifying_columns)
    return _classify_vertical_line_groups(groups, height, width)


def _scan_qualifying_grey_rows(
    grayscale: np.ndarray, min_run_length: int
) -> list[tuple[int, int, int]]:
    """Scan all rows and return all grey runs exceeding the minimum.

    Returns multiple entries per row when a row contains several
    separate grey segments (e.g., field separator lines).

    Args:
        grayscale: Grayscale image array, shape (height, width).
        min_run_length: Minimum consecutive grey pixel count.

    Returns:
        List of (row_index, leftmost_pixel, rightmost_pixel) tuples
        for all qualifying runs, sorted by row then left position.
    """
    height = grayscale.shape[0]
    qualifying = []

    for row_idx in range(height):
        runs = _find_all_grey_runs(
            grayscale[row_idx], GREY_RULE_MIN_VALUE,
            GREY_RULE_MAX_VALUE, min_run_length,
        )
        for _length, left, right in runs:
            qualifying.append((row_idx, left, right))

    return qualifying


def _ranges_overlap(left_a: int, right_a: int, left_b: int, right_b: int) -> bool:
    """Check if two horizontal pixel ranges overlap.

    Uses a small tolerance (10px) to allow for slight misalignment
    between rows of the same grey line segment.
    """
    tolerance = 10
    return left_a <= right_b + tolerance and left_b <= right_a + tolerance


def _group_rows_with_tolerance(
    qualifying_rows: list[tuple[int, int, int]],
    tolerance: int,
) -> list[list[tuple[int, int, int]]]:
    """Group qualifying rows by vertical proximity and horizontal overlap.

    Rows are grouped when they are within the vertical tolerance AND
    their x-ranges overlap. This ensures that separate grey segments
    on the same row (e.g., field separator lines) become distinct groups.

    Args:
        qualifying_rows: Sorted list of (row_index, left, right) tuples.
        tolerance: Maximum gap in pixels between consecutive rows.

    Returns:
        List of groups, where each group is a list of row tuples.
    """
    if not qualifying_rows:
        return []

    groups: list[list[tuple[int, int, int]]] = []

    for row_data in qualifying_rows:
        row_idx, left, right = row_data
        merged = False

        for group in groups:
            last_row_idx = group[-1][0]
            if row_idx - last_row_idx > tolerance:
                continue
            group_left = min(entry[1] for entry in group)
            group_right = max(entry[2] for entry in group)
            if _ranges_overlap(left, right, group_left, group_right):
                group.append(row_data)
                merged = True
                break

        if not merged:
            groups.append([row_data])

    return groups


def _build_horizontal_lines_from_groups(
    groups: list[list[tuple[int, int, int]]], height: int, width: int
) -> list[HorizontalLine]:
    """Convert row groups into HorizontalLine instances.

    Args:
        groups: List of row groups.
        height: Image height in pixels.
        width: Image width in pixels.

    Returns:
        List of HorizontalLine instances (unsorted).
    """
    lines: list[HorizontalLine] = []

    for group in groups:
        top_row = group[0][0]
        bottom_row = group[-1][0]
        leftmost = min(entry[1] for entry in group)
        rightmost = max(entry[2] for entry in group)
        thickness = bottom_row - top_row + 1

        lines.append(HorizontalLine(
            y=round(top_row / height * 100, 1),
            x=round(leftmost / width * 100, 1),
            x2=round(rightmost / width * 100, 1),
            thickness_px=thickness,
            y2=round((bottom_row + 1) / height * 100, 1),
        ))

    return lines


def _is_near_black_line(
    grey_y: float,
    black_lines: list[HorizontalLine],
    tolerance: float,
) -> bool:
    """Check if a grey line's y is within tolerance of any black line.

    Args:
        grey_y: The grey line's y position as absolute percentage.
        black_lines: List of black horizontal lines to check against.
        tolerance: Maximum y-distance in percentage points.

    Returns:
        True if the grey line overlaps with a black line.
    """
    return any(abs(grey_y - bl.y) < tolerance for bl in black_lines)


def detect_grey_rules(
    grayscale: np.ndarray,
    h_thin: list[HorizontalLine],
    h_bar: list[HorizontalLine],
) -> list[HorizontalLine]:
    """Detect grey horizontal rule lines, deduplicating against black lines.

    Scans each row for runs of medium-grey pixels (grayscale 50-200)
    spanning more than 5% of page width. Groups within 3px tolerance.
    Discards any grey line whose y is within 0.5 percentage points
    of an existing h_thin or h_bar entry.

    Args:
        grayscale: Grayscale image array, shape (height, width).
        h_thin: Already-detected horizontal thin lines.
        h_bar: Already-detected horizontal thick bars.

    Returns:
        List of grey horizontal rules sorted by y ascending.

    Requirements: chronicle-blueprints 4.1, 4.2, 4.3, 4.4, 4.5
    """
    height, width = grayscale.shape
    min_run_length = int(width * HORIZONTAL_MIN_WIDTH_RATIO)

    qualifying_rows = _scan_qualifying_grey_rows(grayscale, min_run_length)
    groups = _group_rows_with_tolerance(
        qualifying_rows, GREY_RULE_GROUPING_TOLERANCE
    )
    candidates = _build_horizontal_lines_from_groups(groups, height, width)

    all_black_lines = list(h_thin) + list(h_bar)
    deduplicated = [
        line for line in candidates
        if not _is_near_black_line(line.y, all_black_lines, GREY_RULE_DEDUP_TOLERANCE)
    ]

    deduplicated.sort(key=lambda line: line.y)
    return deduplicated


def _build_structural_grey_mask(rgb: np.ndarray) -> np.ndarray:
    """Create a boolean mask of structural grey pixels.

    A pixel is structural grey when all three RGB channels are in
    [220, 240] and the max-min channel difference is less than 8.

    Args:
        rgb: RGB image array, shape (height, width, 3).

    Returns:
        Boolean array of shape (height, width).
    """
    channel_min = rgb.min(axis=2)
    channel_max = rgb.max(axis=2)
    in_range = (channel_min >= GREY_BOX_MIN_CHANNEL) & (
        channel_max <= GREY_BOX_MAX_CHANNEL
    )
    low_diff = (channel_max - channel_min) < GREY_BOX_CHANNEL_DIFF_LIMIT
    return in_range & low_diff


def _build_grey_block_grid(
    mask: np.ndarray, block_size: int, fill_threshold: float
) -> np.ndarray:
    """Divide the mask into blocks and classify each as grey or not.

    Args:
        mask: Boolean structural grey pixel mask, shape (height, width).
        block_size: Size of each grid block in pixels.
        fill_threshold: Fraction of grey pixels required to mark a block.

    Returns:
        Boolean 2D array where True means the block is grey.
    """
    height, width = mask.shape
    grid_rows = height // block_size
    grid_cols = width // block_size
    grid = np.zeros((grid_rows, grid_cols), dtype=bool)

    for row in range(grid_rows):
        for col in range(grid_cols):
            y_start = row * block_size
            y_end = y_start + block_size
            x_start = col * block_size
            x_end = x_start + block_size
            block = mask[y_start:y_end, x_start:x_end]
            grey_count = np.count_nonzero(block)
            total = block.size
            if grey_count / total > fill_threshold:
                grid[row, col] = True

    return grid


def _find_valid_neighbors(
    row: int,
    col: int,
    grid: np.ndarray,
    visited: np.ndarray,
) -> list[tuple[int, int]]:
    """Return unvisited grey neighbors of a grid cell (4-connected).

    Args:
        row: Current cell row.
        col: Current cell column.
        grid: Boolean 2D grid of grey blocks.
        visited: Boolean 2D array tracking visited cells.

    Returns:
        List of (row, col) tuples for valid unvisited grey neighbors.
    """
    rows, cols = grid.shape
    neighbors = []
    for delta_row, delta_col in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        neighbor_row = row + delta_row
        neighbor_col = col + delta_col
        if (
            0 <= neighbor_row < rows
            and 0 <= neighbor_col < cols
            and grid[neighbor_row, neighbor_col]
            and not visited[neighbor_row, neighbor_col]
        ):
            neighbors.append((neighbor_row, neighbor_col))
    return neighbors


def _flood_fill_components(
    grid: np.ndarray,
) -> list[list[tuple[int, int]]]:
    """Find connected components of True cells via BFS flood fill.

    Uses 4-connected adjacency (up, down, left, right).

    Args:
        grid: Boolean 2D grid of grey blocks.

    Returns:
        List of components, each a list of (row, col) grid positions.
    """
    rows, cols = grid.shape
    visited = np.zeros_like(grid, dtype=bool)
    components: list[list[tuple[int, int]]] = []

    for row in range(rows):
        for col in range(cols):
            if not (grid[row, col] and not visited[row, col]):
                continue

            component: list[tuple[int, int]] = []
            queue = deque([(row, col)])
            visited[row, col] = True

            while queue:
                current_row, current_col = queue.popleft()
                component.append((current_row, current_col))

                for neighbor in _find_valid_neighbors(
                    current_row, current_col, grid, visited
                ):
                    visited[neighbor[0], neighbor[1]] = True
                    queue.append(neighbor)

            components.append(component)

    return components


def _refine_bounding_box(
    mask: np.ndarray,
    component: list[tuple[int, int]],
    block_size: int,
) -> tuple[int, int, int, int] | None:
    """Refine a component's bounding box at pixel level.

    Scans the structural grey mask within the component's grid bounds
    to find the tightest pixel-level bounding box.

    Args:
        mask: Boolean structural grey pixel mask, shape (height, width).
        component: List of (grid_row, grid_col) positions.
        block_size: Size of each grid block in pixels.

    Returns:
        Tuple of (x1, y1, x2, y2) pixel coordinates, or None if no
        grey pixels found within the region.
    """
    min_grid_row = min(pos[0] for pos in component)
    max_grid_row = max(pos[0] for pos in component)
    min_grid_col = min(pos[1] for pos in component)
    max_grid_col = max(pos[1] for pos in component)

    pixel_y_start = min_grid_row * block_size
    pixel_y_end = (max_grid_row + 1) * block_size
    pixel_x_start = min_grid_col * block_size
    pixel_x_end = (max_grid_col + 1) * block_size

    height, width = mask.shape
    pixel_y_end = min(pixel_y_end, height)
    pixel_x_end = min(pixel_x_end, width)

    region = mask[pixel_y_start:pixel_y_end, pixel_x_start:pixel_x_end]
    grey_positions = np.argwhere(region)

    if len(grey_positions) == 0:
        return None

    y1 = pixel_y_start + int(grey_positions[:, 0].min())
    y2 = pixel_y_start + int(grey_positions[:, 0].max())
    x1 = pixel_x_start + int(grey_positions[:, 1].min())
    x2 = pixel_x_start + int(grey_positions[:, 1].max())

    return (x1, y1, x2, y2)


def detect_grey_boxes(rgb: np.ndarray) -> list[GreyBox]:
    """Detect grey filled rectangles via grid-based flood fill.

    Identifies structural grey pixels (RGB channels each 220-240,
    channel differences < 8). Divides into 10x10 blocks, flood-fills
    connected grey blocks, refines bounding boxes at pixel level,
    and filters by minimum area.

    Args:
        rgb: RGB image array, shape (height, width, 3).

    Returns:
        List of grey boxes sorted by y ascending then x ascending.

    Requirements: chronicle-blueprints 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
    """
    height, width = rgb.shape[:2]

    mask = _build_structural_grey_mask(rgb)
    grid = _build_grey_block_grid(mask, GREY_BOX_BLOCK_SIZE, GREY_BOX_BLOCK_FILL_THRESHOLD)
    components = _flood_fill_components(grid)

    boxes: list[GreyBox] = []
    for component in components:
        if len(component) < GREY_BOX_MIN_BLOCKS:
            continue

        bounds = _refine_bounding_box(mask, component, GREY_BOX_BLOCK_SIZE)
        if bounds is None:
            continue

        x1, y1, x2, y2 = bounds
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        if area < GREY_BOX_MIN_AREA:
            continue

        boxes.append(GreyBox(
            x=round(x1 / width * 100, 1),
            y=round(y1 / height * 100, 1),
            x2=round(x2 / width * 100, 1),
            y2=round(y2 / height * 100, 1),
        ))

    boxes.sort(key=lambda box: (box.y, box.x))
    return boxes


VECTOR_LINE_MAX_WIDTH = 1.0
VECTOR_LINE_DEDUP_TOLERANCE = 0.3


def extract_vector_h_rules(
    pdf_path: str,
    h_thin: list[HorizontalLine],
    h_bar: list[HorizontalLine],
    h_rule: list[HorizontalLine],
) -> list[HorizontalLine]:
    """Extract thin horizontal vector lines from the PDF.

    Finds horizontal line segments in the PDF's vector drawing commands
    that are too thin to survive rasterization (width <= 1pt). Deduplicates
    against already-detected raster lines.

    Args:
        pdf_path: Path to the PDF file.
        h_thin: Already-detected horizontal thin lines.
        h_bar: Already-detected horizontal thick bars.
        h_rule: Already-detected grey horizontal rules.

    Returns:
        List of new HorizontalLine instances not already detected.
    """
    import fitz

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return []

    if doc.page_count == 0:
        doc.close()
        return []

    page = doc[doc.page_count - 1]
    page_width = page.rect.width
    page_height = page.rect.height

    min_width_pts = page_width * HORIZONTAL_MIN_WIDTH_RATIO

    all_existing = list(h_thin) + list(h_bar) + list(h_rule)
    candidates: list[HorizontalLine] = []

    for path in page.get_drawings():
        line_width = path.get("width") or 0
        if line_width > VECTOR_LINE_MAX_WIDTH:
            continue

        for item in path["items"]:
            if item[0] != "l":
                continue
            p1, p2 = item[1], item[2]
            if abs(p1.y - p2.y) > 0.5:
                continue
            span = abs(p2.x - p1.x)
            if span < min_width_pts:
                continue

            x_left = min(p1.x, p2.x)
            x_right = max(p1.x, p2.x)
            y_pct = round(p1.y / page_height * 100, 1)
            x_pct = round(x_left / page_width * 100, 1)
            x2_pct = round(x_right / page_width * 100, 1)

            line = HorizontalLine(
                y=y_pct, x=x_pct, x2=x2_pct, thickness_px=1, y2=y_pct,
            )

            is_duplicate = any(
                abs(line.y - existing.y) < VECTOR_LINE_DEDUP_TOLERANCE
                and abs(line.x - existing.x) < 1.0
                and abs(line.x2 - existing.x2) < 1.0
                for existing in all_existing
            )
            if not is_duplicate:
                candidates.append(line)
                all_existing.append(line)

    doc.close()
    candidates.sort(key=lambda l: (l.y, l.x))
    return candidates


def detect_structures(
    grayscale: np.ndarray,
    rgb: np.ndarray,
    pdf_path: str | None = None,
) -> DetectionResult:
    """Run all detection passes and assemble the complete result.

    Orchestrates horizontal black lines, vertical black lines,
    grey rules (with deduplication), grey boxes, and optionally
    extracts thin vector lines from the PDF that are too thin
    to survive rasterization.

    Args:
        grayscale: Grayscale image array, shape (height, width).
        rgb: RGB image array, shape (height, width, 3).
        pdf_path: Optional path to the PDF for vector line extraction.

    Returns:
        A DetectionResult with all six arrays populated.

    Requirements: chronicle-blueprints 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """
    h_thin, h_bar = detect_horizontal_black_lines(grayscale)
    v_thin, v_bar = detect_vertical_black_lines(grayscale)
    h_rule = detect_grey_rules(grayscale, h_thin, h_bar)
    grey_box = detect_grey_boxes(rgb)

    if pdf_path is not None:
        vector_h_rules = extract_vector_h_rules(pdf_path, h_thin, h_bar, h_rule)
        if vector_h_rules:
            h_rule = list(h_rule) + vector_h_rules
            h_rule.sort(key=lambda line: (line.y, line.x))

    return DetectionResult(
        h_thin=h_thin,
        h_bar=h_bar,
        h_rule=h_rule,
        v_thin=v_thin,
        v_bar=v_bar,
        grey_box=grey_box,
    )
