"""Clip detected canvas regions from a chronicle PDF and save as PNGs.

Usage:
    python clip_canvases.py <pdf_path> [output_dir]

If output_dir is omitted, clips are saved to debug_clips/<pdf_stem>/.
"""

import sys
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

from season_layout_generator.image_detection import extract_image_regions
from season_layout_generator.region_merge import merge_regions
from season_layout_generator.text_detection import extract_text_regions

SUB_REGIONS = [
    "player_info",
    "summary",
    "rewards",
    "items",
    "notes",
    "boons",
    "reputation",
    "session_info",
]


def clip_canvases(pdf_path: str, output_dir: str | None = None) -> None:
    """Run detection on a chronicle PDF and save each canvas as a PNG."""
    pdf = Path(pdf_path)
    if not pdf.exists():
        print(f"Error: {pdf} not found", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(output_dir) if output_dir else Path("debug_clips") / pdf.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf)
    page = doc[0]

    text_regions = extract_text_regions(page)
    image_regions = extract_image_regions(page)
    merged = merge_regions(
        text_regions, image_regions, page.rect.width, page.rect.height
    )

    pix = page.get_pixmap(dpi=150)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )
    full_img = Image.fromarray(img_array)
    full_img.save(out_dir / "full_page.png")
    print(f"full_page: {full_img.size[0]}x{full_img.size[1]}px")

    main_coords = merged.main
    if not main_coords:
        print("No main canvas detected", file=sys.stderr)
        doc.close()
        sys.exit(1)

    pw, ph = full_img.size
    main_img = full_img.crop((
        int(main_coords.x / 100 * pw),
        int(main_coords.y / 100 * ph),
        int(main_coords.x2 / 100 * pw),
        int(main_coords.y2 / 100 * ph),
    ))
    main_img.save(out_dir / "main.png")
    print(f"main: {main_img.size[0]}x{main_img.size[1]}px")

    mw, mh = main_img.size
    for field in SUB_REGIONS:
        coords = getattr(merged, field)
        if coords is None:
            print(f"{field}: None (skipped)")
            continue
        clip = main_img.crop((
            int(coords.x / 100 * mw),
            int(coords.y / 100 * mh),
            int(coords.x2 / 100 * mw),
            int(coords.y2 / 100 * mh),
        ))
        clip.save(out_dir / f"{field}.png")
        print(f"{field}: {clip.size[0]}x{clip.size[1]}px")

    doc.close()
    print(f"\nAll clips saved to {out_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <pdf_path> [output_dir]")
        sys.exit(1)
    clip_canvases(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
