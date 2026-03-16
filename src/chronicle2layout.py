"""chronicle2layout — CLI entry point.

Detect checkboxes and extract text lines from a single-page PDF
and output layout-compatible JSON.

Requirements: refactor-chronicle2layout 4.1, 4.2, 4.6, 5.3, 5.5, 3.2, 3.4
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

import fitz  # PyMuPDF

from shared_utils import find_layout_file, transform_canvas_coordinates
from layout_generator import generate_layout_json

DEFAULT_REGION_PCT: list[float] = [0.5, 50.8, 40.0, 83.0]
"""Default item-region coordinates [x0, y0, x1, y1] as page percentages."""

Y_COORDINATE_GROUPING_TOLERANCE: float = 2.0
"""Maximum vertical distance (in PDF points) for grouping words into the same line."""


def _resolve_region_from_layout(
    layout_dir: str, parent_id: str, canvas_name: str,
) -> Optional[list[float]]:
    """Attempt to load region coordinates from a parent layout file."""
    try:
        base_layout_path = find_layout_file(layout_dir, parent_id)
        with open(base_layout_path) as f:
            base_layout = json.load(f)
            return transform_canvas_coordinates(base_layout, canvas_name)
    except Exception as e:
        print(f"Warning: Failed to load layout file: {e}", file=sys.stderr)
        return None


def _group_words_by_line(
    words_on_page: list[tuple],
    region_x0: float,
    region_y0: float,
    region_x2: float,
    region_y2: float,
) -> dict[float, list[dict]]:
    """Filter words to a region and group into lines by y-coordinate.

    Words within Y_COORDINATE_GROUPING_TOLERANCE of each other vertically
    are considered part of the same line.

    Requirements: refactor-chronicle2layout 3.2, 3.4
    """
    lines_dict: dict[float, list[dict]] = {}

    for word_data in words_on_page:
        x0, y0, x1, y1, text, _block_no, _line_no, _word_no = word_data

        if not (x0 >= region_x0 and x1 <= region_x2
                and y0 >= region_y0 and y1 <= region_y2):
            continue

        quantized_y = _find_matching_line_y(y0, lines_dict)
        if quantized_y is None:
            quantized_y = y0
            lines_dict[quantized_y] = []

        lines_dict[quantized_y].append({
            'text': text, 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
        })

    return lines_dict


def _find_matching_line_y(
    y0: float,
    lines_dict: dict[float, list[dict]],
) -> Optional[float]:
    """Return an existing line key within tolerance of y0, or None."""
    for existing_y in lines_dict:
        if abs(y0 - existing_y) <= Y_COORDINATE_GROUPING_TOLERANCE:
            return existing_y
    return None


def _convert_lines_to_results(
    lines_dict: dict[float, list[dict]],
    region_x0: float,
    region_y0: float,
    region_width: float,
    region_height: float,
) -> list[dict]:
    """Convert grouped word lines into percentage-based result dicts.

    Each result contains joined text and bounding-box coordinates
    as percentages relative to the extraction region.

    Requirements: refactor-chronicle2layout 3.2, 3.4
    """
    results: list[dict] = []

    for y_coord in sorted(lines_dict.keys()):
        words = lines_dict[y_coord]
        if not words:
            continue

        words.sort(key=lambda w: w['x0'])
        text = ' '.join(w['text'] for w in words)

        if text.lower().strip() in ['items', 'items:']:
            continue

        x0 = min(w['x0'] for w in words)
        y0 = min(w['y0'] for w in words)
        x1 = max(w['x1'] for w in words)
        y1 = max(w['y1'] for w in words)

        x0_pct = ((x0 - region_x0) / region_width) * 100.0
        y0_pct = ((y0 - region_y0) / region_height) * 100.0
        x1_pct = ((x1 - region_x0) / region_width) * 100.0
        y1_pct = ((y1 - region_y0) / region_height) * 100.0

        results.append({
            'text': text,
            'top_left_pct': [round(x0_pct, 3), round(y0_pct, 3)],
            'bottom_right_pct': [round(x1_pct, 3), round(y1_pct, 3)],
        })

    return results


def extract_text_lines(
    pdf_path: str,
    region_pct: Optional[list[float]] = None,
    zoom: int = 6,
    debug_dir: Optional[str] = None,
    layout_dir: Optional[str] = None,
    parent_id: Optional[str] = None,
    canvas_name: str = "items",
) -> list[dict]:
    """Extract text lines from a PDF region using PyMuPDF text extraction.

    Opens the last page of the PDF, resolves the extraction region (from
    arguments, a parent layout file, or the default), then groups words
    into lines and converts them to percentage-based coordinates.

    Args:
        pdf_path: Path to the PDF file.
        region_pct: Optional [x0, y0, x1, y1] in percent to extract from.
        zoom: Not used, kept for API compatibility.
        debug_dir: Optional debug output directory.
        layout_dir: Base layouts directory.
        parent_id: Parent layout ID for finding canvas.
        canvas_name: Name of the canvas to extract from.

    Returns:
        List of dicts with 'text', 'top_left_pct', 'bottom_right_pct'.

    Requirements: refactor-chronicle2layout 4.1, 4.2, 4.6, 5.3, 5.5, 3.2, 3.4
    """
    doc = fitz.open(pdf_path)
    if doc.page_count < 1:
        return []
    page = doc.load_page(doc.page_count - 1)

    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height

    # Resolve region: argument → layout file → default
    if region_pct is None:
        if layout_dir and parent_id:
            region_pct = _resolve_region_from_layout(layout_dir, parent_id, canvas_name)
        else:
            print("Warning: No layout_dir/parent_id provided for canvas lookup", file=sys.stderr)

        if region_pct is None:
            region_pct = list(DEFAULT_REGION_PCT)

    # Convert percent region to PDF coordinates (points)
    rx0, ry0, rx1, ry1 = region_pct
    region_x0 = (rx0 / 100.0) * page_width
    region_y0 = (ry0 / 100.0) * page_height
    region_x2 = (rx1 / 100.0) * page_width
    region_y2 = (ry1 / 100.0) * page_height
    region_width = region_x2 - region_x0
    region_height = region_y2 - region_y0

    words_on_page = page.get_text("words")

    lines_dict = _group_words_by_line(
        words_on_page, region_x0, region_y0, region_x2, region_y2,
    )

    return _convert_lines_to_results(
        lines_dict, region_x0, region_y0, region_width, region_height,
    )


def main() -> None:
    """CLI entry point for chronicle2layout.

    Parses command-line arguments, resolves the extraction region, runs
    layout generation, and writes JSON output to a file or stdout.
    """
    p = argparse.ArgumentParser(
        description="chronicle2layout: generate layout-compatible JSON with text-based strikeout choices")
    p.add_argument("pdf", help="Path to single-page PDF")
    p.add_argument("--debug-dir", type=str, default=None,
                  help="Directory to write debug images")
    p.add_argument("--region", type=str, default=None,
                  help="Region in percent as x0,y0,x1,y1 (e.g. 0.5,50.8,40,83). If omitted, will use canvas from layout.")
    p.add_argument("--output", "-o", help="Output JSON file path. If not specified, prints to stdout.")
    p.add_argument("--layout-dir", type=str, help="Base layouts directory (e.g. 'layouts')")
    p.add_argument("--item-canvas", type=str, default="items",
                  help="Name of the canvas to extract items from (default: items)")
    p.add_argument("--checkbox-canvas", type=str, default="summary",
                  help="Name of the canvas to detect checkboxes from (default: summary)")
    p.add_argument("--id", type=str, help="ID for the layout (e.g. 'pfs2.s5-07')")
    p.add_argument("--description", type=str, help="Description of the scenario")
    p.add_argument("--parent", type=str, help="Parent layout ID (e.g. 'pfs2.season5')")
    p.add_argument("--default-chronicle", type=str, help="Default path to the blank chronicle PDF (e.g. 'modules/pf2e-pfs06-year-of-immortal-influence/assets/chronicles-1/6-06-RottenApples.pdf')")
    args = p.parse_args()

    try:
        region_pct = _parse_region_arg(args.region)
        if region_pct is False:
            return

        checkbox_region_pct = None
        if args.layout_dir and args.parent:
            try:
                base_layout_path = find_layout_file(args.layout_dir, args.parent)
                with open(base_layout_path) as f:
                    base_layout = json.load(f)
                    if region_pct is None:
                        region_pct = transform_canvas_coordinates(base_layout, args.item_canvas)
                    checkbox_region_pct = transform_canvas_coordinates(base_layout, args.checkbox_canvas)
            except Exception as e:
                print(json.dumps({"error": f"Failed to process layout file for parent '{args.parent}': {e}"}))
                return

        if region_pct is None:
            region_pct = list(DEFAULT_REGION_PCT)

        layout = generate_layout_json(
            args.pdf,
            region_pct=region_pct,
            debug_dir=args.debug_dir,
            layout_dir=args.layout_dir,
            parent_id=args.parent,
            scenario_id=args.id,
            description=args.description,
            parent=args.parent,
            checkbox_region_pct=checkbox_region_pct,
            item_canvas_name=args.item_canvas,
            checkbox_canvas_name=args.checkbox_canvas,
            default_chronicle_location=args.default_chronicle,
        )

        output = json.dumps(layout, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
        else:
            print(output)

    except Exception as e:
        print(json.dumps({"error": str(e)}))


def _parse_region_arg(region_str: Optional[str]) -> list[float] | None | bool:
    """Parse the --region CLI argument into a list of floats.

    Returns a list of four floats on success, None if not provided,
    or False if parsing failed (caller should abort).
    """
    if region_str is None:
        return None
    try:
        parts = [p.strip() for p in region_str.split(',') if p.strip() != '']
        if len(parts) != 4:
            raise ValueError('region must have four comma-separated values')
        return [float(x) for x in parts]
    except Exception as e:
        print(json.dumps({"error": f"Invalid --region value: {e}"}))
        return False


if __name__ == '__main__':
    main()
