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


def find_layout_file(layout_dir: str, layout_id: str) -> Path:
    base_path = Path(layout_dir)
    parts = layout_id.split('.')
    if len(parts) == 1:
        return base_path / parts[0] / f"{parts[0]}.json"
    search_base = base_path / parts[0]
    ident = parts[1]
    import re
    m = re.match(r'^season(\d+)([a-z])?$', ident)
    if m:
        season_num = m.group(1)
        variant = m.group(2)
        season_dir = search_base / f"s{season_num}"
        if variant:
            # Check for .generated.json first, fall back to regular
            generated = season_dir / f"Season{season_num}{variant}.generated.json"
            if generated.exists():
                return generated
            return season_dir / f"Season{season_num}{variant}.json"
        return season_dir / f"Season {season_num}.json"
    if ident.startswith('s') and '-' in ident:
        season_num = ident.split('-')[0][1:]
        return search_base / f"s{season_num}" / f"{ident}.json"
    return search_base / ident / f"{ident}.json"


def transform_canvas_coordinates(layout_json: dict, canvas_name: str):
    if "canvas" not in layout_json or canvas_name not in layout_json["canvas"]:
        raise ValueError(f"Canvas {canvas_name} not found in layout")

    def transform(name: str):
        c = layout_json["canvas"][name]
        x, y, x2, y2 = c["x"], c["y"], c["x2"], c["y2"]
        if "parent" in c:
            px, py, px2, py2 = transform(c["parent"])
            pw, ph = (px2 - px), (py2 - py)
            x = px + (x / 100.0) * pw
            y = py + (y / 100.0) * ph
            x2 = px + (x2 / 100.0) * pw
            y2 = py + (y2 / 100.0) * ph
        return [x, y, x2, y2]

    return transform(canvas_name)


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
