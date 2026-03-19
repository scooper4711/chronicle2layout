"""Shared utility functions for the chronicle2layout package.

Consolidates functions that were previously duplicated across multiple modules
into a single source of truth. All layout file resolution, canvas coordinate
transformation, and PDF image rendering should use these functions.

Public functions:
    find_layout_file: Resolve a layout ID to a filesystem Path.
    transform_canvas_coordinates: Transform canvas coordinates to absolute page percentages.
    render_page_to_image: Render the last page of a PDF to a PIL Image.
    words_positions: Extract word bounding boxes from a PDF page, scaled by zoom factor.
    find_grey_boxes: Detect light grey filled rectangles (form fields) in an image.

Requirements: refactor-chronicle2layout 1.1, 1.2, 1.6, 1.7, 1.8, 5.1, 5.2, 7.3, 8.1, 10.1
"""

import re
from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def _resolve_season_layout(search_base: Path, season_num: str, variant: str | None) -> Path:
    """Resolve a season-based layout ID to a file path."""
    season_dir = search_base / f"s{season_num}"
    if variant:
        generated = season_dir / f"Season{season_num}{variant}.generated.json"
        if generated.exists():
            return generated
        return season_dir / f"Season{season_num}{variant}.json"
    return season_dir / f"Season {season_num}.json"


def find_layout_file(layout_dir: str, layout_id: str) -> Path:
    """Resolve a layout ID string to the corresponding layout JSON file path.

    Supports several layout ID patterns:
      - Single-part ID: ``pfs2`` → ``<layout_dir>/pfs2/pfs2.json``
      - Season parent: ``pfs2.season5`` → ``<layout_dir>/pfs2/s5/Season 5.json``
      - Season variant: ``pfs2.season4a`` → ``<layout_dir>/pfs2/s4/Season4a.json``
        (checks for ``.generated.json`` first, falls back to ``.json``)
      - Scenario reference: ``pfs2.s5-07`` → ``<layout_dir>/pfs2/s5/s5-07.json``
      - Generic fallback: ``pfs2.foo`` → ``<layout_dir>/pfs2/foo/foo.json``

    Args:
        layout_dir: Base layouts directory (e.g. ``'layouts'``).
        layout_id: Dot-separated layout identifier (e.g. ``'pfs2.season5'``).

    Returns:
        Resolved ``Path`` to the layout JSON file.

    Raises:
        ValueError: If the resolved layout file does not exist on disk.
    """
    base_path = Path(layout_dir)
    parts = layout_id.split(".")

    if len(parts) == 1:
        layout_file = base_path / parts[0] / f"{parts[0]}.json"
    else:
        search_base = base_path / parts[0]
        ident = parts[1]
        match = re.match(r"^season(\d+)([a-z])?$", ident)

        if match:
            layout_file = _resolve_season_layout(
                search_base, match.group(1), match.group(2)
            )
        elif ident.startswith("s") and "-" in ident:
            season_num = ident.split("-")[0][1:]
            layout_file = search_base / f"s{season_num}" / f"{ident}.json"
        else:
            layout_file = search_base / ident / f"{ident}.json"

    if not layout_file.exists():
        raise ValueError(f"Layout file not found: {layout_file}")

    return layout_file


def transform_canvas_coordinates(layout_json: dict, canvas_name: str) -> list[float]:
    """Transform canvas coordinates to absolute page percentages by following the parent chain.

    Each canvas entry in the layout JSON defines coordinates as percentages of its
    parent canvas (or the full page if no parent is specified). This function
    recursively resolves parent references to produce absolute page-level
    percentage coordinates.

    Args:
        layout_json: The loaded layout JSON object containing a ``"canvas"`` key.
        canvas_name: Name of the canvas to transform (e.g. ``"items"``).

    Returns:
        A list ``[x, y, x2, y2]`` of absolute page percentage coordinates.

    Raises:
        ValueError: If *canvas_name* is not found in the layout's ``"canvas"`` dict.
    """
    if "canvas" not in layout_json or canvas_name not in layout_json["canvas"]:
        raise ValueError(f"Canvas {canvas_name} not found in layout")

    def transform(name: str) -> list[float]:
        canvas = layout_json["canvas"][name]
        x, y, x2, y2 = canvas["x"], canvas["y"], canvas["x2"], canvas["y2"]

        if "parent" in canvas:
            px, py, px2, py2 = transform(canvas["parent"])
            pw = px2 - px
            ph = py2 - py
            x = px + (x / 100.0) * pw
            y = py + (y / 100.0) * ph
            x2 = px + (x2 / 100.0) * pw
            y2 = py + (y2 / 100.0) * ph

        return [x, y, x2, y2]

    return transform(canvas_name)


def render_page_to_image(pdf_path: str, zoom: int = 2) -> tuple[fitz.Page, Image.Image]:
    """Render the last page of a PDF document to a PIL Image.

    Opens the PDF, selects the last page, and renders it at the given zoom
    level using PyMuPDF. Returns both the page object (for text extraction)
    and the rendered image.

    Args:
        pdf_path: Filesystem path to the PDF file.
        zoom: Rendering scale factor (default 2 for 2× resolution).

    Returns:
        A tuple of ``(page, image)`` where *page* is the PyMuPDF ``Page``
        object and *image* is the rendered ``PIL.Image.Image``.

    Requirements: refactor-chronicle2layout 7.3
    """
    doc = fitz.open(str(pdf_path))
    page = doc.load_page(doc.page_count - 1)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return page, img


def words_positions(
    page: fitz.Page, zoom: int = 2
) -> list[tuple[str, int, int, int, int]]:
    """Extract word bounding boxes from a PDF page, scaled by a zoom factor.

    Each word is returned as a tuple of ``(text, x0, y0, x1, y1)`` where
    the coordinates are integer pixel positions at the given zoom level.

    Args:
        page: A PyMuPDF ``Page`` object to extract words from.
        zoom: Scale factor applied to the raw PDF coordinates (default 2).

    Returns:
        A list of ``(text, x0, y0, x1, y1)`` tuples for every word on the page.

    Requirements: refactor-chronicle2layout 7.3
    """
    words = page.get_text("words")
    scaled: list[tuple[str, int, int, int, int]] = []
    for w in words:
        x0, y0, x1, y1, text, _, _, _ = w
        scaled.append((text, int(x0 * zoom), int(y0 * zoom), int(x1 * zoom), int(y1 * zoom)))
    return scaled


def _measure_box_height(
    arr: np.ndarray,
    y: int,
    x_start: int,
    x_end: int,
    grey_min: int,
    grey_max: int,
) -> int:
    """Measure how many rows below y maintain a grey span from x_start to x_end."""
    h = arr.shape[0]
    span_width = x_end - x_start
    box_height = 1
    for y2 in range(y + 1, min(y + 100, h)):
        grey_count = np.sum(
            (arr[y2, x_start:x_end] >= grey_min)
            & (arr[y2, x_start:x_end] <= grey_max)
        )
        if grey_count / span_width < 0.7:
            break
        box_height += 1
    return box_height


def _is_duplicate_box(
    x_start: int,
    y: int,
    boxes: list[tuple[int, int, int, int]],
    tolerance: int = 5,
) -> bool:
    """Check if a box at (x_start, y) is a near-duplicate of an existing box."""
    return any(
        abs(x_start - bx0) < tolerance and abs(y - by0) < tolerance
        for bx0, by0, _, _ in boxes
    )


def find_grey_boxes(
    img: Image.Image,
    grey_min: int = 200,
    grey_max: int = 240,
    min_width: int = 50,
    min_height: int = 20,
) -> list[tuple[int, int, int, int]]:
    """Detect light grey filled rectangles in an image.

    Scans the image row-by-row for horizontal spans of grey pixels, then
    checks whether each span extends vertically to form a box. Duplicate
    detections at nearly the same position are suppressed.

    Args:
        img: A PIL ``Image.Image`` to scan (will be converted to greyscale).
        grey_min: Minimum greyscale value to consider as "grey" (default 200).
        grey_max: Maximum greyscale value to consider as "grey" (default 240).
        min_width: Minimum horizontal span in pixels to qualify (default 50).
        min_height: Minimum vertical extent in pixels to qualify (default 20).

    Returns:
        A list of ``(x0, y0, x1, y1)`` bounding-box tuples for each detected
        grey rectangle.

    Requirements: refactor-chronicle2layout 7.3
    """
    arr = np.array(img.convert("L"))
    h, w = arr.shape

    boxes: list[tuple[int, int, int, int]] = []
    for y in range(h):
        in_grey = False
        x_start = 0
        for x in range(w):
            is_grey = grey_min <= arr[y, x] <= grey_max
            if is_grey and not in_grey:
                x_start = x
                in_grey = True
            elif not is_grey and in_grey:
                if x - x_start >= min_width:
                    box_height = _measure_box_height(arr, y, x_start, x, grey_min, grey_max)
                    if box_height >= min_height and not _is_duplicate_box(x_start, y, boxes):
                        boxes.append((x_start, y, x, y + box_height))
                in_grey = False

    return boxes
