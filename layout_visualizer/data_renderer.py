"""Data text rendering for layout data mode.

Renders example parameter values as styled text onto a PDF page pixmap
using PyMuPDF's text insertion API. Handles alignment computation,
multiline slot division, and font weight selection.
"""

import fitz

from layout_visualizer.models import (
    CheckboxEntry,
    DataContentEntry,
    PixelRect,
    RectangleEntry,
    StrikeoutEntry,
)


def compute_text_position(
    text: str,
    fontsize: float,
    font: str,
    is_bold: bool,
    align: str,
    bbox: PixelRect,
) -> fitz.Point:
    """Compute the insertion point for text within a bounding box.

    Uses the alignment code to position text horizontally and
    vertically within the box. Measures text width via
    ``fitz.get_text_length`` for horizontal alignment.

    Horizontal: L=left edge, C=centered, R=right edge.
    Vertical: B=bottom, M=middle, T=top.

    Args:
        text: The text string to render.
        fontsize: Font size in points.
        font: Font family name.
        is_bold: Whether the text is bold.
        align: Two-character alignment code (e.g. "LB", "CM").
        bbox: The bounding box in pixel coordinates.

    Returns:
        A fitz.Point for the text insertion position.

    Requirements: layout-data-mode 5.1-5.8
    """
    fontname = f"{font}-Bold" if is_bold else font
    text_width = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)

    box_width = bbox.x2 - bbox.x
    box_height = bbox.y2 - bbox.y

    horizontal = align[0]
    vertical = align[1]

    if horizontal == "L":
        x = bbox.x
    elif horizontal == "C":
        x = bbox.x + (box_width - text_width) / 2
    else:  # R
        x = bbox.x2 - text_width

    if vertical == "B":
        y = bbox.y2
    elif vertical == "M":
        y = bbox.y + (box_height + fontsize) / 2
    else:  # T
        y = bbox.y + fontsize

    return fitz.Point(x, y)


def _resolve_entry_pixel_rect(
    entry: DataContentEntry,
    canvas_rect: PixelRect,
) -> PixelRect:
    """Convert an entry's percentage coordinates to pixels within a canvas.

    Args:
        entry: The data content entry with percentage coords.
        canvas_rect: The resolved pixel rect for the entry's canvas.

    Returns:
        A PixelRect with absolute pixel coordinates.
    """
    canvas_width = canvas_rect.x2 - canvas_rect.x
    canvas_height = canvas_rect.y2 - canvas_rect.y

    return PixelRect(
        name=entry.param_name,
        x=canvas_rect.x + (entry.x / 100) * canvas_width,
        y=canvas_rect.y + (entry.y / 100) * canvas_height,
        x2=canvas_rect.x + (entry.x2 / 100) * canvas_width,
        y2=canvas_rect.y + (entry.y2 / 100) * canvas_height,
    )


def _pixel_rect_to_points(rect: PixelRect, scale: float) -> PixelRect:
    """Convert a pixel-space rectangle to point-space coordinates.

    Args:
        rect: Rectangle in pixel coordinates.
        scale: DPI scale factor (dpi / 72).

    Returns:
        A new PixelRect with coordinates divided by the scale factor.
    """
    return PixelRect(
        name=rect.name,
        x=rect.x / scale,
        y=rect.y / scale,
        x2=rect.x2 / scale,
        y2=rect.y2 / scale,
    )


def _select_fontname(font: str, is_bold: bool) -> str:
    """Return the PyMuPDF fontname, appending '-Bold' when needed."""
    return f"{font}-Bold" if is_bold else font


def draw_data_text(
    pixmap: fitz.Pixmap,
    entries: list[DataContentEntry],
    canvas_pixels: dict[str, PixelRect],
    rectangles: list[RectangleEntry] | None = None,
    checkboxes: list[CheckboxEntry] | None = None,
    strikeouts: list[StrikeoutEntry] | None = None,
    dpi: int = 150,
) -> fitz.Pixmap:
    """Render example text onto the PDF page pixmap.

    Creates a temporary PDF page sized in points (matching the
    original PDF dimensions), inserts the background pixmap, then
    for each DataContentEntry:

    1. Converts the entry's pixel bounding box to point-space
       coordinates (dividing by the DPI scale factor).
    2. Computes the text insertion point using alignment.
    3. Inserts the text with the specified font, size, and weight.

    The final pixmap is rendered at the same DPI as the input so
    that font sizes match the Foundry VTT chronicle generator.

    For multiline entries, divides the bounding box height by the
    lines count and renders the example value in the first line slot.

    Args:
        pixmap: The background PDF page pixmap (RGB).
        entries: Resolved DataContentEntry instances.
        canvas_pixels: Map of canvas name to resolved PixelRect.
        dpi: The DPI at which the background pixmap was rendered
             (default 150, matching ``render_pdf_page``).

    Returns:
        A new RGB pixmap with text rendered on the background.

    Requirements: layout-data-mode 4.1-4.5, 5.1-5.8, 6.1-6.3, 9.3
    """
    scale = dpi / 72.0
    page_width_pt = pixmap.width / scale
    page_height_pt = pixmap.height / scale

    doc = fitz.open()
    page = doc.new_page(width=page_width_pt, height=page_height_pt)
    page.insert_image(
        fitz.Rect(0, 0, page_width_pt, page_height_pt), pixmap=pixmap,
    )

    shape = page.new_shape()

    for rect_entry in (rectangles or []):
        if rect_entry.canvas not in canvas_pixels:
            continue
        canvas_rect = canvas_pixels[rect_entry.canvas]
        canvas_w = canvas_rect.x2 - canvas_rect.x
        canvas_h = canvas_rect.y2 - canvas_rect.y
        px = PixelRect(
            name="rect",
            x=canvas_rect.x + (rect_entry.x / 100) * canvas_w,
            y=canvas_rect.y + (rect_entry.y / 100) * canvas_h,
            x2=canvas_rect.x + (rect_entry.x2 / 100) * canvas_w,
            y2=canvas_rect.y + (rect_entry.y2 / 100) * canvas_h,
        )
        pt = _pixel_rect_to_points(px, scale)
        shape.draw_rect(fitz.Rect(pt.x, pt.y, pt.x2, pt.y2))
        shape.finish(fill=rect_entry.color, color=rect_entry.color)

    for cb in (checkboxes or []):
        if cb.canvas not in canvas_pixels:
            continue
        canvas_rect = canvas_pixels[cb.canvas]
        canvas_w = canvas_rect.x2 - canvas_rect.x
        canvas_h = canvas_rect.y2 - canvas_rect.y
        px = PixelRect(
            name="checkbox",
            x=canvas_rect.x + (cb.x / 100) * canvas_w,
            y=canvas_rect.y + (cb.y / 100) * canvas_h,
            x2=canvas_rect.x + (cb.x2 / 100) * canvas_w,
            y2=canvas_rect.y + (cb.y2 / 100) * canvas_h,
        )
        pt = _pixel_rect_to_points(px, scale)
        cx = (pt.x + pt.x2) / 2
        cy = (pt.y + pt.y2) / 2
        size = min(pt.x2 - pt.x, pt.y2 - pt.y) * 0.35
        shape.draw_line(
            fitz.Point(cx - size, cy - size),
            fitz.Point(cx + size, cy + size),
        )
        shape.finish(color=cb.color, width=1.5)
        shape.draw_line(
            fitz.Point(cx + size, cy - size),
            fitz.Point(cx - size, cy + size),
        )
        shape.finish(color=cb.color, width=1.5)

    for so in (strikeouts or []):
        if so.canvas not in canvas_pixels:
            continue
        canvas_rect = canvas_pixels[so.canvas]
        canvas_w = canvas_rect.x2 - canvas_rect.x
        canvas_h = canvas_rect.y2 - canvas_rect.y
        px = PixelRect(
            name="strikeout",
            x=canvas_rect.x + (so.x / 100) * canvas_w,
            y=canvas_rect.y + (so.y / 100) * canvas_h,
            x2=canvas_rect.x + (so.x2 / 100) * canvas_w,
            y2=canvas_rect.y + (so.y2 / 100) * canvas_h,
        )
        pt = _pixel_rect_to_points(px, scale)
        rect = fitz.Rect(pt.x, pt.y, pt.x2, pt.y2)
        shape.draw_rect(rect)
        shape.finish(
            fill=(so.color[0], so.color[1], so.color[2]),
            color=so.color,
            width=0.5,
            fill_opacity=0.15,
        )

    for entry in entries:
        if entry.canvas not in canvas_pixels:
            continue

        canvas_rect = canvas_pixels[entry.canvas]
        pixel_bbox = _resolve_entry_pixel_rect(entry, canvas_rect)
        pt_bbox = _pixel_rect_to_points(pixel_bbox, scale)
        is_bold = entry.fontweight == "bold"
        fontname = _select_fontname(entry.font, is_bold)

        if entry.entry_type == "multiline" and entry.lines > 1:
            slot_height = (pt_bbox.y2 - pt_bbox.y) / entry.lines
            lines = entry.example_value.split("\n")
            for line_idx, line_text in enumerate(lines[:entry.lines]):
                slot = PixelRect(
                    name=pt_bbox.name,
                    x=pt_bbox.x,
                    y=pt_bbox.y + slot_height * line_idx,
                    x2=pt_bbox.x2,
                    y2=pt_bbox.y + slot_height * (line_idx + 1),
                )
                point = compute_text_position(
                    line_text, entry.fontsize, entry.font,
                    is_bold, entry.align, slot,
                )
                shape.insert_text(
                    point,
                    line_text,
                    fontname=fontname,
                    fontsize=entry.fontsize,
                    color=(0, 0, 0),
                )
        else:
            point = compute_text_position(
                entry.example_value, entry.fontsize, entry.font,
                is_bold, entry.align, pt_bbox,
            )
            shape.insert_text(
                point,
                entry.example_value,
                fontname=fontname,
                fontsize=entry.fontsize,
                color=(0, 0, 0),
            )

    shape.commit()

    result = page.get_pixmap(dpi=dpi)
    doc.close()
    return result
