"""chronicle2layout

Detect checkboxes and extract text lines from a single-page PDF and output useful JSON data.
This is a renamed copy of the previous `checkbox_finder_simple.py` module.
"""
import argparse
import json
from pathlib import Path
import sys

import fitz  # PyMuPDF
import numpy as np
import cv2

import pytesseract
from pytesseract import Output


def image_checkboxes(pdf_path: str, zoom: int = 3, min_box_size_pct: float = 0.4, 
                    max_box_size_pct: float = 1.2, debug_dir: str = None, 
                    max_fill_ratio: float = 0.95, min_mean_inner: float = 140.0):
    """Detect hollow square checkboxes in a rendered PDF page using OpenCV.
    
    Returns coordinates as percentages of page dimensions.
    """
    # Load and render PDF page
    doc = fitz.open(pdf_path)
    if doc.page_count < 1:
        return []
    page = doc.load_page(0)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if img.ndim == 3 and img.shape[2] == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img

    h, w = gray.shape

    # Preprocess image
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    th = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                             cv2.THRESH_BINARY_INV, 11, 2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    results = []

    # Process each contour
    seen_positions = set()  # Track positions we've seen to deduplicate
    for cnt in contours:
        if cv2.contourArea(cnt) < 10:
            continue
            
        # Approximate the contour to a polygon
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        
        # Look for quadrilateral shapes
        if len(approx) == 4:
            x, y, bw, bh = cv2.boundingRect(approx)
            
            # Calculate size as percentage of page dimensions
            bw_pct = bw / w * 100.0
            bh_pct = bh / h * 100.0
            if not (min_box_size_pct <= bw_pct <= max_box_size_pct and 
                   min_box_size_pct <= bh_pct <= max_box_size_pct):
                continue
                
            # Check if we've seen this position before (with some tolerance)
            pos_key = f"{x//5},{y//5}"  # Group nearby positions
            if pos_key in seen_positions:
                continue
            seen_positions.add(pos_key)
                
            # Check if roughly square
            ar = float(bw) / float(bh) if bh > 0 else 0
            if ar < 0.6 or ar > 1.6:
                continue

            # Calculate fill ratio to find hollow boxes
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask, [approx], -1, 255, -1)
            filled_area = cv2.countNonZero(mask[y:y+bh, x:x+bw])
            fill_ratio = float(filled_area) / float(max(1, bw * bh))
            if fill_ratio > max_fill_ratio:
                continue

            # Convert to percent coordinates (0% = top/left of page)
            x_pct = (x / w) * 100.0
            y_pct = (y / h) * 100.0
            x2_pct = ((x + bw) / w) * 100.0
            y2_pct = ((y + bh) / h) * 100.0
            
            results.append({
                "x": round(x_pct, 3),
                "y": round(y_pct, 3),
                "x2": round(x2_pct, 3),
                "y2": round(y2_pct, 3)
            })

    # Deduplicate results that are very close together
    deduped = []
    for r in sorted(results, key=lambda x: (x['x'], x['y'])):
        if not any(abs(d['x'] - r['x']) < 0.5 and 
                  abs(d['y'] - r['y']) < 0.5 for d in deduped):
            deduped.append(r)

    # Save debug images if requested
    if debug_dir:
        try:
            outp = Path(debug_dir)
            outp.mkdir(parents=True, exist_ok=True)
            
            # Save rendered page
            if img.ndim == 3 and img.shape[2] == 3:
                rendered_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                rendered_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            # Create debug visualization
            annotated = rendered_bgr.copy()
            for r in deduped:
                # Convert percentages back to image coordinates
                x = int((r['x'] / 100.0) * w)
                y = int((r['y'] / 100.0) * h)
                x2 = int((r['x2'] / 100.0) * w)
                y2 = int((r['y2'] / 100.0) * h)
                
                # Draw detection
                cv2.rectangle(annotated, (x, y), (x2, y2), (0, 255, 0), 2)
                cx = (x + x2) // 2
                cy = (y + y2) // 2
                cv2.circle(annotated, (cx, cy), 3, (0, 0, 255), -1)
                cv2.putText(annotated, f"{r['x']:.1f},{r['y']:.1f}", 
                          (x, max(10, y-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 
                          (255, 0, 0), 1)

            cv2.imwrite(str(outp / 'annotated.png'), annotated)
            cv2.imwrite(str(outp / 'threshold.png'), th)

        except Exception as e:
            print(f"Failed to save debug images: {e}", file=sys.stderr)

    return deduped

def extract_text_lines(pdf_path: str, region_pct=None, zoom=6, debug_dir=None, layout_dir=None, layout_id=None):
    """
    Extract bounding boxes for each line of text inside a specified region.
    Handles smart quotes and periods appropriately for JSON output.

    Args:
        pdf_path (str): Path to the PDF file to process
        region_pct (list, optional): Region as [x0, y0, x1, y1] in percent coordinates
        zoom (int, optional): Zoom factor for PDF rendering. Defaults to 6.
        debug_dir (str, optional): Directory for debug output images
        layout_dir (str, optional): Directory containing layout files (e.g. 'layouts/pfs2/s5')
        layout_id (str, optional): Specific layout ID to use (e.g. 'Season 5')

    Returns:
        list: List of dicts {text, top_left_pct, bottom_right_pct} where percentages
             are relative to the cropped sub-canvas.
    """
    # Track seen text positions to avoid duplicates
    seen_positions = set()
    doc = fitz.open(pdf_path)
    if doc.page_count < 1:
        return []
    page = doc.load_page(0)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if img.ndim == 3 and img.shape[2] == 3:
        rgb = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = rgb.shape[:2]

    # If no region_pct provided, try to load from layout file
    if region_pct is None:
        try:
            # Use provided layout_dir/id or try to find a suitable default
            if layout_dir and layout_id:
                base_layout_path = Path(layout_dir) / f"{layout_id}.json"
            else:
                # Look for Season 5 layout first, then fall back to pfs2.json
                base_layout_path = Path(pdf_path).parent.parent / "s5" / "Season 5.json"
                if not base_layout_path.exists():
                    base_layout_path = Path(pdf_path).parent.parent / "pfs2.json"
                
            if base_layout_path.exists():
                with open(base_layout_path) as f:
                    base_layout = json.load(f)
                    if "canvas" in base_layout and "items" in base_layout["canvas"]:
                        def transform_coordinates(canvas_name):
                            canvas = base_layout["canvas"][canvas_name]
                            x, y = canvas["x"], canvas["y"]
                            x2, y2 = canvas["x2"], canvas["y2"]
                            if "parent" in canvas:
                                parent_coords = transform_coordinates(canvas["parent"])
                                # Transform coordinates relative to parent
                                px, py, px2, py2 = parent_coords
                                pw = px2 - px
                                ph = py2 - py
                                x = px + (x / 100.0) * pw
                                y = py + (y / 100.0) * ph
                                x2 = px + (x2 / 100.0) * pw
                                y2 = py + (y2 / 100.0) * ph
                            return [x, y, x2, y2]
                        
                        # Get absolute coordinates for items canvas
                        region_pct = transform_coordinates("items")
        except Exception as e:
            print(f"Warning: Failed to load items canvas from pfs2.json: {e}", file=sys.stderr)

        # Fall back to default if we couldn't load from layout
        if region_pct is None:
            region_pct = [0.5, 50.8, 40.0, 83.0]

    # convert percent region to full-image pixels and crop
    try:
        rx0, ry0, rx1, ry1 = region_pct
        cx0 = int((rx0 / 100.0) * w)
        cy0 = int((ry0 / 100.0) * h)
        cx1 = int((rx1 / 100.0) * w)
        cy1 = int((ry1 / 100.0) * h)
        # clamp
        cx0 = max(0, min(w - 1, cx0))
        cy0 = max(0, min(h - 1, cy0))
        cx1 = max(0, min(w - 1, cx1))
        cy1 = max(0, min(h - 1, cy1))
        if cx1 <= cx0 or cy1 <= cy0:
            return []
    except Exception:
        return []

    # Draw the crop region on the debug image
    if debug_dir:
        debug_img = rgb.copy()
        cv2.rectangle(debug_img, (cx0, cy0), (cx1, cy1), (0, 255, 0), 2)
        debug_path = Path(debug_dir) / 'ocr_region.png'
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_path), debug_img)
        # Also save just the cropped region
        cv2.imwrite(str(Path(debug_dir) / 'ocr_crop.png'), rgb[cy0:cy1, cx0:cx1])

    crop = rgb[cy0:cy1, cx0:cx1]
    ch, cw = crop.shape[:2]

    # OCR with block mode for better line detection
    data = pytesseract.image_to_data(crop, output_type=Output.DICT, config='--psm 6')
    
    words = []
    heights = []
    seen_positions = set()
    
    # Collect all words with their coordinates
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if not text:
            continue
            
        x = data['left'][i]
        y = data['top'][i]
        w = data['width'][i]
        h = data['height'][i]
        
        # Create a position key for deduplication
        pos_key = f"{x//2}:{y//2}"  # Group very close positions
        if pos_key in seen_positions:
            continue
        seen_positions.add(pos_key)
        
        words.append({'text': text, 'left': x, 'top': y, 'width': w, 'height': h})
        heights.append(h)
    
    if not words:
        return []
        
    # Sort words by vertical position first, then horizontal position
    words.sort(key=lambda w: (w['top'], w['left']))
    
    # Group into lines using improved line detection
    lines = []
    current_line = []
    last_y = None
    median_h = int(np.median(heights))
    
    for word in words:
        if last_y is None:
            current_line.append(word)
            last_y = word['top']
            continue
            
        # If this word is within the vertical threshold of any word in the current line
        if any(abs(word['top'] - w['top']) <= median_h * 0.75 for w in current_line):
            current_line.append(word)
            # Update last_y to be the average of the line
            last_y = sum(w['top'] for w in current_line) / len(current_line)
        else:
            # Start a new line
            if current_line:
                # Sort by horizontal position
                current_line.sort(key=lambda w: w['left'])
                lines.append(current_line)
            current_line = [word]
            last_y = word['top']
            
    if current_line:
        current_line.sort(key=lambda w: w['left'])
        lines.append(current_line)
    
    results = []
    for line in lines:
        text = ' '.join(w['text'] for w in line)
        if 'items' in text.lower():
            continue
            
        # Get line bounds
        x0 = min(w['left'] for w in line)
        y0 = min(w['top'] for w in line)
        x1 = max(w['left'] + w['width'] for w in line)
        y1 = max(w['top'] + w['height'] for w in line)
        
        # Convert to percentages
        x0_pct = x0 / cw * 100.0
        y0_pct = y0 / ch * 100.0
        x1_pct = x1 / cw * 100.0
        y1_pct = y1 / ch * 100.0
        
        results.append({
            'text': text,
            'top_left_pct': [round(x0_pct, 3), round(y0_pct, 3)],
            'bottom_right_pct': [round(x1_pct, 3), round(y1_pct, 3)]
        })

    return results


def generate_layout_json(pdf_path: str, region_pct=None, include_checkboxes=True, debug_dir=None, 
                    layout_dir=None, layout_id=None, scenario_id=None, description=None, parent=None):
    """Generate JSON in layout file format with text-based choices for strikeouts.
    
    Args:
        pdf_path (str): Path to the PDF file to process
        region_pct (list, optional): Region as [x0, y0, x1, y1] in percent coordinates
        include_checkboxes (bool, optional): Whether to detect checkboxes. Defaults to True.
        debug_dir (str, optional): Directory for debug output images
        layout_dir (str, optional): Directory containing layout files (e.g. 'layouts/pfs2/s5')
        layout_id (str, optional): Specific layout ID to use (e.g. 'Season 5')
        scenario_id (str, optional): ID for the layout (e.g. '5-07')
        description (str, optional): Description of the scenario
        parent (str, optional): Parent layout file (e.g. 's5')
    
    Returns:
        dict: Layout JSON configuration with detected items and checkboxes
    """
    # Create base layout structure
    layout = {}
    
    # Add metadata if provided
    if scenario_id:
        layout["id"] = scenario_id
    if description:
        layout["description"] = description
    if parent:
        layout["parent"] = parent

    # Add required sections
    layout.update({
        "parameters": {
            "Items": {
                "strikeout_item_lines": {
                    "type": "choice",
                    "description": "Item line text to be struck out",
                    "choices": [],  # Will fill with text choices
                    "example": ""
                }
            }
        },
        "presets": {
            "strikeout_item": {
                "canvas": "items",
                "color": "black",
                "linewidth": 11,
                "x": 0.5,
                "x2": 95
            }
        },
        "content": [
            {
                "type": "choice",
                "choices": "param:strikeout_item_lines",
                "content": {}
            }
        ]
    })

    if include_checkboxes:
        boxes = image_checkboxes(pdf_path, debug_dir=debug_dir)
        layout["checkboxes"] = boxes

    # Extract text lines
    lines = extract_text_lines(pdf_path, region_pct=region_pct, debug_dir=debug_dir,
                        layout_dir=layout_dir, layout_id=layout_id)
    
    # Join lines that belong to the same item by looking for Item X pattern
    items = []
    item_lines = []
    
    def clean_text(text):
        # Remove any trailing quotes, dots, or periods while preserving smart quotes in the middle
        text = text.strip()
        return text

    def is_item_start(text):
        return "Item" in text and any(str(i) in text for i in range(1, 21))
    
    for line in lines:
        if "items" in line["text"].lower() and ":" not in line["text"]:
            continue
            
        text = clean_text(line["text"])
        
        # If this is an item start and we have collected lines, save the previous item
        if is_item_start(text) and item_lines:
            y_start = item_lines[0]["top_left_pct"][1]
            y_end = item_lines[-1]["bottom_right_pct"][1]
            # Join the lines with proper text cleaning and deduplicate any repeated parts
            cleaned_text = " ".join(clean_text(l["text"]) for l in item_lines)
            # Remove any duplicated text that might occur from OCR issues
            text_parts = cleaned_text.split(" ")
            unique_parts = []
            for part in text_parts:
                if not unique_parts or part != unique_parts[-1]:
                    unique_parts.append(part)
            items.append({
                "text": " ".join(unique_parts),
                "y": y_start,
                "y2": y_end
            })
            item_lines = []
            
        # Only track non-empty lines
        if text.strip():
            item_lines.append({
                "text": text,
                "y": line["top_left_pct"][1],
                "y2": line["bottom_right_pct"][1],
                "top_left_pct": line["top_left_pct"],
                "bottom_right_pct": line["bottom_right_pct"]
            })
    
    # Don't forget to add the last item
    if item_lines:
        # For multi-line items, use first line's y and last line's y2
        y_start = item_lines[0]["top_left_pct"][1]
        y_end = item_lines[-1]["bottom_right_pct"][1]
        items.append({
            "text": " ".join(l["text"] for l in item_lines),
            "y": y_start,
            "y2": y_end
        })

    
    # Process joined items
    for item in items:
        text = item["text"]
        # Clean up OCR artifacts
        # Just use the text as-is, preserving smart quotes and other characters
        text = text.strip()
        # Add text as a choice if not already present
        if text not in layout["parameters"]["Items"]["strikeout_item_lines"]["choices"]:
            layout["parameters"]["Items"]["strikeout_item_lines"]["choices"].append(text)
        
        # Create preset for this line's position
        safe_text = text[:50].replace(" ", "_").replace(",", "").replace(".", "").replace("(", "").replace(")", "").replace("'", "").replace('"', "")
        preset_name = f"item.line.{safe_text}"
        layout["presets"][preset_name] = {
            "y": round(item["y"], 1),
            "y2": round(item["y2"], 1)
        }
        
        # Add content entry for this line
        layout["content"][0]["content"][text] = [{
            "type": "line",
            "presets": ["strikeout_item", preset_name]
        }]

    # Set example using first detected text
    if layout["parameters"]["Items"]["strikeout_item_lines"]["choices"]:
        first_text = layout["parameters"]["Items"]["strikeout_item_lines"]["choices"][0]
        layout["parameters"]["Items"]["strikeout_item_lines"]["example"] = first_text

    return layout

def main():
    p = argparse.ArgumentParser(
        description="chronicle2layout: generate layout-compatible JSON with text-based strikeout choices")
    p.add_argument("pdf", help="Path to single-page PDF")
    p.add_argument("--debug-dir", type=str, default=None,
                  help="Directory to write debug images")
    p.add_argument("--region", type=str, default=None,
                  help="Region in percent as x0,y0,x1,y1 (e.g. 0.5,50.8,40,83). If omitted, a sensible default is used.")
    p.add_argument("--skip-checkboxes", action='store_true',
                  help="If set, skip checkbox detection.")
    p.add_argument("--output", "-o", help="Output JSON file path. If not specified, prints to stdout.")
    p.add_argument("--layout-dir", type=str, help="Directory containing layout files (e.g. layouts/pfs2/s5)")
    p.add_argument("--layout-id", type=str, help="Specific layout ID to use (e.g. 'Season 5')")
    p.add_argument("--id", type=str, help="ID for the layout (e.g. '5-07')")
    p.add_argument("--description", type=str, help="Description of the scenario")
    p.add_argument("--parent", type=str, help="Parent layout file (e.g. 's5')")
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

        layout = generate_layout_json(
            args.pdf,
            region_pct=region_pct,
            include_checkboxes=not args.skip_checkboxes,
            debug_dir=args.debug_dir,
            layout_dir=args.layout_dir,
            layout_id=args.layout_id,
            scenario_id=args.id,
            description=args.description,
            parent=args.parent
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
