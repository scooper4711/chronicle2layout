"""Unit tests for checkbox_extractor.image_checkboxes and extract_checkbox_labels.

Tests checkbox detection in PDFs (empty PDF, no checkbox chars, checkbox present)
and label extraction (empty checkboxes list, empty PDF, checkbox with label text).

Requirements: refactor-chronicle2layout 2.3
"""

import sys
from pathlib import Path

import fitz  # PyMuPDF
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from checkbox_extractor import CHECKBOX_CHARS, extract_checkbox_labels, image_checkboxes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LETTER_WIDTH = 612
LETTER_HEIGHT = 792

# Courier font supports □ and other checkbox Unicode characters,
# unlike the default Helvetica which substitutes them with ·.
CHECKBOX_FONT = fitz.Font("cour")


def create_test_pdf(
    tmp_path: Path,
    text_items: list[tuple[str, float, float]],
    filename: str = "test.pdf",
) -> str:
    """Create a single-page PDF with text placed via TextWriter.

    Uses the Courier font which correctly encodes checkbox Unicode characters.

    Args:
        tmp_path: pytest tmp_path fixture directory.
        text_items: List of (text, x, y) tuples for text placement.
        filename: Output filename.

    Returns:
        Absolute path to the created PDF.
    """
    pdf_path = str(tmp_path / filename)
    doc = fitz.open()
    page = doc.new_page(width=LETTER_WIDTH, height=LETTER_HEIGHT)
    tw = fitz.TextWriter(page.rect)
    for text, x, y in text_items:
        tw.append((x, y), text, font=CHECKBOX_FONT, fontsize=12)
    tw.write_text(page)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


# Minimal valid PDF with zero pages (PyMuPDF refuses to save empty docs,
# so we write the raw PDF structure directly).
_ZERO_PAGE_PDF = (
    b"%PDF-1.0\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
    b"xref\n0 3\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"trailer<</Size 3/Root 1 0 R>>\n"
    b"startxref\n109\n%%EOF"
)


def create_empty_pdf(tmp_path: Path, filename: str = "empty.pdf") -> str:
    """Create a valid PDF with zero pages.

    Returns:
        Absolute path to the created PDF.
    """
    pdf_path = str(tmp_path / filename)
    with open(pdf_path, "wb") as f:
        f.write(_ZERO_PAGE_PDF)
    return pdf_path


# ---------------------------------------------------------------------------
# image_checkboxes tests
# ---------------------------------------------------------------------------

class TestImageCheckboxes:
    """Unit tests for image_checkboxes."""

    def test_empty_pdf_returns_empty_list(self, tmp_path: Path) -> None:
        """A PDF with zero pages returns an empty list."""
        pdf_path = create_empty_pdf(tmp_path)
        result = image_checkboxes(pdf_path)
        assert result == []

    def test_no_checkbox_chars_returns_empty_list(self, tmp_path: Path) -> None:
        """A PDF containing only regular text (no checkbox chars) returns empty."""
        pdf_path = create_test_pdf(tmp_path, [
            ("Hello world", 100, 400),
            ("Some regular text", 200, 500),
        ])
        result = image_checkboxes(pdf_path)
        assert result == []

    def test_detects_checkbox_character(self, tmp_path: Path) -> None:
        """A PDF containing □ returns a checkbox with valid position percentages."""
        pdf_path = create_test_pdf(tmp_path, [("□", 100, 400)])
        result = image_checkboxes(pdf_path)

        assert len(result) == 1
        checkbox = result[0]
        assert "x" in checkbox and "y" in checkbox
        assert "x2" in checkbox and "y2" in checkbox
        # Coordinates are percentages in 0-100 range
        for key in ("x", "y", "x2", "y2"):
            assert 0 <= checkbox[key] <= 100
        # Bounding box is valid (x2 > x, y2 > y)
        assert checkbox["x2"] > checkbox["x"]
        assert checkbox["y2"] > checkbox["y"]

    def test_detects_multiple_checkbox_characters(self, tmp_path: Path) -> None:
        """Multiple checkbox characters on a page are all detected."""
        pdf_path = create_test_pdf(tmp_path, [
            ("□", 50, 200),
            ("□", 50, 400),
            ("□", 50, 600),
        ])
        result = image_checkboxes(pdf_path)
        assert len(result) == 3

    def test_region_filter_excludes_outside_checkboxes(self, tmp_path: Path) -> None:
        """Checkboxes outside the specified region_pct are excluded."""
        pdf_path = create_test_pdf(tmp_path, [
            ("□", 50, 50),     # top-left area
            ("□", 500, 700),   # bottom-right area
        ])
        # Region covers only the bottom-right half of the page
        region = [50.0, 50.0, 100.0, 100.0]
        result = image_checkboxes(pdf_path, region_pct=region)
        assert len(result) == 1

    def test_checkbox_chars_constant_contains_expected_chars(self) -> None:
        """CHECKBOX_CHARS contains the four expected Unicode checkbox characters."""
        assert set(CHECKBOX_CHARS) == {'□', '☐', '☑', '☒'}


# ---------------------------------------------------------------------------
# extract_checkbox_labels tests
# ---------------------------------------------------------------------------

class TestExtractCheckboxLabels:
    """Unit tests for extract_checkbox_labels."""

    def test_empty_checkboxes_returns_empty_list(self, tmp_path: Path) -> None:
        """An empty checkboxes list returns an empty result."""
        pdf_path = create_test_pdf(tmp_path, [("□ Option A", 100, 400)])
        region = [0.0, 0.0, 100.0, 100.0]
        result = extract_checkbox_labels(pdf_path, [], region)
        assert result == []

    def test_empty_pdf_returns_empty_list(self, tmp_path: Path) -> None:
        """A PDF with zero pages returns an empty result."""
        pdf_path = create_empty_pdf(tmp_path)
        region = [0.0, 0.0, 100.0, 100.0]
        checkboxes = [{"x": 10, "y": 10, "x2": 15, "y2": 15}]
        result = extract_checkbox_labels(pdf_path, checkboxes, region)
        assert result == []

    def test_extracts_label_after_checkbox(self, tmp_path: Path) -> None:
        """A checkbox followed by label text extracts the correct label."""
        pdf_path = create_test_pdf(tmp_path, [
            ("□", 50, 400),
            ("Alliance", 70, 400),
        ])
        region = [0.0, 0.0, 100.0, 100.0]

        checkboxes = image_checkboxes(pdf_path, region_pct=region)
        assert len(checkboxes) >= 1

        result = extract_checkbox_labels(pdf_path, checkboxes, region)
        assert len(result) >= 1
        assert "Alliance" in result[0]["label"]
        assert result[0]["checkbox"] is not None

    def test_multiple_checkboxes_get_separate_labels(self, tmp_path: Path) -> None:
        """Each checkbox gets its own label from the following text."""
        pdf_path = create_test_pdf(tmp_path, [
            ("□", 50, 300),
            ("First", 70, 300),
            ("□", 50, 500),
            ("Second", 70, 500),
        ])
        region = [0.0, 0.0, 100.0, 100.0]

        checkboxes = image_checkboxes(pdf_path, region_pct=region)
        assert len(checkboxes) == 2

        result = extract_checkbox_labels(pdf_path, checkboxes, region)
        assert len(result) == 2
        labels = [r["label"] for r in result]
        assert any("First" in label for label in labels)
        assert any("Second" in label for label in labels)
