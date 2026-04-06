"""Property-based tests for layout_generator.text_extractor module.

Uses hypothesis to verify universal properties of text extraction
across randomly generated PDF word positions and regions.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import fitz
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from layout_generator.text_extractor import extract_text_lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
FONT_SIZE = 10.0

# Approximate bounding box dimensions for a single word at FONT_SIZE.
# PyMuPDF's insert_text uses the baseline y; the bbox top is ~font_size
# above the baseline, and the bbox extends ~2pt below.
WORD_HEIGHT_APPROX = FONT_SIZE + 2.0
WORD_WIDTH_PER_CHAR = FONT_SIZE * 0.6


def create_pdf_with_words(
    tmp_path: Path,
    words: list[tuple[float, float, str]],
    filename: str = "test.pdf",
) -> Path:
    """Create a single-page PDF with text inserted at specific positions.

    Args:
        tmp_path: Temporary directory for the PDF file.
        words: List of (x, y_baseline, text) tuples in PDF points.
        filename: Output filename.

    Returns:
        Path to the created PDF.
    """
    pdf_path = tmp_path / filename
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    for x, y_baseline, text in words:
        page.insert_text(fitz.Point(x, y_baseline), text, fontsize=FONT_SIZE)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Region margins: leave enough room so words placed inside the region
# have their full bounding boxes contained within it.
_MARGIN = 15.0  # percentage margin from page edges for region bounds

# Region strategy: [x0, y0, x1, y1] as page percentages.
# Ensure the region is large enough to contain at least one word.
_region_pct = st.tuples(
    st.floats(min_value=_MARGIN, max_value=40.0),       # x0
    st.floats(min_value=_MARGIN, max_value=40.0),       # y0
    st.floats(min_value=60.0, max_value=100.0 - _MARGIN),  # x1
    st.floats(min_value=60.0, max_value=100.0 - _MARGIN),  # y1
).map(lambda t: [t[0], t[1], t[2], t[3]])

# Simple word text — short alphabetic strings that won't be filtered
# as "items" headers.
_word_text = st.from_regex(r"[a-z]{3,6}", fullmatch=True)


def _words_inside_region(region_pct: list[float]) -> st.SearchStrategy:
    """Generate a list of (x_baseline, y_baseline, text) tuples inside the region.

    Positions are chosen so the full bounding box fits within the region,
    accounting for font metrics.
    """
    x0_abs = (region_pct[0] / 100.0) * PAGE_WIDTH
    y0_abs = (region_pct[1] / 100.0) * PAGE_HEIGHT
    x1_abs = (region_pct[2] / 100.0) * PAGE_WIDTH
    y1_abs = (region_pct[3] / 100.0) * PAGE_HEIGHT

    # Inset to ensure the word bounding box stays inside the region.
    # The bbox top is ~FONT_SIZE above baseline, so baseline must be
    # at least FONT_SIZE below region top. The bbox bottom extends ~2pt
    # below baseline, so baseline must be at least 2pt above region bottom.
    inset = FONT_SIZE + 4.0
    word_max_width = WORD_WIDTH_PER_CHAR * 6  # max 6-char word

    safe_x_min = x0_abs + 2.0
    safe_x_max = x1_abs - word_max_width - 2.0
    safe_y_min = y0_abs + inset
    safe_y_max = y1_abs - 4.0

    if safe_x_min >= safe_x_max or safe_y_min >= safe_y_max:
        return st.just([])

    word_st = st.tuples(
        st.floats(min_value=safe_x_min, max_value=safe_x_max),
        st.floats(min_value=safe_y_min, max_value=safe_y_max),
        _word_text,
    )
    return st.lists(word_st, min_size=1, max_size=8)


# ---------------------------------------------------------------------------
# Property 3: Text extraction produces region-relative sorted lines
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 3: Text extraction produces region-relative sorted lines
@given(data=st.data())
@settings(max_examples=100, deadline=None)
def test_region_relative_sorted_lines(data: st.DataObject) -> None:
    """extract_text_lines returns region-relative percentages sorted top-to-bottom.

    Validates: Requirements 4.3, 4.5, 4.6

    Strategy:
    - Generate a rectangular region as page percentages.
    - Generate word positions guaranteed to be inside that region.
    - Create a synthetic PDF with those words.
    - Call extract_text_lines and verify:
      (a) For each line: 0 <= top_left_pct[1] <= bottom_right_pct[1] <= 100
      (b) For consecutive lines i, i+1:
          lines[i]['top_left_pct'][1] <= lines[i+1]['top_left_pct'][1]
    """
    region = data.draw(_region_pct, label="region_pct")
    words = data.draw(_words_inside_region(region), label="words")
    assume(len(words) > 0)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pdf_path = create_pdf_with_words(tmp_path, words)
        lines = extract_text_lines(str(pdf_path), region)

    # (a) Bounding box y-coordinates are valid region-relative percentages
    for line in lines:
        top_y = line["top_left_pct"][1]
        bottom_y = line["bottom_right_pct"][1]
        assert 0 <= top_y <= bottom_y <= 100, (
            f"Invalid y percentages: top_y={top_y}, bottom_y={bottom_y}"
        )

        # Also verify x-coordinates are in range
        top_x = line["top_left_pct"][0]
        bottom_x = line["bottom_right_pct"][0]
        assert 0 <= top_x <= 100, f"top_left x out of range: {top_x}"
        assert 0 <= bottom_x <= 100, f"bottom_right x out of range: {bottom_x}"

    # (b) Lines are sorted by vertical position (top to bottom)
    for i in range(len(lines) - 1):
        current_y = lines[i]["top_left_pct"][1]
        next_y = lines[i + 1]["top_left_pct"][1]
        assert current_y <= next_y, (
            f"Lines not sorted: line {i} y={current_y} > line {i+1} y={next_y}"
        )


# ---------------------------------------------------------------------------
# Property 4: Y-coordinate line grouping within tolerance
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 4: Y-coordinate line grouping within tolerance
@given(data=st.data())
@settings(max_examples=100, deadline=None)
def test_y_coordinate_grouping(data: st.DataObject) -> None:
    """Words within Y_COORDINATE_GROUPING_TOLERANCE are on the same line; beyond are on different lines.

    Validates: Requirements 4.4

    Strategy:
    - Use the full page as the region to avoid filtering issues.
    - Generate two words at known y-coordinates:
      Case 1: y-coordinates within tolerance → same line (1 result line)
      Case 2: y-coordinates beyond tolerance → different lines (2 result lines)
    - Create a synthetic PDF and verify grouping via extract_text_lines.
    """
    from layout_generator.text_extractor import Y_COORDINATE_GROUPING_TOLERANCE

    full_page_region = [0.0, 0.0, 100.0, 100.0]

    # Fixed x-positions: word_a on the left, word_b on the right so they
    # don't overlap horizontally and both stay well within the page.
    x_a = 50.0
    x_b = 200.0

    # Base y-baseline for the first word — keep it in a safe vertical band
    # so bounding boxes stay on the page.
    base_y = data.draw(
        st.floats(min_value=80.0, max_value=700.0),
        label="base_y_baseline",
    )

    # Draw a boolean to decide which case we're testing.
    within_tolerance = data.draw(st.booleans(), label="within_tolerance")

    if within_tolerance:
        # Delta in [0, tolerance] — words should land on the same line.
        delta = data.draw(
            st.floats(min_value=0.0, max_value=Y_COORDINATE_GROUPING_TOLERANCE),
            label="delta_within",
        )
    else:
        # Delta in (tolerance + small_gap, tolerance + 30] — different lines.
        # Use a gap of 1.0 to avoid floating-point edge effects right at the boundary.
        delta = data.draw(
            st.floats(
                min_value=Y_COORDINATE_GROUPING_TOLERANCE + 1.0,
                max_value=Y_COORDINATE_GROUPING_TOLERANCE + 30.0,
            ),
            label="delta_beyond",
        )

    second_y = base_y + delta

    # Ensure the second word's bounding box stays on the page.
    assume(second_y + WORD_HEIGHT_APPROX < PAGE_HEIGHT)

    words = [
        (x_a, base_y, "alpha"),
        (x_b, second_y, "bravo"),
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pdf_path = create_pdf_with_words(tmp_path, words)
        lines = extract_text_lines(str(pdf_path), full_page_region)

    # Both words should always be extracted.
    all_text = " ".join(line["text"] for line in lines)
    assert "alpha" in all_text, f"'alpha' missing from extracted text: {all_text}"
    assert "bravo" in all_text, f"'bravo' missing from extracted text: {all_text}"

    if within_tolerance:
        # Words within tolerance → grouped into a single line.
        lines_with_both = [
            line for line in lines
            if "alpha" in line["text"] and "bravo" in line["text"]
        ]
        assert len(lines_with_both) == 1, (
            f"Expected 1 line with both words (delta={delta}), "
            f"got {len(lines_with_both)}. Lines: {lines}"
        )
    else:
        # Words beyond tolerance → on separate lines.
        alpha_lines = [line for line in lines if "alpha" in line["text"]]
        bravo_lines = [line for line in lines if "bravo" in line["text"]]
        assert len(alpha_lines) >= 1 and len(bravo_lines) >= 1, (
            f"Expected both words on separate lines (delta={delta}). "
            f"Lines: {lines}"
        )
        # They should NOT share a line.
        lines_with_both = [
            line for line in lines
            if "alpha" in line["text"] and "bravo" in line["text"]
        ]
        assert len(lines_with_both) == 0, (
            f"Words should be on different lines (delta={delta}), "
            f"but found shared line. Lines: {lines}"
        )
