"""Unit tests for shared_utils image/PDF functions.

Tests render_page_to_image, words_positions, _measure_box_height,
_is_duplicate_box, and find_grey_boxes using real numpy arrays and PIL images.

Requirements: refactor-chronicle2layout 7.3, 8.1
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from shared_utils import (
    _is_duplicate_box,
    _measure_box_height,
    find_grey_boxes,
    render_page_to_image,
    words_positions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LETTER_WIDTH = 612
LETTER_HEIGHT = 792
CHECKBOX_FONT = fitz.Font("cour")


def create_test_pdf(
    tmp_path: Path,
    text_items: list[tuple[str, float, float]],
    filename: str = "test.pdf",
) -> str:
    """Create a single-page PDF with text placed via TextWriter."""
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


# ---------------------------------------------------------------------------
# render_page_to_image tests
# ---------------------------------------------------------------------------

class TestRenderPageToImage:
    """Unit tests for render_page_to_image."""

    def test_returns_page_and_image(self, tmp_path: Path) -> None:
        """Returns a tuple of (fitz.Page, PIL.Image)."""
        pdf_path = create_test_pdf(tmp_path, [("Hello", 100, 400)])
        page, img = render_page_to_image(pdf_path)
        assert isinstance(page, fitz.Page)
        assert isinstance(img, Image.Image)

    def test_image_dimensions_scale_with_zoom(self, tmp_path: Path) -> None:
        """Image dimensions scale with the zoom factor."""
        pdf_path = create_test_pdf(tmp_path, [("Hello", 100, 400)])
        _, img1 = render_page_to_image(pdf_path, zoom=1)
        _, img2 = render_page_to_image(pdf_path, zoom=2)
        assert img2.width == pytest.approx(img1.width * 2, abs=2)
        assert img2.height == pytest.approx(img1.height * 2, abs=2)

    def test_renders_last_page(self, tmp_path: Path) -> None:
        """Renders the last page of a multi-page PDF."""
        pdf_path = str(tmp_path / "multi.pdf")
        doc = fitz.open()
        doc.new_page(width=LETTER_WIDTH, height=LETTER_HEIGHT)
        page2 = doc.new_page(width=200, height=300)
        tw = fitz.TextWriter(page2.rect)
        tw.append((10, 50), "Page2", font=CHECKBOX_FONT, fontsize=12)
        tw.write_text(page2)
        doc.save(pdf_path)
        doc.close()

        page, img = render_page_to_image(pdf_path, zoom=1)
        # Last page is 200x300, so image should be roughly that size
        assert img.width == pytest.approx(200, abs=5)
        assert img.height == pytest.approx(300, abs=5)


# ---------------------------------------------------------------------------
# words_positions tests
# ---------------------------------------------------------------------------

class TestWordsPositions:
    """Unit tests for words_positions."""

    def test_returns_scaled_word_positions(self, tmp_path: Path) -> None:
        """Words are returned with coordinates scaled by zoom factor."""
        pdf_path = create_test_pdf(tmp_path, [("Hello", 100, 400)])
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)

        result = words_positions(page, zoom=2)
        assert len(result) >= 1
        text, x0, y0, x1, y1 = result[0]
        assert text == "Hello"
        assert isinstance(x0, int)
        assert isinstance(y0, int)

    def test_zoom_factor_affects_coordinates(self, tmp_path: Path) -> None:
        """Higher zoom produces larger coordinate values."""
        pdf_path = create_test_pdf(tmp_path, [("Test", 100, 400)])
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)

        result_z1 = words_positions(page, zoom=1)
        result_z2 = words_positions(page, zoom=2)
        assert result_z2[0][1] == pytest.approx(result_z1[0][1] * 2, abs=2)

    def test_empty_page_returns_empty(self, tmp_path: Path) -> None:
        """A page with no text returns an empty list."""
        pdf_path = str(tmp_path / "blank.pdf")
        doc = fitz.open()
        doc.new_page(width=LETTER_WIDTH, height=LETTER_HEIGHT)
        doc.save(pdf_path)
        doc.close()

        doc2 = fitz.open(pdf_path)
        page = doc2.load_page(0)
        result = words_positions(page)
        assert result == []


# ---------------------------------------------------------------------------
# _measure_box_height tests
# ---------------------------------------------------------------------------

class TestMeasureBoxHeight:
    """Unit tests for _measure_box_height."""

    def test_single_row_returns_one(self) -> None:
        """A grey span on only one row returns height 1."""
        arr = np.zeros((10, 100), dtype=np.uint8)
        arr[5, 10:60] = 220  # grey span on row 5
        result = _measure_box_height(arr, 5, 10, 60, 200, 240)
        assert result == 1

    def test_multiple_grey_rows(self) -> None:
        """Consecutive grey rows increase the measured height."""
        arr = np.zeros((50, 100), dtype=np.uint8)
        for row in range(10, 30):
            arr[row, 20:80] = 220
        result = _measure_box_height(arr, 10, 20, 80, 200, 240)
        assert result == 20

    def test_stops_at_non_grey_row(self) -> None:
        """Measurement stops when a row is no longer grey."""
        arr = np.zeros((50, 100), dtype=np.uint8)
        for row in range(10, 15):
            arr[row, 20:80] = 220
        arr[15, 20:80] = 0  # non-grey row
        for row in range(16, 20):
            arr[row, 20:80] = 220
        result = _measure_box_height(arr, 10, 20, 80, 200, 240)
        assert result == 5

    def test_respects_max_100_rows(self) -> None:
        """Measurement caps at 100 rows below the start."""
        arr = np.full((200, 100), 220, dtype=np.uint8)
        result = _measure_box_height(arr, 0, 0, 100, 200, 240)
        assert result == 100


# ---------------------------------------------------------------------------
# _is_duplicate_box tests
# ---------------------------------------------------------------------------

class TestIsDuplicateBox:
    """Unit tests for _is_duplicate_box."""

    def test_no_existing_boxes(self) -> None:
        """No existing boxes means no duplicate."""
        assert _is_duplicate_box(10, 20, []) is False

    def test_exact_duplicate(self) -> None:
        """Exact same position is a duplicate."""
        boxes = [(10, 20, 50, 40)]
        assert _is_duplicate_box(10, 20, boxes) is True

    def test_near_duplicate_within_tolerance(self) -> None:
        """Position within tolerance is a duplicate."""
        boxes = [(10, 20, 50, 40)]
        assert _is_duplicate_box(12, 22, boxes, tolerance=5) is True

    def test_not_duplicate_outside_tolerance(self) -> None:
        """Position outside tolerance is not a duplicate."""
        boxes = [(10, 20, 50, 40)]
        assert _is_duplicate_box(100, 200, boxes) is False


# ---------------------------------------------------------------------------
# find_grey_boxes tests
# ---------------------------------------------------------------------------

class TestFindGreyBoxes:
    """Unit tests for find_grey_boxes."""

    def test_white_image_returns_empty(self) -> None:
        """An all-white image has no grey boxes."""
        img = Image.new("L", (200, 200), color=255)
        result = find_grey_boxes(img)
        assert result == []

    def test_black_image_returns_empty(self) -> None:
        """An all-black image has no grey boxes."""
        img = Image.new("L", (200, 200), color=0)
        result = find_grey_boxes(img)
        assert result == []

    def test_detects_grey_rectangle(self) -> None:
        """A grey rectangle meeting min_width and min_height is detected."""
        arr = np.full((200, 200), 255, dtype=np.uint8)
        # Draw a grey rectangle: rows 50-90, cols 20-120
        arr[50:90, 20:120] = 220
        img = Image.fromarray(arr, mode="L")

        result = find_grey_boxes(img, min_width=50, min_height=20)
        assert len(result) >= 1
        x0, y0, x1, y1 = result[0]
        assert x0 >= 15 and x0 <= 25
        assert y0 == 50

    def test_ignores_narrow_grey_span(self) -> None:
        """A grey span narrower than min_width is not detected."""
        arr = np.full((200, 200), 255, dtype=np.uint8)
        arr[50:90, 20:40] = 220  # only 20px wide
        img = Image.fromarray(arr, mode="L")

        result = find_grey_boxes(img, min_width=50, min_height=20)
        assert result == []

    def test_ignores_short_grey_span(self) -> None:
        """A grey span shorter than min_height is not detected."""
        arr = np.full((200, 200), 255, dtype=np.uint8)
        arr[50:55, 20:120] = 220  # only 5px tall
        img = Image.fromarray(arr, mode="L")

        result = find_grey_boxes(img, min_width=50, min_height=20)
        assert result == []

    def test_suppresses_duplicate_detections(self) -> None:
        """Near-duplicate detections at similar positions are suppressed."""
        arr = np.full((200, 200), 255, dtype=np.uint8)
        arr[50:90, 20:120] = 220
        img = Image.fromarray(arr, mode="L")

        result = find_grey_boxes(img, min_width=50, min_height=20)
        # Duplicate suppression uses tolerance=5, so detections within 5px
        # of each other are suppressed. A 40px tall box will produce a few
        # detections at ~5px intervals.
        assert len(result) < 40  # far fewer than one per row
        assert len(result) >= 1
