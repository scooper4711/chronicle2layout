"""Unit tests for overlay rendering."""

import fitz
import pytest

from layout_visualizer.models import PixelRect
from layout_visualizer.overlay_renderer import draw_overlays


def _make_white_pixmap(width: int, height: int) -> fitz.Pixmap:
    """Create a white RGB pixmap with the given dimensions."""
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), 0)
    pixmap.clear_with(255)
    return pixmap


class TestDrawOverlays:
    """Tests for draw_overlays."""

    def test_returns_pixmap_with_same_dimensions(self):
        """Output pixmap matches the input pixmap dimensions."""
        bg = _make_white_pixmap(200, 300)
        rects = {
            "main": PixelRect(name="main", x=10, y=10, x2=190, y2=290),
        }
        colors = {"main": (230, 25, 75)}

        result = draw_overlays(bg, rects, colors)

        assert isinstance(result, fitz.Pixmap)
        assert result.width == 200
        assert result.height == 300

    def test_returns_rgb_pixmap_without_alpha(self):
        """Output pixmap is RGB with no alpha channel."""
        bg = _make_white_pixmap(100, 100)
        rects = {
            "box": PixelRect(name="box", x=5, y=5, x2=95, y2=95),
        }
        colors = {"box": (60, 180, 75)}

        result = draw_overlays(bg, rects, colors)

        assert result.n == 3
        assert not result.alpha

    def test_multiple_regions_no_exception(self):
        """Drawing multiple canvas regions completes without error."""
        bg = _make_white_pixmap(400, 600)
        rects = {
            "header": PixelRect(name="header", x=10, y=10, x2=390, y2=60),
            "body": PixelRect(name="body", x=10, y=70, x2=390, y2=500),
            "footer": PixelRect(name="footer", x=10, y=510, x2=390, y2=590),
        }
        colors = {
            "header": (230, 25, 75),
            "body": (60, 180, 75),
            "footer": (0, 130, 200),
        }

        result = draw_overlays(bg, rects, colors)

        assert result.width == 400
        assert result.height == 600

    def test_empty_rects_returns_unchanged_dimensions(self):
        """An empty pixel_rects dict still returns a valid pixmap."""
        bg = _make_white_pixmap(150, 150)

        result = draw_overlays(bg, {}, {})

        assert result.width == 150
        assert result.height == 150

    def test_overlay_modifies_pixel_values(self):
        """Pixels inside an overlay region differ from the background."""
        bg = _make_white_pixmap(100, 100)
        rects = {
            "red_box": PixelRect(
                name="red_box", x=20, y=20, x2=80, y2=80,
            ),
        }
        colors = {"red_box": (255, 0, 0)}

        result = draw_overlays(bg, rects, colors)

        # A pixel inside the overlay should no longer be pure white
        inner_pixel = result.pixel(50, 50)
        assert inner_pixel != (255, 255, 255), (
            "Pixel inside overlay should differ from white background"
        )
