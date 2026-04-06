"""PDF text line extraction via PyMuPDF.

Opens the last page of a chronicle PDF, filters words to a rectangular
region, groups them into lines by y-coordinate proximity, and returns
percentage-based bounding boxes relative to the extraction region.

Requirements: layout-generator 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
"""

from __future__ import annotations

from pathlib import Path

import fitz

Y_COORDINATE_GROUPING_TOLERANCE: float = 2.0
"""Maximum vertical distance (PDF points) for grouping words into the same line."""


def extract_text_lines(
    pdf_path: str | Path,
    region_pct: list[float],
) -> list[dict]:
    """Extract text lines from a rectangular region of the last PDF page.

    Opens the PDF, filters words to the region, groups by y-coordinate,
    and returns lines with percentage-based bounding boxes relative to
    the region.

    Args:
        pdf_path: Path to the PDF file.
        region_pct: [x0, y0, x1, y1] as absolute page percentages.

    Returns:
        List of dicts with 'text', 'top_left_pct' [x, y],
        'bottom_right_pct' [x, y], sorted top-to-bottom.
        Returns empty list for zero-page PDFs.

    Requirements: layout-generator 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
    """
    doc = fitz.open(str(pdf_path))
    if doc.page_count < 1:
        return []

    page = doc.load_page(doc.page_count - 1)
    page_rect = page.rect

    region_abs = _convert_region_to_absolute(region_pct, page_rect)
    words = page.get_text("words")
    lines_by_y = _group_words_by_line(words, region_abs)

    region_width = region_abs[2] - region_abs[0]
    region_height = region_abs[3] - region_abs[1]

    return _build_line_results(lines_by_y, region_abs, region_width, region_height)


def _convert_region_to_absolute(
    region_pct: list[float],
    page_rect: fitz.Rect,
) -> tuple[float, float, float, float]:
    """Convert percentage-based region to absolute PDF coordinates.

    Args:
        region_pct: [x0, y0, x1, y1] as page percentages (0-100).
        page_rect: The PDF page rectangle.

    Returns:
        Tuple of (x0, y0, x1, y1) in PDF points.
    """
    rx0, ry0, rx1, ry1 = region_pct
    return (
        (rx0 / 100.0) * page_rect.width,
        (ry0 / 100.0) * page_rect.height,
        (rx1 / 100.0) * page_rect.width,
        (ry1 / 100.0) * page_rect.height,
    )


def _group_words_by_line(
    words: list[tuple],
    region_abs: tuple[float, float, float, float],
) -> dict[float, list[dict]]:
    """Filter words to a region and group into lines by y-coordinate.

    Words within Y_COORDINATE_GROUPING_TOLERANCE of an existing line's
    y-coordinate are merged into that line.

    Args:
        words: Raw word tuples from PyMuPDF's page.get_text("words").
        region_abs: (x0, y0, x1, y1) absolute region bounds in PDF points.

    Returns:
        Dict mapping y-coordinate keys to lists of word dicts.
    """
    region_x0, region_y0, region_x1, region_y1 = region_abs
    lines: dict[float, list[dict]] = {}

    for word_data in words:
        x0, y0, x1, y1, text = word_data[0], word_data[1], word_data[2], word_data[3], word_data[4]

        if not (x0 >= region_x0 and x1 <= region_x1
                and y0 >= region_y0 and y1 <= region_y1):
            continue

        matching_y = _find_matching_line_y(y0, lines)
        if matching_y is None:
            matching_y = y0
            lines[matching_y] = []

        lines[matching_y].append({"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1})

    return lines


def _find_matching_line_y(
    y0: float,
    lines: dict[float, list[dict]],
) -> float | None:
    """Return an existing line key within tolerance of y0, or None.

    Args:
        y0: The y-coordinate to match.
        lines: Existing line groups keyed by y-coordinate.

    Returns:
        The matching y-coordinate key, or None if no match.
    """
    for existing_y in lines:
        if abs(y0 - existing_y) <= Y_COORDINATE_GROUPING_TOLERANCE:
            return existing_y
    return None


def _build_line_results(
    lines_by_y: dict[float, list[dict]],
    region_abs: tuple[float, float, float, float],
    region_width: float,
    region_height: float,
) -> list[dict]:
    """Convert grouped word lines into region-relative percentage results.

    Joins words into text, computes bounding boxes as percentages of the
    extraction region, sorts top-to-bottom, and skips bare "items" headers.

    Args:
        lines_by_y: Dict mapping y-coordinates to word dicts.
        region_abs: (x0, y0, x1, y1) absolute region bounds in PDF points.
        region_width: Width of the region in PDF points.
        region_height: Height of the region in PDF points.

    Returns:
        Sorted list of line dicts with 'text', 'top_left_pct', 'bottom_right_pct'.
    """
    region_x0, region_y0 = region_abs[0], region_abs[1]
    results: list[dict] = []

    for y_coord in sorted(lines_by_y.keys()):
        words = lines_by_y[y_coord]
        if not words:
            continue

        words.sort(key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in words)

        if text.lower().strip() in ("items", "items:"):
            continue

        x0 = min(w["x0"] for w in words)
        y0 = min(w["y0"] for w in words)
        x1 = max(w["x1"] for w in words)
        y1 = max(w["y1"] for w in words)

        results.append({
            "text": text,
            "top_left_pct": [
                round(((x0 - region_x0) / region_width) * 100.0, 3),
                round(((y0 - region_y0) / region_height) * 100.0, 3),
            ],
            "bottom_right_pct": [
                round(((x1 - region_x0) / region_width) * 100.0, 3),
                round(((y1 - region_y0) / region_height) * 100.0, 3),
            ],
        })

    return results
