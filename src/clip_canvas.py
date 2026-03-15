#!/usr/bin/env python3
"""
Clip a canvas region from a PDF based on a layout parent and canvas name.
Resolves variant season parent files (e.g., Season4a.json) and applies parent
canvas transforms to produce absolute page coordinates.

Usage:
  python clip_canvas.py \
    --pdf /path/to/chronicle.pdf \
    --layout-dir /Users/stephen/git/HelloFoundry/pfs-chronicle-generator/layouts \
    --parent pfs2.season4a \
    --canvas items \
    --output /path/to/output.png
"""
import argparse
import json
from pathlib import Path

import fitz

from shared_utils import find_layout_file, transform_canvas_coordinates


def main():
    ap = argparse.ArgumentParser(description="Clip a canvas region from a PDF using layout coordinates")
    ap.add_argument('--pdf', required=True, help='Path to the PDF file')
    ap.add_argument('--layout-dir', required=True, help='Base layouts directory')
    ap.add_argument('--parent', required=True, help='Parent layout ID (e.g., pfs2.season4a)')
    ap.add_argument('--canvas', default='items', help='Canvas name (default: items)')
    ap.add_argument('--output', required=True, help='Output PNG path')
    args = ap.parse_args()

    layout_path = find_layout_file(args.layout_dir, args.parent)
    if not layout_path.exists():
        raise SystemExit(f"Layout file not found: {layout_path}")

    with open(layout_path) as f:
        layout = json.load(f)

    # Absolute page percent coordinates
    pct = transform_canvas_coordinates(layout, args.canvas)

    # Open PDF (last page)
    doc = fitz.open(args.pdf)
    if doc.page_count < 1:
        raise SystemExit("PDF has no pages")
    page = doc.load_page(doc.page_count - 1)

    # Convert to points
    rect_page = page.rect
    x0 = rect_page.x0 + (pct[0] / 100.0) * rect_page.width
    y0 = rect_page.y0 + (pct[1] / 100.0) * rect_page.height
    x1 = rect_page.x0 + (pct[2] / 100.0) * rect_page.width
    y1 = rect_page.y0 + (pct[3] / 100.0) * rect_page.height

    clip_rect = fitz.Rect(x0, y0, x1, y1)

    # Render the clipped region
    pix = page.get_pixmap(clip=clip_rect, alpha=False)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))
    print(f"Wrote {out_path} (size: {pix.width}x{pix.height})")


if __name__ == '__main__':
    main()
