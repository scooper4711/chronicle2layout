"""Clip canvas regions from a chronicle PDF using a layout JSON.

Usage:
    python clip_canvases.py <layout.json> <chronicle.pdf> [output_dir]

If output_dir is omitted, clips are saved to debug_clips/<pdf_stem>/.
Reads the layout's canvas section and clips each region from the PDF,
resolving parent-relative coordinates to absolute page coordinates.
"""

import json
import sys
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

RENDER_DPI = 150


def resolve_absolute_coords(
    canvas: dict, all_canvases: dict,
) -> tuple[float, float, float, float]:
    """Resolve a canvas's parent-relative coords to absolute page coords."""
    x, y, x2, y2 = canvas["x"], canvas["y"], canvas["x2"], canvas["y2"]
    parent_name = canvas.get("parent")
    if parent_name is None:
        return x, y, x2, y2

    parent = all_canvases[parent_name]
    px, py, px2, py2 = resolve_absolute_coords(parent, all_canvases)
    pw = px2 - px
    ph = py2 - py
    return (
        px + x / 100 * pw,
        py + y / 100 * ph,
        px + x2 / 100 * pw,
        py + y2 / 100 * ph,
    )


def load_full_canvas_chain(layout_path: Path) -> dict:
    """Load a layout and all its parents, merging canvas sections."""
    with open(layout_path, encoding="utf-8") as f:
        layout = json.load(f)

    all_canvases = dict(layout.get("canvas", {}))
    parent_id = layout.get("parent")
    layout_dir = layout_path.parent

    while parent_id is not None:
        parent_path = find_layout_by_id(layout_dir, parent_id)
        if parent_path is None:
            break
        with open(parent_path, encoding="utf-8") as f:
            parent_layout = json.load(f)
        for name, coords in parent_layout.get("canvas", {}).items():
            if name not in all_canvases:
                all_canvases[name] = coords
        parent_id = parent_layout.get("parent")

    return all_canvases


def find_layout_by_id(search_dir: Path, layout_id: str) -> Path | None:
    """Find a layout JSON file by its id, searching recursively."""
    for json_path in search_dir.rglob("*.json"):
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("id") == layout_id:
                return json_path
        except (json.JSONDecodeError, OSError):
            continue
    return None


def clip_canvases(layout_path: str, pdf_path: str, output_dir: str | None = None) -> None:
    """Clip each canvas region from a chronicle PDF and save as PNG."""
    layout_file = Path(layout_path)
    pdf_file = Path(pdf_path)

    if not layout_file.exists():
        print(f"Error: layout not found: {layout_file}", file=sys.stderr)
        sys.exit(1)
    if not pdf_file.exists():
        print(f"Error: PDF not found: {pdf_file}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(output_dir) if output_dir else Path("debug_clips") / pdf_file.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    all_canvases = load_full_canvas_chain(layout_file)

    doc = fitz.open(str(pdf_file))
    page = doc[-1]
    pix = page.get_pixmap(dpi=RENDER_DPI)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n,
    )
    if pix.n == 4:
        img_array = img_array[:, :, :3]
    full_img = Image.fromarray(img_array)
    full_img.save(out_dir / "full_page.png")
    print(f"full_page: {full_img.size[0]}x{full_img.size[1]}px")
    doc.close()

    pw, ph = full_img.size
    for name, canvas in all_canvases.items():
        ax, ay, ax2, ay2 = resolve_absolute_coords(canvas, all_canvases)
        crop_box = (
            int(ax / 100 * pw),
            int(ay / 100 * ph),
            int(ax2 / 100 * pw),
            int(ay2 / 100 * ph),
        )
        clip = full_img.crop(crop_box)
        clip.save(out_dir / f"{name}.png")
        print(f"{name}: {clip.size[0]}x{clip.size[1]}px")

    print(f"\nAll clips saved to {out_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <layout.json> <chronicle.pdf> [output_dir]")
        sys.exit(1)
    clip_canvases(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3] if len(sys.argv) > 3 else None,
    )
