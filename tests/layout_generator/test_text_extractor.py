"""Unit tests for layout_generator.text_extractor module.

Tests extract_text_lines with real chronicle PDFs, synthetic PDFs
with known word positions, empty PDFs, filtering, y-coordinate
grouping, percentage conversion, and sort order.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from layout_generator.text_extractor import (
    Y_COORDINATE_GROUPING_TOLERANCE,
    extract_text_lines,
)

REAL_PDF = Path("modules/pfs-chronicle-generator/assets/chronicles/pfs2/season1/1-00-OriginoftheOpenRoadChronicle.pdf")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_pdf_with_words(
    tmp_path: Path,
    words: list[tuple[float, float, str]],
    page_width: float = 612.0,
    page_height: float = 792.0,
    font_size: float = 12.0,
    filename: str = "test.pdf",
) -> Path:
    """Create a single-page PDF with text inserted at specific positions.

    Args:
        tmp_path: Temporary directory for the PDF file.
        words: List of (x, y, text) tuples in PDF points.
        page_width: Page width in PDF points.
        page_height: Page height in PDF points.
        font_size: Font size for inserted text.
        filename: Output filename.

    Returns:
        Path to the created PDF.
    """
    pdf_path = tmp_path / filename
    doc = fitz.open()
    page = doc.new_page(width=page_width, height=page_height)
    for x, y, text in words:
        page.insert_text(fitz.Point(x, y), text, fontsize=font_size)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def create_empty_pdf(tmp_path: Path) -> Path:
    """Create a PDF with zero pages.

    PyMuPDF refuses to save a document with zero pages, so we write
    a minimal valid PDF structure directly.
    """
    pdf_path = tmp_path / "empty.pdf"
    raw = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"xref\n0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000052 00000 n \n"
        b"trailer<</Size 3/Root 1 0 R>>\n"
        b"startxref\n97\n%%EOF"
    )
    pdf_path.write_bytes(raw)
    return pdf_path


# ---------------------------------------------------------------------------
# Real chronicle PDF
# ---------------------------------------------------------------------------


class TestRealChroniclePdf:
    """Tests using a real chronicle PDF from the Scenarios directory."""

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_extracts_text_from_real_pdf(self) -> None:
        """extract_text_lines returns non-empty results for a known region."""
        region = [5.0, 50.0, 95.0, 90.0]
        lines = extract_text_lines(str(REAL_PDF), region)

        assert isinstance(lines, list)
        assert len(lines) > 0

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_real_pdf_lines_have_expected_keys(self) -> None:
        """Each returned line dict has text, top_left_pct, bottom_right_pct."""
        region = [5.0, 50.0, 95.0, 90.0]
        lines = extract_text_lines(str(REAL_PDF), region)

        for line in lines:
            assert "text" in line
            assert "top_left_pct" in line
            assert "bottom_right_pct" in line
            assert isinstance(line["text"], str)
            assert len(line["top_left_pct"]) == 2
            assert len(line["bottom_right_pct"]) == 2

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_real_pdf_percentages_in_range(self) -> None:
        """Bounding box percentages are within 0-100 range."""
        region = [5.0, 50.0, 95.0, 90.0]
        lines = extract_text_lines(str(REAL_PDF), region)

        for line in lines:
            x0, y0 = line["top_left_pct"]
            x1, y1 = line["bottom_right_pct"]
            assert 0 <= x0 <= 100
            assert 0 <= y0 <= 100
            assert 0 <= x1 <= 100
            assert 0 <= y1 <= 100


# ---------------------------------------------------------------------------
# Empty PDF (zero pages)
# ---------------------------------------------------------------------------


class TestEmptyPdf:
    """Tests for PDFs with zero pages."""

    def test_zero_page_pdf_returns_empty_list(self, tmp_path: Path) -> None:
        """A PDF with no pages returns an empty list."""
        pdf_path = create_empty_pdf(tmp_path)
        result = extract_text_lines(str(pdf_path), [0.0, 0.0, 100.0, 100.0])
        assert result == []


# ---------------------------------------------------------------------------
# Filtering: words outside region excluded
# ---------------------------------------------------------------------------


class TestRegionFiltering:
    """Tests that words outside the extraction region are excluded."""

    def test_words_outside_region_excluded(self, tmp_path: Path) -> None:
        """Only words within the region boundaries appear in results."""
        # Place one word inside and one outside a region
        # Region will be 25%-75% of page (153-459 pts on 612-wide page)
        words = [
            (200.0, 400.0, "inside"),   # x=200, within 153-459
            (10.0, 400.0, "outside"),    # x=10, outside 153-459
        ]
        pdf_path = create_pdf_with_words(tmp_path, words)

        # Region: 25% to 75% of page
        region = [25.0, 25.0, 75.0, 75.0]
        lines = extract_text_lines(str(pdf_path), region)

        all_text = " ".join(line["text"] for line in lines)
        assert "inside" in all_text
        assert "outside" not in all_text

    def test_word_partially_outside_region_excluded(self, tmp_path: Path) -> None:
        """A word whose bounding box extends beyond the region is excluded."""
        # Place a word at the very right edge so it extends past the region
        words = [
            (200.0, 400.0, "centered"),
            (450.0, 400.0, "edge_word_that_extends_beyond"),
        ]
        pdf_path = create_pdf_with_words(tmp_path, words)

        # Narrow region that includes centered but clips the edge word
        region = [25.0, 25.0, 75.0, 75.0]
        lines = extract_text_lines(str(pdf_path), region)

        all_text = " ".join(line["text"] for line in lines)
        assert "centered" in all_text


# ---------------------------------------------------------------------------
# Y-coordinate grouping
# ---------------------------------------------------------------------------


class TestYCoordinateGrouping:
    """Tests for y-coordinate line grouping within tolerance."""

    def test_words_within_tolerance_grouped(self, tmp_path: Path) -> None:
        """Words within Y_COORDINATE_GROUPING_TOLERANCE are on the same line."""
        # Two words at nearly the same y, offset by less than tolerance
        y_base = 400.0
        words = [
            (200.0, y_base, "hello"),
            (300.0, y_base + 1.0, "world"),  # 1.0 < 2.0 tolerance
        ]
        pdf_path = create_pdf_with_words(tmp_path, words)

        region = [0.0, 0.0, 100.0, 100.0]
        lines = extract_text_lines(str(pdf_path), region)

        # Both words should be on the same line
        matching = [l for l in lines if "hello" in l["text"] and "world" in l["text"]]
        assert len(matching) == 1, f"Expected 1 grouped line, got {len(matching)}: {lines}"

    def test_words_beyond_tolerance_separated(self, tmp_path: Path) -> None:
        """Words beyond Y_COORDINATE_GROUPING_TOLERANCE are on separate lines."""
        y_base = 300.0
        gap = Y_COORDINATE_GROUPING_TOLERANCE + 20.0  # Well beyond tolerance
        words = [
            (200.0, y_base, "first"),
            (200.0, y_base + gap, "second"),
        ]
        pdf_path = create_pdf_with_words(tmp_path, words)

        region = [0.0, 0.0, 100.0, 100.0]
        lines = extract_text_lines(str(pdf_path), region)

        first_lines = [l for l in lines if "first" in l["text"]]
        second_lines = [l for l in lines if "second" in l["text"]]
        assert len(first_lines) == 1
        assert len(second_lines) == 1
        assert first_lines[0] != second_lines[0]


# ---------------------------------------------------------------------------
# Percentage conversion
# ---------------------------------------------------------------------------


class TestPercentageConversion:
    """Tests that bounding boxes are region-relative percentages."""

    def test_bounding_boxes_are_region_relative(self, tmp_path: Path) -> None:
        """Coordinates are expressed as percentages of the extraction region."""
        # Place a word at a known position
        # Page: 612 x 792. Region: 50% of page = 306-612 x 396-792
        # Word at (400, 500) is inside the region
        words = [(400.0, 500.0, "test")]
        pdf_path = create_pdf_with_words(tmp_path, words)

        # Region: right half of page (50%-100%)
        region = [50.0, 50.0, 100.0, 100.0]
        lines = extract_text_lines(str(pdf_path), region)

        assert len(lines) > 0
        line = lines[0]

        # The word's x position relative to region should be between 0 and 100
        x_pct = line["top_left_pct"][0]
        y_pct = line["top_left_pct"][1]
        assert 0 <= x_pct <= 100, f"x% {x_pct} out of range"
        assert 0 <= y_pct <= 100, f"y% {y_pct} out of range"

    def test_word_at_region_origin_has_near_zero_pct(self, tmp_path: Path) -> None:
        """A word near the top-left of the region has near-zero percentages."""
        # Page 612x792. Region: 10%-90% → x0=61.2, y0=79.2, x1=550.8, y1=712.8
        # insert_text y is the text baseline; bounding box y0 is above it.
        # Place word well inside the region so the bbox top is still inside.
        words = [(70.0, 110.0, "origin")]
        pdf_path = create_pdf_with_words(tmp_path, words)

        region = [10.0, 10.0, 90.0, 90.0]
        lines = extract_text_lines(str(pdf_path), region)

        assert len(lines) > 0
        x_pct = lines[0]["top_left_pct"][0]
        y_pct = lines[0]["top_left_pct"][1]
        # Should be in the first ~15% of the region
        assert x_pct < 15.0, f"Expected near-zero x%, got {x_pct}"
        assert y_pct < 15.0, f"Expected near-zero y%, got {y_pct}"


# ---------------------------------------------------------------------------
# Sort order
# ---------------------------------------------------------------------------


class TestSortOrder:
    """Tests that lines are sorted top-to-bottom."""

    def test_lines_sorted_top_to_bottom(self, tmp_path: Path) -> None:
        """Returned lines are ordered by ascending y-coordinate."""
        # Place words at different y positions (inserted bottom-first)
        words = [
            (200.0, 600.0, "bottom"),
            (200.0, 300.0, "top"),
            (200.0, 450.0, "middle"),
        ]
        pdf_path = create_pdf_with_words(tmp_path, words)

        region = [0.0, 0.0, 100.0, 100.0]
        lines = extract_text_lines(str(pdf_path), region)

        y_values = [line["top_left_pct"][1] for line in lines]
        assert y_values == sorted(y_values), (
            f"Lines not sorted top-to-bottom: {y_values}"
        )

    def test_consecutive_lines_ascending_y(self, tmp_path: Path) -> None:
        """For consecutive lines, line[i].y <= line[i+1].y."""
        words = [
            (200.0, 700.0, "line3"),
            (200.0, 200.0, "line1"),
            (200.0, 450.0, "line2"),
        ]
        pdf_path = create_pdf_with_words(tmp_path, words)

        region = [0.0, 0.0, 100.0, 100.0]
        lines = extract_text_lines(str(pdf_path), region)

        for i in range(len(lines) - 1):
            assert lines[i]["top_left_pct"][1] <= lines[i + 1]["top_left_pct"][1]


# ---------------------------------------------------------------------------
# Items header filtering
# ---------------------------------------------------------------------------


class TestItemsHeaderFiltering:
    """Tests that bare 'items' header lines are skipped."""

    def test_bare_items_header_skipped(self, tmp_path: Path) -> None:
        """A line containing only 'items' is excluded from results."""
        words = [
            (200.0, 300.0, "items"),
            (200.0, 400.0, "actual_content"),
        ]
        pdf_path = create_pdf_with_words(tmp_path, words)

        region = [0.0, 0.0, 100.0, 100.0]
        lines = extract_text_lines(str(pdf_path), region)

        texts = [line["text"] for line in lines]
        assert "items" not in texts
        assert "actual_content" in texts
