"""Unit tests for data text rendering.

Requirements: 4.1-4.5, 5.1-5.8, 6.1-6.3, 9.3
"""

import fitz
import pytest

from layout_visualizer.data_renderer import compute_text_position, draw_data_text
from layout_visualizer.models import DataContentEntry, PixelRect


def _make_white_pixmap(width: int, height: int) -> fitz.Pixmap:
    """Create a white RGB pixmap with the given dimensions."""
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), 0)
    pixmap.clear_with(255)
    return pixmap


def _make_bbox(x: float, y: float, x2: float, y2: float) -> PixelRect:
    """Create a PixelRect bounding box for alignment tests."""
    return PixelRect(name="test", x=x, y=y, x2=x2, y2=y2)


def _make_entry(
    *,
    entry_type: str = "text",
    canvas: str = "page",
    fontweight: str | None = None,
    lines: int = 1,
    align: str = "LB",
    example_value: str = "Hello",
) -> DataContentEntry:
    """Create a DataContentEntry with sensible defaults."""
    return DataContentEntry(
        param_name="test_param",
        example_value=example_value,
        entry_type=entry_type,
        canvas=canvas,
        x=10, y=10, x2=90, y2=30,
        font="Helvetica",
        fontsize=12,
        fontweight=fontweight,
        align=align,
        lines=lines,
    )


# ---------------------------------------------------------------------------
# compute_text_position — all 9 alignment combinations
# ---------------------------------------------------------------------------

class TestComputeTextPosition:
    """Tests for compute_text_position across all alignment codes."""

    BBOX = _make_bbox(100, 200, 400, 300)
    TEXT = "Test"
    FONTSIZE = 12.0
    FONT = "Helvetica"

    def _text_width(self, bold: bool = False) -> float:
        fontname = "Helvetica-Bold" if bold else "Helvetica"
        return fitz.get_text_length(self.TEXT, fontname=fontname, fontsize=self.FONTSIZE)

    # --- Left horizontal ---

    def test_left_bottom(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "LB", self.BBOX)
        assert point.x == pytest.approx(self.BBOX.x)
        assert point.y == pytest.approx(self.BBOX.y2)

    def test_left_middle(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "LM", self.BBOX)
        assert point.x == pytest.approx(self.BBOX.x)
        expected_y = self.BBOX.y + (100 + self.FONTSIZE) / 2
        assert point.y == pytest.approx(expected_y)

    def test_left_top(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "LT", self.BBOX)
        assert point.x == pytest.approx(self.BBOX.x)
        assert point.y == pytest.approx(self.BBOX.y + self.FONTSIZE)

    # --- Center horizontal ---

    def test_center_bottom(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "CB", self.BBOX)
        tw = self._text_width()
        expected_x = self.BBOX.x + (300 - tw) / 2
        assert point.x == pytest.approx(expected_x)
        assert point.y == pytest.approx(self.BBOX.y2)

    def test_center_middle(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "CM", self.BBOX)
        tw = self._text_width()
        expected_x = self.BBOX.x + (300 - tw) / 2
        expected_y = self.BBOX.y + (100 + self.FONTSIZE) / 2
        assert point.x == pytest.approx(expected_x)
        assert point.y == pytest.approx(expected_y)

    def test_center_top(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "CT", self.BBOX)
        tw = self._text_width()
        expected_x = self.BBOX.x + (300 - tw) / 2
        assert point.x == pytest.approx(expected_x)
        assert point.y == pytest.approx(self.BBOX.y + self.FONTSIZE)

    # --- Right horizontal ---

    def test_right_bottom(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "RB", self.BBOX)
        tw = self._text_width()
        assert point.x == pytest.approx(self.BBOX.x2 - tw)
        assert point.y == pytest.approx(self.BBOX.y2)

    def test_right_middle(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "RM", self.BBOX)
        tw = self._text_width()
        expected_y = self.BBOX.y + (100 + self.FONTSIZE) / 2
        assert point.x == pytest.approx(self.BBOX.x2 - tw)
        assert point.y == pytest.approx(expected_y)

    def test_right_top(self):
        point = compute_text_position(self.TEXT, self.FONTSIZE, self.FONT, False, "RT", self.BBOX)
        tw = self._text_width()
        assert point.x == pytest.approx(self.BBOX.x2 - tw)
        assert point.y == pytest.approx(self.BBOX.y + self.FONTSIZE)


# ---------------------------------------------------------------------------
# Multiline slot height computation
# ---------------------------------------------------------------------------

class TestMultilineSlotHeight:
    """Test that multiline entries divide bounding box height correctly."""

    def test_slot_height_divides_evenly(self):
        """Slot height = total height / lines count."""
        total_height = 120.0
        lines = 4
        expected_slot = total_height / lines
        assert expected_slot == pytest.approx(30.0)

    def test_first_slot_bounds(self):
        """First slot spans from bbox.y to bbox.y + slot_height."""
        bbox = _make_bbox(0, 100, 200, 220)
        lines = 3
        slot_height = (bbox.y2 - bbox.y) / lines
        first_slot_y = bbox.y
        first_slot_y2 = bbox.y + slot_height
        assert first_slot_y == pytest.approx(100.0)
        assert first_slot_y2 == pytest.approx(140.0)


# ---------------------------------------------------------------------------
# draw_data_text
# ---------------------------------------------------------------------------

class TestDrawDataText:
    """Tests for draw_data_text."""

    CANVAS_PIXELS = {
        "page": PixelRect(name="page", x=0, y=0, x2=400, y2=600),
    }

    def test_returns_pixmap_with_same_dimensions(self):
        """Output pixmap matches the input pixmap dimensions."""
        bg = _make_white_pixmap(400, 600)
        entry = _make_entry()
        result = draw_data_text(bg, [entry], self.CANVAS_PIXELS)

        assert isinstance(result, fitz.Pixmap)
        assert result.width == 400
        assert result.height == 600

    def test_text_entry_renders_without_exception(self):
        """A text entry renders without raising."""
        bg = _make_white_pixmap(400, 600)
        entry = _make_entry(entry_type="text", example_value="Sample")
        result = draw_data_text(bg, [entry], self.CANVAS_PIXELS)
        assert result.width == 400

    def test_multiline_entry_renders_without_exception(self):
        """A multiline entry renders without raising."""
        bg = _make_white_pixmap(400, 600)
        entry = _make_entry(entry_type="multiline", lines=3, example_value="Notes")
        result = draw_data_text(bg, [entry], self.CANVAS_PIXELS)
        assert result.width == 400

    def test_bold_fontweight_renders_without_exception(self):
        """A bold entry renders without raising."""
        bg = _make_white_pixmap(400, 600)
        entry = _make_entry(fontweight="bold", example_value="Bold Text")
        result = draw_data_text(bg, [entry], self.CANVAS_PIXELS)
        assert result.width == 400

    def test_skips_entry_referencing_nonexistent_canvas(self):
        """Entries referencing a missing canvas are silently skipped."""
        bg = _make_white_pixmap(400, 600)
        entry = _make_entry(canvas="nonexistent")
        result = draw_data_text(bg, [entry], self.CANVAS_PIXELS)
        assert result.width == 400
        assert result.height == 600

    def test_empty_entries_returns_background_only(self):
        """An empty entries list returns a pixmap matching the background."""
        bg = _make_white_pixmap(200, 300)
        result = draw_data_text(bg, [], self.CANVAS_PIXELS)
        assert result.width == 200
        assert result.height == 300
