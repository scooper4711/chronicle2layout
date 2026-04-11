"""Checkbox Unicode detection and label extraction.

Detects checkbox Unicode characters (□, ☐, ☑, ☒) in the PDF text layer
and extracts their associated text labels by scanning subsequent words
until a delimiter is reached.

Requirements: layout-generator 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2,
    7.3, 7.4, 7.5, 7.6
"""

from __future__ import annotations

from pathlib import Path

import fitz

CHECKBOX_CHARS: list[str] = ['□', '☐', '☑', '☒', '▫']
"""Unicode characters recognized as checkboxes."""


def _contains_checkbox_char(text: str) -> bool:
    """Check if any character in the text is a checkbox character."""
    return any(ch in text for ch in CHECKBOX_CHARS)


def _is_in_region(
    x0: float, y0: float, x1: float, y1: float,
    region_x0: float, region_y0: float,
    region_x2: float, region_y2: float,
) -> bool:
    """Check if a word bounding box falls within the specified region."""
    return (x0 >= region_x0 and x1 <= region_x2
            and y0 >= region_y0 and y1 <= region_y2)


def _compute_region_bounds(
    region_pct: list[float] | None,
    page_width: float,
    page_height: float,
) -> tuple[float, float, float, float, float, float]:
    """Convert region percentages to absolute coordinates.

    Returns:
        Tuple of (region_x0, region_y0, region_x2, region_y2,
        region_width, region_height).
    """
    if region_pct:
        rx0, ry0, rx1, ry1 = region_pct
        region_x0 = (rx0 / 100.0) * page_width
        region_y0 = (ry0 / 100.0) * page_height
        region_x2 = (rx1 / 100.0) * page_width
        region_y2 = (ry1 / 100.0) * page_height
    else:
        region_x0 = 0
        region_y0 = 0
        region_x2 = page_width
        region_y2 = page_height

    region_width = region_x2 - region_x0
    region_height = region_y2 - region_y0
    return region_x0, region_y0, region_x2, region_y2, region_width, region_height


def _to_region_relative_pct(
    x0: float, y0: float, x1: float, y1: float,
    region_x0: float, region_y0: float,
    region_width: float, region_height: float,
) -> dict:
    """Convert absolute coordinates to region-relative percentage bbox."""
    return {
        "x": round(((x0 - region_x0) / region_width) * 100.0, 3),
        "y": round(((y0 - region_y0) / region_height) * 100.0, 3),
        "x2": round(((x1 - region_x0) / region_width) * 100.0, 3),
        "y2": round(((y1 - region_y0) / region_height) * 100.0, 3),
    }


def detect_checkboxes(
    pdf_path: str | Path,
    region_pct: list[float] | None = None,
) -> list[dict]:
    """Detect checkbox Unicode characters in the PDF text layer.

    Scans the last page for checkbox characters, filters to the
    region, and returns bounding boxes as region-relative percentages.

    Args:
        pdf_path: Path to the PDF file.
        region_pct: Optional [x0, y0, x1, y1] as absolute page
            percentages. When None, coordinates are page-relative.

    Returns:
        List of dicts with 'x', 'y', 'x2', 'y2' keys.

    Requirements: layout-generator 6.1, 6.2, 6.3, 6.4, 6.5
    """
    doc = fitz.open(str(pdf_path))
    if doc.page_count < 1:
        return []
    page = doc.load_page(doc.page_count - 1)

    page_width = page.rect.width
    page_height = page.rect.height

    region_x0, region_y0, region_x2, region_y2, region_width, region_height = (
        _compute_region_bounds(region_pct, page_width, page_height)
    )

    checkboxes: list[dict] = []
    for word_data in page.get_text("words"):
        x0, y0, x1, y1, text = word_data[0], word_data[1], word_data[2], word_data[3], word_data[4]

        if not _contains_checkbox_char(text):
            continue
        if not _is_in_region(x0, y0, x1, y1, region_x0, region_y0, region_x2, region_y2):
            continue

        cb_x0 = x0
        cb_x1 = x1
        if len(text) > 1:
            char_width = (x1 - x0) / len(text)
            for ch in CHECKBOX_CHARS:
                idx = text.find(ch)
                if idx >= 0:
                    cb_x0 = x0 + char_width * idx
                    cb_x1 = cb_x0 + char_width
                    break

        checkboxes.append(
            _to_region_relative_pct(
                cb_x0, y0, cb_x1, y1,
                region_x0, region_y0, region_width, region_height,
            )
        )

    return checkboxes


def _extract_text_after_checkbox(text: str) -> str | None:
    """Extract text following the first checkbox character in a word.

    Returns the remaining text after the checkbox symbol, or None
    if the checkbox character is the entire word.
    """
    for ch in CHECKBOX_CHARS:
        idx = text.find(ch)
        if idx >= 0:
            remainder = text[idx + len(ch):]
            if remainder:
                return remainder
    return None


def _collect_label_words(
    words_on_page: list,
    start_idx: int,
    end_idx: int,
    cb_text: str,
    region_x0: float,
    region_y0: float,
    region_x2: float,
    region_y2: float,
) -> list[str]:
    """Collect label words following a checkbox until a delimiter is reached."""
    label_words: list[str] = []

    trailing_text = _extract_text_after_checkbox(cb_text)
    if trailing_text:
        label_words.append(trailing_text)

    for word_idx in range(start_idx + 1, end_idx):
        word_data = words_on_page[word_idx]
        x0, y0, x1, y1, text = word_data[0], word_data[1], word_data[2], word_data[3], word_data[4]

        if not _is_in_region(x0, y0, x1, y1, region_x0, region_y0, region_x2, region_y2):
            continue
        if _contains_checkbox_char(text):
            break
        if text.lower() == 'or':
            break
        label_words.append(text)
        if text.endswith(',') or text.endswith('.'):
            break

    return label_words


def _clean_label(label_words: list[str]) -> str:
    """Join label words and strip trailing punctuation.

    Preserves ellipsis ("...") and decimal numbers (digit before period).
    """
    label = ' '.join(label_words).strip()
    if label.endswith('.') or label.endswith(','):
        if not label.endswith('...') and not (len(label) >= 2 and label[-2].isdigit()):
            label = label[:-1].strip()
    return label


def extract_checkbox_labels(
    pdf_path: str | Path,
    checkboxes: list[dict],
    region_pct: list[float],
) -> list[dict]:
    """Extract text labels for detected checkboxes.

    Scans words following each checkbox character until a delimiter
    (another checkbox, "or", trailing punctuation).

    Args:
        pdf_path: Path to the PDF file.
        checkboxes: Checkbox dicts from detect_checkboxes.
        region_pct: [x0, y0, x1, y1] as absolute page percentages.

    Returns:
        List of dicts with 'checkbox' and 'label' keys.

    Requirements: layout-generator 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    """
    if not checkboxes:
        return []

    doc = fitz.open(str(pdf_path))
    if doc.page_count < 1:
        return []
    page = doc.load_page(doc.page_count - 1)

    page_width = page.rect.width
    page_height = page.rect.height

    rx0, ry0, rx1, ry1 = region_pct
    region_x0 = (rx0 / 100.0) * page_width
    region_y0 = (ry0 / 100.0) * page_height
    region_x2 = (rx1 / 100.0) * page_width
    region_y2 = (ry1 / 100.0) * page_height

    words_on_page = page.get_text("words")

    checkbox_positions: list[int] = []
    for idx, word_data in enumerate(words_on_page):
        x0, y0, x1, y1, text = word_data[0], word_data[1], word_data[2], word_data[3], word_data[4]
        if _contains_checkbox_char(text):
            if _is_in_region(x0, y0, x1, y1, region_x0, region_y0, region_x2, region_y2):
                checkbox_positions.append(idx)

    results: list[dict] = []
    for i, cb_idx in enumerate(checkbox_positions):
        next_cb_idx = (
            checkbox_positions[i + 1]
            if i + 1 < len(checkbox_positions)
            else len(words_on_page)
        )

        cb_text = words_on_page[cb_idx][4]
        label_words = _collect_label_words(
            words_on_page, cb_idx, next_cb_idx, cb_text,
            region_x0, region_y0, region_x2, region_y2,
        )
        label = _clean_label(label_words)

        results.append({
            'checkbox': checkboxes[i] if i < len(checkboxes) else None,
            'label': label,
        })

    return results
