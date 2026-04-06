"""Property-based tests for layout_generator.checkbox_extractor module.

Uses hypothesis to verify universal properties of checkbox detection
and label cleaning across randomly generated inputs.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import fitz
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from layout_generator.checkbox_extractor import (
    CHECKBOX_CHARS,
    _clean_label,
    detect_checkboxes,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
FONT_SIZE = 12.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_pdf_with_checkboxes(
    tmp_path: Path,
    entries: list[tuple[float, float, str]],
    page_width: float = PAGE_WIDTH,
    page_height: float = PAGE_HEIGHT,
    font_size: float = FONT_SIZE,
    filename: str = "checkboxes.pdf",
) -> Path:
    """Create a single-page PDF with checkbox characters at specific positions.

    Uses TextWriter with the built-in Helvetica font, which supports
    checkbox Unicode glyphs in PyMuPDF.
    """
    pdf_path = tmp_path / filename
    doc = fitz.open()
    page = doc.new_page(width=page_width, height=page_height)

    checkbox_font = fitz.Font("helv")
    tw = fitz.TextWriter(page.rect)

    for x, y, text in entries:
        tw.append(fitz.Point(x, y), text, font=checkbox_font, fontsize=font_size)

    tw.write_text(page)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ---------------------------------------------------------------------------
# Strategies for Property 7
# ---------------------------------------------------------------------------

_MARGIN = 15.0  # percentage margin from page edges for region bounds

# Region strategy: [x0, y0, x1, y1] as page percentages.
_region_pct = st.tuples(
    st.floats(min_value=_MARGIN, max_value=35.0),
    st.floats(min_value=_MARGIN, max_value=35.0),
    st.floats(min_value=65.0, max_value=100.0 - _MARGIN),
    st.floats(min_value=65.0, max_value=100.0 - _MARGIN),
).map(lambda t: [t[0], t[1], t[2], t[3]])

# Checkbox character strategy
_checkbox_char = st.sampled_from(CHECKBOX_CHARS)


def _checkbox_positions_inside_region(
    region_pct: list[float],
) -> st.SearchStrategy[list[tuple[float, float, str]]]:
    """Generate checkbox entries guaranteed to be inside the region.

    Positions are inset from region edges to ensure the full glyph
    bounding box stays within the region.
    """
    x0_abs = (region_pct[0] / 100.0) * PAGE_WIDTH
    y0_abs = (region_pct[1] / 100.0) * PAGE_HEIGHT
    x1_abs = (region_pct[2] / 100.0) * PAGE_WIDTH
    y1_abs = (region_pct[3] / 100.0) * PAGE_HEIGHT

    # Inset to keep glyph bounding boxes inside the region.
    inset = FONT_SIZE + 4.0
    glyph_width = FONT_SIZE * 1.2

    safe_x_min = x0_abs + 2.0
    safe_x_max = x1_abs - glyph_width - 2.0
    safe_y_min = y0_abs + inset
    safe_y_max = y1_abs - 4.0

    if safe_x_min >= safe_x_max or safe_y_min >= safe_y_max:
        return st.just([])

    entry_st = st.tuples(
        st.floats(min_value=safe_x_min, max_value=safe_x_max),
        st.floats(min_value=safe_y_min, max_value=safe_y_max),
        _checkbox_char,
    )
    return st.lists(entry_st, min_size=1, max_size=6)


# ---------------------------------------------------------------------------
# Property 7: Checkbox detection produces region-relative positions
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 7: Checkbox detection produces region-relative positions
@given(data=st.data())
@settings(max_examples=100, deadline=None)
def test_checkbox_region_relative_positions(data: st.DataObject) -> None:
    """detect_checkboxes returns region-relative percentages in [0, 100].

    **Validates: Requirements 6.2, 6.3**

    Strategy:
    - Generate a rectangular region as page percentages.
    - Generate checkbox positions guaranteed to be inside that region.
    - Create a synthetic PDF with those checkboxes.
    - Call detect_checkboxes and verify:
      (a) All returned checkboxes have x, y, x2, y2 in [0, 100].
      (b) x <= x2 and y <= y2 (bounding box is valid).
    """
    region = data.draw(_region_pct, label="region_pct")
    entries = data.draw(
        _checkbox_positions_inside_region(region), label="checkbox_entries"
    )
    assume(len(entries) > 0)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)
        checkboxes = detect_checkboxes(str(pdf_path), region)

    # We placed checkboxes inside the region, so we expect results.
    assert len(checkboxes) > 0, (
        f"Expected checkboxes but got none. "
        f"Region: {region}, entries: {entries}"
    )

    for cb in checkboxes:
        # (a) All coordinates are region-relative percentages in [0, 100]
        for key in ("x", "y", "x2", "y2"):
            value = cb[key]
            assert 0 <= value <= 100, (
                f"Coordinate {key}={value} out of [0, 100] range. "
                f"Checkbox: {cb}, region: {region}"
            )

        # (b) Bounding box is valid: x <= x2 and y <= y2
        assert cb["x"] <= cb["x2"], (
            f"Invalid bbox: x={cb['x']} > x2={cb['x2']}"
        )
        assert cb["y"] <= cb["y2"], (
            f"Invalid bbox: y={cb['y']} > y2={cb['y2']}"
        )


# ---------------------------------------------------------------------------
# Strategies for Property 8
# ---------------------------------------------------------------------------

# Base label word: alphabetic text without trailing punctuation
_label_word = st.from_regex(r"[A-Za-z]{2,10}", fullmatch=True)

# A word ending in comma
_word_trailing_comma = _label_word.map(lambda w: w + ",")

# A word ending in period
_word_trailing_period = _label_word.map(lambda w: w + ".")

# A word ending in ellipsis
_word_trailing_ellipsis = _label_word.map(lambda w: w + "...")

# A decimal number ending in period (digit before period)
_decimal_trailing_period = st.builds(
    lambda word, integer, decimal: f"{word} {integer}.{decimal}.",
    _label_word,
    st.integers(min_value=0, max_value=999),
    st.integers(min_value=0, max_value=99),
).map(lambda s: s.split())


# ---------------------------------------------------------------------------
# Property 8: Trailing punctuation stripping preserves ellipsis and decimals
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 8: Trailing punctuation stripping preserves ellipsis and decimals
@given(
    prefix_words=st.lists(_label_word, min_size=0, max_size=4),
    case=st.sampled_from(["comma", "period", "ellipsis", "decimal"]),
    data=st.data(),
)
@settings(max_examples=200, deadline=None)
def test_trailing_punctuation_stripping(
    prefix_words: list[str],
    case: str,
    data: st.DataObject,
) -> None:
    """_clean_label strips trailing comma/period but preserves ellipsis and decimals.

    **Validates: Requirements 7.5**

    Strategy:
    - Generate a list of prefix words (0-4 plain words).
    - Append a final word with trailing punctuation based on the case:
      comma, period, ellipsis, or decimal-period.
    - Call _clean_label and verify:
      (a) Trailing comma → stripped.
      (b) Trailing period → stripped.
      (c) Trailing ellipsis ("...") → preserved.
      (d) Digit before trailing period (decimal) → preserved.
    """
    if case == "comma":
        last_word = data.draw(_word_trailing_comma, label="last_word")
        words = prefix_words + [last_word]
        result = _clean_label(words)
        # Trailing comma should be stripped
        assert not result.endswith(","), (
            f"Trailing comma not stripped: {result!r} (words: {words})"
        )
        # The word content (minus comma) should be present
        expected_content = last_word[:-1]
        assert result.endswith(expected_content), (
            f"Expected result to end with {expected_content!r}, "
            f"got {result!r}"
        )

    elif case == "period":
        last_word = data.draw(_word_trailing_period, label="last_word")
        words = prefix_words + [last_word]
        result = _clean_label(words)
        # Trailing period should be stripped (not ellipsis, not decimal)
        assert not result.endswith("."), (
            f"Trailing period not stripped: {result!r} (words: {words})"
        )
        expected_content = last_word[:-1]
        assert result.endswith(expected_content), (
            f"Expected result to end with {expected_content!r}, "
            f"got {result!r}"
        )

    elif case == "ellipsis":
        last_word = data.draw(_word_trailing_ellipsis, label="last_word")
        words = prefix_words + [last_word]
        result = _clean_label(words)
        # Ellipsis should be preserved
        assert result.endswith("..."), (
            f"Ellipsis not preserved: {result!r} (words: {words})"
        )

    elif case == "decimal":
        decimal_words = data.draw(_decimal_trailing_period, label="decimal_words")
        words = prefix_words + decimal_words
        result = _clean_label(words)
        # Decimal period should be preserved (digit before period)
        assert result.endswith("."), (
            f"Decimal period not preserved: {result!r} (words: {words})"
        )
