"""chronicle2layout

Detect checkboxes and extract text lines from a single-page PDF and output useful JSON data.
This is a renamed copy of the previous `checkbox_finder_simple.py` module.
"""
import argparse
import json
from pathlib import Path
import sys

import fitz  # PyMuPDF

from shared_utils import find_layout_file, transform_canvas_coordinates
from layout_generator import generate_layout_json


def extract_text_lines(pdf_path: str, region_pct=None, zoom=6, debug_dir=None, 
                      layout_dir=None, parent_id=None, canvas_name="items"):
    """Extract text lines from a PDF region using PyMuPDF text extraction.
    
    Args:
        pdf_path: Path to the PDF file
        region_pct: Optional [x0, y0, x1, y1] in percent to extract from
        zoom: Not used, kept for API compatibility
        debug_dir: Optional debug output directory
        layout_dir: Base layouts directory
        parent_id: Parent layout ID for finding canvas
        canvas_name: Name of the canvas to extract from
        
    Returns:
        List of dicts with 'text', 'top_left_pct', 'bottom_right_pct'
    """
    doc = fitz.open(pdf_path)
    if doc.page_count < 1:
        return []
    page = doc.load_page(doc.page_count - 1)
    
    # Get page dimensions
    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height

    # If no region_pct provided, try to load from layout file
    if region_pct is None:
        try:
            if layout_dir and parent_id:
                base_layout_path = find_layout_file(layout_dir, parent_id)
                with open(base_layout_path) as f:
                    base_layout = json.load(f)
                    region_pct = transform_canvas_coordinates(base_layout, canvas_name)
            else:
                print("Warning: No layout_dir/parent_id provided for canvas lookup", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Failed to load layout file: {e}", file=sys.stderr)

        # Fall back to default if we couldn't load from layout
        if region_pct is None:
            region_pct = [0.5, 50.8, 40.0, 83.0]

    # Convert percent region to PDF coordinates (points) — use canvas exactly
    rx0, ry0, rx1, ry1 = region_pct
    region_x0 = (rx0 / 100.0) * page_width
    region_y0 = (ry0 / 100.0) * page_height
    region_x2 = (rx1 / 100.0) * page_width
    region_y2 = (ry1 / 100.0) * page_height
    region_width = region_x2 - region_x0
    region_height = region_y2 - region_y0
    
    # Extract all text with word-level positions
    words_on_page = page.get_text("words")
    
    # Filter words to region and group by y-coordinate (not line_no, which is unreliable)
    # We'll group words that have similar y0 values (within a small tolerance)
    y_tolerance = 2.0  # pixels
    lines_dict = {}  # quantized_y -> list of words
    
    for word_data in words_on_page:
        x0, y0, x1, y1, text, block_no, line_no, word_no = word_data
        
        # Check if word is strictly within our region (no extra margin)
        if (x0 >= region_x0 and x1 <= region_x2 and 
            y0 >= region_y0 and y1 <= region_y2):
            
            # Find existing line with similar y0, or create new one
            quantized_y = None
            for existing_y in lines_dict.keys():
                if abs(y0 - existing_y) <= y_tolerance:
                    quantized_y = existing_y
                    break
            
            if quantized_y is None:
                quantized_y = y0
                lines_dict[quantized_y] = []
            
            lines_dict[quantized_y].append({
                'text': text,
                'x0': x0,
                'y0': y0,
                'x1': x1,
                'y1': y1
            })
    
    # Convert grouped lines to the expected format
    results = []
    for y_coord in sorted(lines_dict.keys()):
        words = lines_dict[y_coord]
        if not words:
            continue
            
        # Sort words by x position
        words.sort(key=lambda w: w['x0'])
        
        # Join text
        text = ' '.join(w['text'] for w in words)
        
        # Skip lines that are just "Items:" or similar headers
        if text.lower().strip() in ['items', 'items:']:
            continue
        
        # Get line bounds
        x0 = min(w['x0'] for w in words)
        y0 = min(w['y0'] for w in words)
        x1 = max(w['x1'] for w in words)
        y1 = max(w['y1'] for w in words)
        
        # Convert to percentages relative to the region
        x0_pct = ((x0 - region_x0) / region_width) * 100.0
        y0_pct = ((y0 - region_y0) / region_height) * 100.0
        x1_pct = ((x1 - region_x0) / region_width) * 100.0
        y1_pct = ((y1 - region_y0) / region_height) * 100.0
        
        results.append({
            'text': text,
            'top_left_pct': [round(x0_pct, 3), round(y0_pct, 3)],
            'bottom_right_pct': [round(x1_pct, 3), round(y1_pct, 3)]
        })

    return results


def main():
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
        # Parse region CLI arg if provided
        region_pct = None
        if args.region:
            try:
                parts = [p.strip() for p in args.region.split(',') if p.strip() != '']
                if len(parts) != 4:
                    raise ValueError('region must have four comma-separated values')
                region_pct = [float(x) for x in parts]
            except Exception as e:
                print(json.dumps({"error": f"Invalid --region value: {e}"}))
                return

        # Load the layout file first to get canvas coordinates if needed
        checkbox_region_pct = None
        if args.layout_dir and args.parent:
            try:
                base_layout_path = find_layout_file(args.layout_dir, args.parent)
                with open(base_layout_path) as f:
                    base_layout = json.load(f)
                    # Get absolute coordinates for the specified canvas
                    if region_pct is None:
                        region_pct = transform_canvas_coordinates(base_layout, args.item_canvas)
                    # Get absolute coordinates for the checkbox canvas
                    checkbox_region_pct = transform_canvas_coordinates(base_layout, args.checkbox_canvas)
            except Exception as e:
                print(json.dumps({"error": f"Failed to process layout file for parent '{args.parent}': {e}"}))
                return

        # If no region specified and no canvas found, use default
        if region_pct is None:
            region_pct = [0.5, 50.8, 40.0, 83.0]

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
            default_chronicle_location=args.default_chronicle
        )
        
        output = json.dumps(layout, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
        else:
            print(output)
            
    except Exception as e:
        print(json.dumps({"error": str(e)}))


if __name__ == '__main__':
    main()
