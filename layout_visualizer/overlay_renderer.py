"""Overlay drawing for canvas region visualization.

Draws semi-transparent colored rectangles, borders, and text labels
onto a PDF page pixmap using PyMuPDF's drawing primitives.
"""

import fitz

from layout_visualizer.models import PixelRect

_FILL_OPACITY = 0.4
_BORDER_WIDTH = 2.0
_FONT_SIZE = 10
_LABEL_PADDING = 3
_LABEL_BG_OPACITY = 0.85


def _compute_label_background_color(
    fill_color: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Return a darkened version of the fill color for label backgrounds.

    Darkening ensures the white label text remains readable against
    both the overlay rectangle and the underlying PDF content.
    """
    return (fill_color[0] * 0.4, fill_color[1] * 0.4, fill_color[2] * 0.4)


def _draw_single_overlay(
    shape: fitz.utils.Shape,
    rect: PixelRect,
    color_rgb: tuple[int, int, int],
) -> None:
    """Draw one canvas region: filled rect, border, and text label.

    Args:
        shape: PyMuPDF Shape object for the temporary page.
        rect: Pixel rectangle for this canvas region.
        color_rgb: RGB color tuple (0-255 per channel).
    """
    fitz_rect = fitz.Rect(rect.x, rect.y, rect.x2, rect.y2)
    fill = (color_rgb[0] / 255, color_rgb[1] / 255, color_rgb[2] / 255)

    # Semi-transparent filled rectangle with solid border
    shape.draw_rect(fitz_rect)
    shape.finish(
        color=fill,
        fill=fill,
        fill_opacity=_FILL_OPACITY,
        width=_BORDER_WIDTH,
    )

    # Label background
    label_bg = _compute_label_background_color(fill)
    label_x = rect.x + _LABEL_PADDING
    label_y = rect.y + _LABEL_PADDING

    text_width = fitz.get_text_length(rect.name, fontsize=_FONT_SIZE)
    text_height = _FONT_SIZE * 1.2

    bg_rect = fitz.Rect(
        label_x,
        label_y,
        label_x + text_width + _LABEL_PADDING * 2,
        label_y + text_height + _LABEL_PADDING * 2,
    )
    shape.draw_rect(bg_rect)
    shape.finish(fill=label_bg, fill_opacity=_LABEL_BG_OPACITY)

    # White text label
    text_point = fitz.Point(
        label_x + _LABEL_PADDING,
        label_y + _LABEL_PADDING + _FONT_SIZE,
    )
    shape.insert_text(text_point, rect.name, fontsize=_FONT_SIZE, color=(1, 1, 1))


def draw_overlays(
    pixmap: fitz.Pixmap,
    pixel_rects: dict[str, PixelRect],
    colors: dict[str, tuple[int, int, int]],
) -> fitz.Pixmap:
    """Draw semi-transparent rectangles and labels on the pixmap.

    Creates a temporary PDF page matching the pixmap dimensions,
    inserts the background pixmap as an image, draws overlays using
    PyMuPDF's Shape API, and renders the composited result.

    Args:
        pixmap: The background PDF page pixmap (RGB, no alpha).
        pixel_rects: Map of canvas name to PixelRect.
        colors: Map of canvas name to RGB color tuple.

    Returns:
        A new RGB pixmap with overlays composited onto the background.

    Requirements: layout-visualizer 6.1, 6.2, 6.3, 7.1, 7.2, 7.3
    """
    width = pixmap.width
    height = pixmap.height

    doc = fitz.open()
    page = doc.new_page(width=width, height=height)

    # Place background pixmap as the page image
    page.insert_image(fitz.Rect(0, 0, width, height), pixmap=pixmap)

    # Draw overlay shapes on top
    shape = page.new_shape()
    for name, rect in pixel_rects.items():
        color_rgb = colors.get(name, (200, 200, 200))
        _draw_single_overlay(shape, rect, color_rgb)
    shape.commit()

    # Render the composited page as an RGB pixmap
    result = page.get_pixmap()
    doc.close()
    return result
