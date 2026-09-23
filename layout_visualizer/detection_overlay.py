"""Composable overlay collection for ``--show`` rendering.

Combines blueprint2layout detection categories (``h_thin``, ``h_bar``,
``h_rule``, ``v_thin``, ``v_bar``, ``grey_box``) with layout overlay
categories (``canvases``, ``fields``) into a single rect/color pair
ready for :func:`layout_visualizer.overlay_renderer.draw_overlays`.

Detection runs on the cleaned *last* page of the PDF (matching
blueprint2layout), while the background pixmap is the *first* page —
chronicle PDFs are single-page, so the two align.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from blueprint2layout.detection import detect_structures
from blueprint2layout.models import DetectionResult, GreyBox, HorizontalLine, VerticalLine
from blueprint2layout.pdf_preparation import prepare_page

from layout_visualizer.coordinate_resolver import (
    assign_colors,
    resolve_canvas_pixels,
    resolve_field_pixels,
)
from layout_visualizer.layout_loader import (
    load_content_fields,
    load_layout_with_inheritance,
)
from layout_visualizer.models import PixelRect

DETECTION_CATEGORIES = ("h_thin", "h_bar", "h_rule", "v_thin", "v_bar", "grey_box")
OVERLAY_CATEGORIES: tuple[str, ...] = DETECTION_CATEGORIES + ("canvases", "fields")

DETECTION_COLORS: dict[str, tuple[int, int, int]] = {
    "h_thin": (230, 25, 75),
    "h_bar": (245, 130, 48),
    "h_rule": (255, 200, 0),
    "v_thin": (0, 130, 200),
    "v_bar": (70, 240, 240),
    "grey_box": (145, 30, 180),
}


def parse_show_value(value: str) -> frozenset[str]:
    """Parse a comma-separated ``--show`` value into a category set.

    Args:
        value: Comma-separated category names (e.g. ``h_thin,canvases``).

    Returns:
        Frozenset of validated category names (empty string yields empty set).

    Raises:
        argparse.ArgumentTypeError: If any category is unknown.
    """
    parts = frozenset(part.strip() for part in value.split(",") if part.strip())
    unknown = sorted(parts - set(OVERLAY_CATEGORIES))
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown --show categor{'ies' if len(unknown) > 1 else 'y'}: "
            f"{', '.join(unknown)}; choose from: {', '.join(OVERLAY_CATEGORIES)}"
        )
    return parts


def _percent_rect(
    name: str,
    x: float,
    y: float,
    x2: float,
    y2: float,
    page_width: int,
    page_height: int,
) -> PixelRect:
    """Convert absolute page percentages to a pixel rectangle."""
    return PixelRect(
        name=name,
        x=x / 100 * page_width,
        y=y / 100 * page_height,
        x2=x2 / 100 * page_width,
        y2=y2 / 100 * page_height,
    )


def _horizontal_rect(
    line: HorizontalLine,
    name: str,
    page_width: int,
    page_height: int,
) -> PixelRect:
    """Convert a detected horizontal line to a pixel rectangle."""
    return _percent_rect(name, line.x, line.y, line.x2, line.y2, page_width, page_height)


def _vertical_rect(
    line: VerticalLine,
    name: str,
    page_width: int,
    page_height: int,
) -> PixelRect:
    """Convert a detected vertical line to a pixel rectangle."""
    return _percent_rect(name, line.x, line.y, line.x2, line.y2, page_width, page_height)


def _grey_box_rect(
    box: GreyBox,
    name: str,
    page_width: int,
    page_height: int,
) -> PixelRect:
    """Convert a detected grey box to a pixel rectangle."""
    return _percent_rect(name, box.x, box.y, box.x2, box.y2, page_width, page_height)


def _detection_rects(
    detection: DetectionResult,
    show: frozenset[str],
    page_width: int,
    page_height: int,
) -> dict[str, PixelRect]:
    """Build pixel rectangles for the requested detection categories.

    Element names use the blueprint reference form (``h_thin[0]``, …)
    with the same zero-based indexes blueprint2layout resolves.
    """
    rects: dict[str, PixelRect] = {}
    for category in DETECTION_CATEGORIES:
        if category not in show:
            continue
        elements = getattr(detection, category)
        for index, element in enumerate(elements):
            name = f"{category}[{index}]"
            if isinstance(element, GreyBox):
                rect = _grey_box_rect(element, name, page_width, page_height)
            elif isinstance(element, VerticalLine):
                rect = _vertical_rect(element, name, page_width, page_height)
            else:
                rect = _horizontal_rect(element, name, page_width, page_height)
            rects[name] = rect
    return rects


def _unique_key(base: str, existing: dict[str, PixelRect]) -> str:
    """Return base, or base with a numeric suffix if already present."""
    if base not in existing:
        return base
    suffix = 1
    while f"{base}_{suffix}" in existing:
        suffix += 1
    return f"{base}_{suffix}"


def _run_detection(pdf_path: Path) -> DetectionResult:
    """Run blueprint2layout detection on the chronicle PDF."""
    grayscale, rgb = prepare_page(str(pdf_path))
    return detect_structures(grayscale, rgb, pdf_path=str(pdf_path))


def collect_overlay_rects(
    layout_path: Path,
    layout_index: dict[str, Path],
    pdf_path: Path,
    page_width: int,
    page_height: int,
    show: frozenset[str],
) -> tuple[dict[str, PixelRect], dict[str, tuple[int, int, int]]]:
    """Collect pixel rects and colors for the requested overlay categories.

    Args:
        layout_path: Path to the target layout JSON file.
        layout_index: Map of layout ids to file paths.
        pdf_path: Path to the chronicle PDF (for detection).
        page_width: Background pixmap width in pixels.
        page_height: Background pixmap height in pixels.
        show: Requested overlay categories.

    Returns:
        Tuple of (rects keyed by label, colors keyed by the same labels).

    Raises:
        FileNotFoundError: If the PDF does not exist.
        ValueError: If layout JSON is invalid or parent not found.
    """
    rects: dict[str, PixelRect] = {}
    colors: dict[str, tuple[int, int, int]] = {}

    requested_detection = [c for c in DETECTION_CATEGORIES if c in show]
    if requested_detection:
        detection = _run_detection(pdf_path)
        detection_rects = _detection_rects(
            detection, show, page_width, page_height,
        )
        for name, rect in detection_rects.items():
            category = name.split("[", 1)[0]
            rects[name] = rect
            colors[name] = DETECTION_COLORS[category]

    named_rects: list[PixelRect] = []
    if "fields" in show:
        fields, field_canvases, _chain = load_content_fields(
            layout_path, layout_index,
        )
        canvas_pixels = resolve_canvas_pixels(
            field_canvases, page_width, page_height,
        )
        if "canvases" in show:
            named_rects.extend(canvas_pixels.values())
        named_rects.extend(resolve_field_pixels(fields, canvas_pixels).values())
    elif "canvases" in show:
        canvases, _chain = load_layout_with_inheritance(layout_path, layout_index)
        canvas_pixels = resolve_canvas_pixels(canvases, page_width, page_height)
        named_rects.extend(canvas_pixels.values())

    palette_names: list[str] = []
    for rect in named_rects:
        key = _unique_key(rect.name, rects)
        rects[key] = PixelRect(
            name=key,
            x=rect.x,
            y=rect.y,
            x2=rect.x2,
            y2=rect.y2,
            parent=rect.parent,
        )
        palette_names.append(key)

    for name, color in assign_colors(palette_names).items():
        colors[name] = color

    return rects, colors
