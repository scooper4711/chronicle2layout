"""Unit tests for layout_generator.checkbox_extractor module.

Tests detect_checkboxes with real chronicle PDFs, synthetic PDFs
with known checkbox positions, empty PDFs, region filtering,
and extract_checkbox_labels with label collection, delimiter handling,
trailing punctuation stripping, and ellipsis preservation.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from layout_generator.checkbox_extractor import (
    CHECKBOX_CHARS,
    _clean_label,
    detect_checkboxes,
    extract_checkbox_labels,
)

REAL_PDF = Path("modules/pfs-chronicle-generator/assets/chronicles/pfs2/season1/1-00-OriginoftheOpenRoadChronicle.pdf")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_pdf_with_checkboxes(
    tmp_path: Path,
    entries: list[tuple[float, float, str]],
    page_width: float = 612.0,
    page_height: float = 792.0,
    font_size: float = 12.0,
    filename: str = "checkboxes.pdf",
) -> Path:
    """Create a single-page PDF with checkbox characters and labels.

    Uses TextWriter with the built-in Helvetica font, which supports
    checkbox Unicode glyphs in PyMuPDF.

    Args:
        tmp_path: Temporary directory for the PDF file.
        entries: List of (x, y, text) tuples in PDF points.
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

    checkbox_font = fitz.Font("helv")
    text_font = fitz.Font("helv")
    tw = fitz.TextWriter(page.rect)

    checkbox_set = set(CHECKBOX_CHARS)

    for x, y, text in entries:
        has_checkbox = any(ch in text for ch in checkbox_set)
        font = checkbox_font if has_checkbox else text_font
        tw.append(fitz.Point(x, y), text, font=font, fontsize=font_size)

    tw.write_text(page)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def create_empty_pdf(tmp_path: Path) -> Path:
    """Create a PDF with zero pages using raw PDF bytes."""
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
# detect_checkboxes — Real chronicle PDF
# ---------------------------------------------------------------------------


class TestDetectCheckboxesRealPdf:
    """Tests using a real chronicle PDF from the Scenarios directory."""

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_detects_checkboxes_in_real_pdf(self) -> None:
        """detect_checkboxes returns non-empty results for a known region."""
        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(REAL_PDF), region)

        assert isinstance(checkboxes, list)
        assert len(checkboxes) > 0

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_real_pdf_checkboxes_have_expected_keys(self) -> None:
        """Each checkbox dict has x, y, x2, y2 keys."""
        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(REAL_PDF), region)

        for cb in checkboxes:
            assert "x" in cb
            assert "y" in cb
            assert "x2" in cb
            assert "y2" in cb

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_real_pdf_percentages_in_range(self) -> None:
        """Checkbox bounding box percentages are within 0-100 range."""
        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(REAL_PDF), region)

        for cb in checkboxes:
            assert 0 <= cb["x"] <= 100
            assert 0 <= cb["y"] <= 100
            assert 0 <= cb["x2"] <= 100
            assert 0 <= cb["y2"] <= 100


# ---------------------------------------------------------------------------
# detect_checkboxes — Empty PDF
# ---------------------------------------------------------------------------


class TestDetectCheckboxesEmptyPdf:
    """Tests for PDFs with zero pages."""

    def test_zero_page_pdf_returns_empty_list(self, tmp_path: Path) -> None:
        """A PDF with no pages returns an empty list."""
        pdf_path = create_empty_pdf(tmp_path)
        result = detect_checkboxes(str(pdf_path))
        assert result == []


# ---------------------------------------------------------------------------
# detect_checkboxes — Region filtering
# ---------------------------------------------------------------------------


class TestDetectCheckboxesRegionFiltering:
    """Tests that checkboxes outside the region are excluded."""

    def test_checkbox_inside_region_detected(self, tmp_path: Path) -> None:
        """A checkbox within the region is returned."""
        entries = [(200.0, 400.0, "☐")]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [25.0, 25.0, 75.0, 75.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)

        assert len(checkboxes) == 1

    def test_checkbox_outside_region_excluded(self, tmp_path: Path) -> None:
        """A checkbox outside the region is not returned."""
        # Place at far left (x=10), which is ~1.6% of 612 — outside 25%-75%
        entries = [(10.0, 50.0, "☐")]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [25.0, 25.0, 75.0, 75.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)

        assert len(checkboxes) == 0

    def test_mixed_inside_outside_region(self, tmp_path: Path) -> None:
        """Only checkboxes inside the region are returned."""
        entries = [
            (200.0, 400.0, "☐"),   # Inside 25%-75% region
            (10.0, 50.0, "☐"),     # Outside (far left, near top)
            (300.0, 500.0, "☐"),   # Inside
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [25.0, 25.0, 75.0, 75.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)

        assert len(checkboxes) == 2

    def test_no_region_uses_full_page(self, tmp_path: Path) -> None:
        """When region_pct is None, all checkboxes on the page are returned."""
        entries = [
            (10.0, 50.0, "☐"),
            (300.0, 400.0, "☐"),
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        checkboxes = detect_checkboxes(str(pdf_path), region_pct=None)

        assert len(checkboxes) == 2


# ---------------------------------------------------------------------------
# detect_checkboxes — Multiple checkbox characters
# ---------------------------------------------------------------------------


class TestDetectCheckboxesCharacterVariants:
    """Tests that all recognized checkbox Unicode characters are detected."""

    def test_all_checkbox_chars_detected(self, tmp_path: Path) -> None:
        """All four checkbox Unicode variants are detected."""
        y_pos = 200.0
        entries = [
            (200.0, y_pos, "□"),             # U+25A1
            (200.0, y_pos + 40, "☐"),        # U+2610
            (200.0, y_pos + 80, "☑"),        # U+2611
            (200.0, y_pos + 120, "☒"),       # U+2612
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        checkboxes = detect_checkboxes(str(pdf_path))

        assert len(checkboxes) == 4


# ---------------------------------------------------------------------------
# detect_checkboxes — Region-relative percentages
# ---------------------------------------------------------------------------


class TestDetectCheckboxesPercentages:
    """Tests that returned coordinates are region-relative percentages."""

    def test_coordinates_are_region_relative(self, tmp_path: Path) -> None:
        """Checkbox coordinates are percentages of the region, not the page."""
        # Page: 612x792. Region: 50%-100% x, 50%-100% y
        # Region absolute: x0=306, y0=396, x1=612, y1=792
        # Place checkbox at (400, 500) — inside the region
        entries = [(400.0, 500.0, "☐")]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [50.0, 50.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)

        assert len(checkboxes) == 1
        cb = checkboxes[0]
        # x should be relative to region, not page
        assert 0 < cb["x"] < 100
        assert 0 < cb["y"] < 100


# ---------------------------------------------------------------------------
# extract_checkbox_labels — Synthetic PDFs
# ---------------------------------------------------------------------------


class TestExtractCheckboxLabels:
    """Tests for extract_checkbox_labels with synthetic PDFs."""

    def test_basic_label_collection(self, tmp_path: Path) -> None:
        """Labels are collected from words following the checkbox."""
        entries = [
            (200.0, 400.0, "☐"),
            (220.0, 400.0, "Primary"),
            (270.0, 400.0, "Mission"),
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)
        labels = extract_checkbox_labels(str(pdf_path), checkboxes, region)

        assert len(labels) == 1
        assert "Primary" in labels[0]["label"]
        assert "Mission" in labels[0]["label"]

    def test_delimiter_next_checkbox_stops_label(self, tmp_path: Path) -> None:
        """Label collection stops at the next checkbox character."""
        entries = [
            (200.0, 400.0, "☐"),
            (220.0, 400.0, "First"),
            (200.0, 430.0, "☐"),
            (220.0, 430.0, "Second"),
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)
        labels = extract_checkbox_labels(str(pdf_path), checkboxes, region)

        assert len(labels) == 2
        assert labels[0]["label"] == "First"
        assert labels[1]["label"] == "Second"

    def test_delimiter_or_stops_label(self, tmp_path: Path) -> None:
        """Label collection stops at the word 'or'."""
        entries = [
            (200.0, 400.0, "☐"),
            (220.0, 400.0, "Success"),
            (280.0, 400.0, "or"),
            (300.0, 400.0, "Failure"),
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)
        labels = extract_checkbox_labels(str(pdf_path), checkboxes, region)

        assert len(labels) == 1
        assert labels[0]["label"] == "Success"
        assert "or" not in labels[0]["label"]
        assert "Failure" not in labels[0]["label"]

    def test_delimiter_trailing_comma_stops_label(self, tmp_path: Path) -> None:
        """Label collection stops at a word ending with a comma."""
        entries = [
            (200.0, 400.0, "☐"),
            (220.0, 400.0, "Option,"),
            (280.0, 400.0, "extra"),
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)
        labels = extract_checkbox_labels(str(pdf_path), checkboxes, region)

        assert len(labels) == 1
        assert labels[0]["label"] == "Option"

    def test_delimiter_trailing_period_stops_label(self, tmp_path: Path) -> None:
        """Label collection stops at a word ending with a period."""
        entries = [
            (200.0, 400.0, "☐"),
            (220.0, 400.0, "Done."),
            (270.0, 400.0, "extra"),
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)
        labels = extract_checkbox_labels(str(pdf_path), checkboxes, region)

        assert len(labels) == 1
        assert labels[0]["label"] == "Done"

    def test_empty_checkboxes_returns_empty(self, tmp_path: Path) -> None:
        """Passing an empty checkboxes list returns an empty list."""
        entries = [(200.0, 400.0, "☐")]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [0.0, 0.0, 100.0, 100.0]
        labels = extract_checkbox_labels(str(pdf_path), [], region)

        assert labels == []

    def test_label_has_checkbox_key(self, tmp_path: Path) -> None:
        """Each result dict has 'checkbox' and 'label' keys."""
        entries = [
            (200.0, 400.0, "☐"),
            (220.0, 400.0, "Test"),
        ]
        pdf_path = create_pdf_with_checkboxes(tmp_path, entries)

        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(pdf_path), region)
        labels = extract_checkbox_labels(str(pdf_path), checkboxes, region)

        assert len(labels) == 1
        assert "checkbox" in labels[0]
        assert "label" in labels[0]
        assert labels[0]["checkbox"] is not None


# ---------------------------------------------------------------------------
# _clean_label — Trailing punctuation stripping
# ---------------------------------------------------------------------------


class TestCleanLabel:
    """Tests for _clean_label trailing punctuation stripping."""

    def test_strips_trailing_comma(self) -> None:
        """Trailing comma is removed."""
        assert _clean_label(["hello,"]) == "hello"

    def test_strips_trailing_period(self) -> None:
        """Trailing period is removed."""
        assert _clean_label(["world."]) == "world"

    def test_preserves_ellipsis(self) -> None:
        """Trailing ellipsis ('...') is preserved."""
        assert _clean_label(["continue..."]) == "continue..."

    def test_preserves_decimal_number(self) -> None:
        """Trailing period after a digit (decimal) is preserved."""
        assert _clean_label(["price", "3.5."]) == "price 3.5."

    def test_preserves_decimal_ending_in_period(self) -> None:
        """A label like '12.5' ending in period-after-digit is preserved."""
        assert _clean_label(["12.5."]) == "12.5."

    def test_no_trailing_punctuation_unchanged(self) -> None:
        """Label without trailing punctuation is returned as-is."""
        assert _clean_label(["hello", "world"]) == "hello world"

    def test_empty_words_returns_empty(self) -> None:
        """Empty word list returns empty string."""
        assert _clean_label([]) == ""

    def test_single_period_stripped(self) -> None:
        """A single period is stripped to empty."""
        assert _clean_label(["."]) == ""

    def test_multi_word_trailing_comma(self) -> None:
        """Trailing comma on multi-word label is stripped."""
        assert _clean_label(["Primary", "Mission,"]) == "Primary Mission"

    def test_multi_word_trailing_period(self) -> None:
        """Trailing period on multi-word label is stripped."""
        assert _clean_label(["Secondary", "Objective."]) == "Secondary Objective"

    def test_whitespace_stripped(self) -> None:
        """Leading and trailing whitespace is stripped."""
        assert _clean_label(["  hello  "]) == "hello"


# ---------------------------------------------------------------------------
# extract_checkbox_labels — Real chronicle PDF
# ---------------------------------------------------------------------------


class TestExtractCheckboxLabelsRealPdf:
    """Tests using a real chronicle PDF."""

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_extracts_labels_from_real_pdf(self) -> None:
        """extract_checkbox_labels returns results for a real PDF."""
        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = detect_checkboxes(str(REAL_PDF), region)

        if not checkboxes:
            pytest.skip("No checkboxes found in real PDF")

        labels = extract_checkbox_labels(str(REAL_PDF), checkboxes, region)

        assert isinstance(labels, list)
        assert len(labels) > 0
        for item in labels:
            assert "checkbox" in item
            assert "label" in item
            assert isinstance(item["label"], str)
