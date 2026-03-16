"""Checkbox detection and label extraction from PDF chronicle sheets.

Detects checkbox Unicode characters (□, ☐, ☑, ☒) in PDF text and extracts
their associated text labels by scanning subsequent words on the page.

Requirements: refactor-chronicle2layout 2.3, 4.4, 5.6, 8.3, 8.4, 8.5
"""

from __future__ import annotations

import sys

import fitz  # PyMuPDF

CHECKBOX_CHARS: list[str] = ['□', '☐', '☑', '☒']
"""Unicode characters recognized as checkboxes in PDF text."""


def image_checkboxes(
    pdf_path: str,
    debug_dir: str | None = None,
    region_pct: list[float] | None = None,
) -> list[dict]:
    """Detect checkbox positions by finding □ characters in the PDF text.

    Opens the last page of the PDF (to handle full module PDFs) and scans
    for checkbox Unicode characters, returning their positions as percentages
    of the canvas (or page) dimensions.

    # Simplified signature: unused parameters (zoom, min_box_size_pct,
    # max_box_size_pct, max_fill_ratio, min_mean_inner, min_box_size_px,
    # max_box_size_px) were removed because checkbox detection is purely
    # text-based and does not use image analysis thresholds.

    Args:
        pdf_path: Path to the PDF file.
        debug_dir: Optional directory for debug output. When set, prints
            checkbox count and coordinates to stderr.
        region_pct: Optional [x0, y0, x1, y1] in percent to crop before
            detection. Coordinates are returned relative to this region.

    Returns:
        List of dicts, each with keys ``x``, ``y``, ``x2``, ``y2``
        representing checkbox bounding boxes as percentages of the region
        (or full page when *region_pct* is ``None``).
    """
    doc = fitz.open(pdf_path)
    if doc.page_count < 1:
        return []
    page = doc.load_page(doc.page_count - 1)

    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height

    if region_pct:
        rx0, ry0, rx1, ry1 = region_pct
        region_x0 = (rx0 / 100.0) * page_width
        region_y0 = (ry0 / 100.0) * page_height
        region_x2 = (rx1 / 100.0) * page_width
        region_y2 = (ry1 / 100.0) * page_height
        region_width = region_x2 - region_x0
        region_height = region_y2 - region_y0
    else:
        region_x0 = 0
        region_y0 = 0
        region_x2 = page_width
        region_y2 = page_height
        region_width = page_width
        region_height = page_height

    words_on_page = page.get_text("words")

    checkboxes: list[dict] = []
    for word_data in words_on_page:
        x0, y0, x1, y1, text, block_no, line_no, word_no = word_data

        if text.strip() in CHECKBOX_CHARS or text.startswith('□'):
            if (x0 >= region_x0 and x1 <= region_x2
                    and y0 >= region_y0 and y1 <= region_y2):
                rel_x = ((x0 - region_x0) / region_width) * 100.0
                rel_y = ((y0 - region_y0) / region_height) * 100.0
                rel_x2 = ((x1 - region_x0) / region_width) * 100.0
                rel_y2 = ((y1 - region_y0) / region_height) * 100.0

                checkboxes.append({
                    "x": round(rel_x, 3),
                    "y": round(rel_y, 3),
                    "x2": round(rel_x2, 3),
                    "y2": round(rel_y2, 3),
                })

    if debug_dir:
        print(f"DEBUG: Found {len(checkboxes)} checkbox characters", file=sys.stderr)
        for i, cb in enumerate(checkboxes, 1):
            print(
                f"DEBUG: Checkbox {i}: x={cb['x']:.3f}, y={cb['y']:.3f}, "
                f"x2={cb['x2']:.3f}, y2={cb['y2']:.3f}",
                file=sys.stderr,
            )

    return checkboxes


def extract_checkbox_labels(
    pdf_path: str,
    checkboxes: list[dict],
    region_pct: list[float],
    debug_dir: str | None = None,
) -> list[dict]:
    """Extract text labels for checkboxes by finding text following □ characters.

    For each detected checkbox, scans subsequent words on the page until a
    delimiter is reached (another checkbox character, the word "or", or
    trailing punctuation) and assembles the collected words into a label.

    Args:
        pdf_path: Path to the PDF file.
        checkboxes: List of checkbox dicts with ``x``, ``y``, ``x2``, ``y2``
            keys (percentages of the region).
        region_pct: Region as [x0, y0, x1, y1] in percent of the page.
        debug_dir: Optional directory for debug output.

    Returns:
        List of dicts, each with ``checkbox`` (the original checkbox dict)
        and ``label`` (the extracted text string).
    """
    if not checkboxes:
        return []

    doc = fitz.open(pdf_path)
    if doc.page_count < 1:
        return []
    page = doc.load_page(doc.page_count - 1)

    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height

    rx0, ry0, rx1, ry1 = region_pct
    region_x0 = (rx0 / 100.0) * page_width
    region_y0 = (ry0 / 100.0) * page_height
    region_x2 = (rx1 / 100.0) * page_width
    region_y2 = (ry1 / 100.0) * page_height

    words_on_page = page.get_text("words")

    checkbox_positions: list[int] = []
    for idx, word_data in enumerate(words_on_page):
        x0, y0, x1, y1, text, block_no, line_no, word_no = word_data

        if text.strip() in CHECKBOX_CHARS or '□' in text:
            if (x0 >= region_x0 and x1 <= region_x2
                    and y0 >= region_y0 and y1 <= region_y2):
                checkbox_positions.append(idx)

    results: list[dict] = []
    for i, cb_idx in enumerate(checkbox_positions):
        next_cb_idx = (
            checkbox_positions[i + 1]
            if i + 1 < len(checkbox_positions)
            else len(words_on_page)
        )

        cb_text = words_on_page[cb_idx][4]
        label_words: list[str] = []

        # If checkbox has text attached after the □, extract it
        if cb_text.startswith('□') and len(cb_text) > 1:
            label_words.append(cb_text[1:])

        for word_idx in range(cb_idx + 1, next_cb_idx):
            word_data = words_on_page[word_idx]
            x0, y0, x1, y1, text, block_no, line_no, word_no = word_data

            if (x0 >= region_x0 and x1 <= region_x2
                    and y0 >= region_y0 and y1 <= region_y2):
                if any(cb_char in text for cb_char in CHECKBOX_CHARS):
                    break
                if text.lower() == 'or':
                    break
                label_words.append(text)
                if text.endswith(',') or text.endswith('.'):
                    break

        label = ' '.join(label_words).strip()

        # Remove trailing punctuation unless it's an ellipsis or number abbreviation
        if label.endswith('.') or label.endswith(','):
            if not (label.endswith('...') or (len(label) > 2 and label[-2:-1].isdigit())):
                label = label[:-1].strip()

        results.append({
            'checkbox': checkboxes[i] if i < len(checkboxes) else None,
            'label': label,
        })

    return results
