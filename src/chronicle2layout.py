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
                    max_fill_ratio: float = 0.96, min_mean_inner: float = 140.0,
                    region_pct: list = None, min_box_size_px: int = 10, max_box_size_px: int = 50):
    """Detect hollow square checkboxes in a rendered PDF page using OpenCV.
    
    Args:
        region_pct: Optional [x0, y0, x1, y1] in percent to crop before detection.
                   Coordinates will be returned relative to this cropped region.
        min_box_size_px: Minimum checkbox size in pixels (used when region_pct is set)
        max_box_size_px: Maximum checkbox size in pixels (used when region_pct is set)
    
    Returns coordinates as percentages of canvas dimensions (or page if no region).
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

    full_h, full_w = gray.shape
    
    # Save full page for reference if debug enabled
    if debug_dir and region_pct:
        outp = Path(debug_dir)
        outp.mkdir(parents=True, exist_ok=True)
        # Save full grayscale image
        cv2.imwrite(str(outp / 'checkbox_full_page.png'), gray)
    
    # Crop to region if specified
    if region_pct:
        x0_pix = int(region_pct[0] * full_w / 100.0)
        y0_pix = int(region_pct[1] * full_h / 100.0)
        x1_pix = int(region_pct[2] * full_w / 100.0)
        y1_pix = int(region_pct[3] * full_h / 100.0)
        
        if debug_dir:
            print(f"DEBUG: Full image size: {full_w}x{full_h}", file=sys.stderr)
            print(f"DEBUG: Region percent: {region_pct}", file=sys.stderr)
            print(f"DEBUG: Crop pixels: x={x0_pix}:{x1_pix}, y={y0_pix}:{y1_pix}", file=sys.stderr)
            
            # Draw rectangle on full page to show crop region
            full_with_rect = cv2.cvtColor(gray.copy(), cv2.COLOR_GRAY2BGR)
            cv2.rectangle(full_with_rect, (x0_pix, y0_pix), (x1_pix, y1_pix), (0, 255, 0), 3)
            cv2.imwrite(str(outp / 'checkbox_crop_region.png'), full_with_rect)
        
        gray = gray[y0_pix:y1_pix, x0_pix:x1_pix]
        
        if debug_dir:
            print(f"DEBUG: Cropped image size: {gray.shape[1]}x{gray.shape[0]}", file=sys.stderr)
            # Save the cropped region
            cv2.imwrite(str(outp / 'checkbox_cropped.png'), gray)
    
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
    
    if debug_dir:
        print(f"DEBUG: Found {len(contours)} total contours", file=sys.stderr)

    # Process each contour
    seen_positions = set()  # Track positions we've seen to deduplicate
    contour_count = 0
    quad_count = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 10:
            continue
        
        contour_count += 1
            
        # Approximate the contour to a polygon
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        
        if debug_dir and contour_count <= 20:
            print(f"DEBUG: Contour {contour_count}: area={area:.1f}, perimeter={peri:.1f}, approx_sides={len(approx)}", file=sys.stderr)
        
        # Look for quadrilateral shapes
        if len(approx) == 4:
            quad_count += 1
            x, y, bw, bh = cv2.boundingRect(approx)
            
            # Calculate size as percentage of page dimensions
            bw_pct = bw / w * 100.0
            bh_pct = bh / h * 100.0
            
            # Use pixel-based size check if we're working with a cropped region, otherwise use percentages
            if region_pct:
                size_ok = (min_box_size_px <= bw <= max_box_size_px and 
                          min_box_size_px <= bh <= max_box_size_px)
                if debug_dir and quad_count <= 20:
                    print(f"DEBUG: Quad {quad_count}: size={bw}x{bh}px ({bw_pct:.2f}%x{bh_pct:.2f}%), at ({x},{y}), size_ok={size_ok}", file=sys.stderr)
            else:
                size_ok = (min_box_size_pct <= bw_pct <= max_box_size_pct and 
                          min_box_size_pct <= bh_pct <= max_box_size_pct)
                if debug_dir and quad_count <= 20:
                    print(f"DEBUG: Quad {quad_count}: size={bw_pct:.2f}%x{bh_pct:.2f}%, at ({x},{y}), size_ok={size_ok}", file=sys.stderr)
            
            if not size_ok:
                if debug_dir and quad_count <= 20:
                    print(f"  -> Filtered: size check failed", file=sys.stderr)
                continue
                
            # Check if we've seen this position before (with some tolerance)
            pos_key = f"{x//5},{y//5}"  # Group nearby positions
            if pos_key in seen_positions:
                if debug_dir and quad_count <= 20:
                    print(f"  -> Filtered: duplicate position", file=sys.stderr)
                continue
            seen_positions.add(pos_key)
                
            # Check if roughly square
            ar = float(bw) / float(bh) if bh > 0 else 0
            if ar < 0.6 or ar > 1.6:
                if debug_dir and quad_count <= 20:
                    print(f"  -> Filtered: aspect ratio {ar:.2f}", file=sys.stderr)
                continue

            # Calculate fill ratio to find hollow boxes
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask, [approx], -1, 255, -1)
            filled_area = cv2.countNonZero(mask[y:y+bh, x:x+bw])
            fill_ratio = float(filled_area) / float(max(1, bw * bh))
            if fill_ratio > max_fill_ratio:
                if debug_dir and quad_count <= 20:
                    print(f"  -> Filtered: fill ratio {fill_ratio:.2f}", file=sys.stderr)
                continue

            if debug_dir and quad_count <= 20:
                print(f"  -> PASSED all filters", file=sys.stderr)

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

    if debug_dir:
        print(f"DEBUG: Found {len(results)} raw checkboxes, {len(deduped)} after dedup", file=sys.stderr)
        for i, r in enumerate(deduped, 1):
            print(f"DEBUG: Checkbox {i}: x={r['x']:.3f}, y={r['y']:.3f}, x2={r['x2']:.3f}, y2={r['y2']:.3f}", file=sys.stderr)

    # Save debug images if requested
    if debug_dir:
        try:
            outp = Path(debug_dir)
            outp.mkdir(parents=True, exist_ok=True)
            
            # Save the cropped image that was processed
            if region_pct:
                # We're working with the cropped gray image
                cropped_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            else:
                # Save rendered page
                if img.ndim == 3 and img.shape[2] == 3:
                    cropped_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                else:
                    cropped_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            # Create debug visualization on the cropped image
            annotated = cropped_bgr.copy()
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

            cv2.imwrite(str(outp / 'checkbox_annotated.png'), annotated)
            cv2.imwrite(str(outp / 'checkbox_threshold.png'), th)
            cv2.imwrite(str(outp / 'checkbox_closed.png'), closed)

        except Exception as e:
            print(f"Failed to save debug images: {e}", file=sys.stderr)

    return deduped

def find_layout_file(layout_dir, layout_id):
    """Find the layout file for a given layout ID by searching the layout directory.
    
    The layout ID follows patterns like:
    - pfs2 -> layouts/pfs2/pfs2.json
    - pfs2.season5 -> layouts/pfs2/s5/Season 5.json
    - pfs2.s5-07 -> layouts/pfs2/s5/5-07-SewerDragonCrisis.json
    
    Args:
        layout_dir (str): Base layouts directory (e.g., 'layouts')
        layout_id (str): Layout ID to find (e.g., 'pfs2.season5')
        
    Returns:
        Path: Path to the layout file
        
    Raises:
        ValueError: If the layout file cannot be found
    """
    base_path = Path(layout_dir)
    
    # Split the layout ID by dots
    parts = layout_id.split('.')
    
    if len(parts) == 1:
        # Simple case: pfs2 -> pfs2/pfs2.json
        layout_file = base_path / parts[0] / f"{parts[0]}.json"
    else:
        # Complex case: need to search for the file
        # Start with the first part (e.g., pfs2)
        search_base = base_path / parts[0]
        
        # For patterns like pfs2.season5, look for Season 5.json in subdirectories
        if parts[1].startswith('season'):
            season_num = parts[1].replace('season', '')
            # Look in s{N} subdirectory for Season {N}.json
            layout_file = search_base / f"s{season_num}" / f"Season {season_num}.json"
        elif parts[1].startswith('s') and '-' in parts[1]:
            # For scenario IDs like s5-07
            season_num = parts[1].split('-')[0][1:]  # Extract '5' from 's5'
            # This would be a scenario file, but we're looking for parent layouts
            layout_file = search_base / f"s{season_num}" / f"{parts[1]}.json"
        else:
            # Generic fallback
            layout_file = search_base / parts[1] / f"{parts[1]}.json"
    
    if not layout_file.exists():
        raise ValueError(f"Layout file not found: {layout_file}")
    
    return layout_file

def transform_canvas_coordinates(layout_json, canvas_name):
    """Transform canvas coordinates into absolute page coordinates by following the parent chain.
    
    Args:
        layout_json (dict): The loaded layout JSON object
        canvas_name (str): Name of the canvas to transform
        
    Returns:
        list: [x, y, x2, y2] coordinates in absolute page percent
    """
    if "canvas" not in layout_json or canvas_name not in layout_json["canvas"]:
        raise ValueError(f"Canvas {canvas_name} not found in layout")
        
    def transform_coordinates(canvas_name):
        canvas = layout_json["canvas"][canvas_name]
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
        
    return transform_coordinates(canvas_name)

def extract_text_lines(pdf_path: str, region_pct=None, zoom=6, debug_dir=None, 
                      layout_dir=None, parent_id=None, canvas_name="items"):
    """
    Extract bounding boxes for each line of text inside a specified region.
    Handles smart quotes and periods appropriately for JSON output.

    Args:
        pdf_path (str): Path to the PDF file to process
        region_pct (list, optional): Region as [x0, y0, x1, y1] in percent coordinates
        zoom (int, optional): Zoom factor for PDF rendering. Defaults to 6.
        debug_dir (str, optional): Directory for debug output images
        layout_dir (str, optional): Base layouts directory (e.g. 'layouts')
        parent_id (str, optional): Parent layout ID (e.g. 'pfs2.season5')
        canvas_name (str, optional): Name of the canvas to extract text from. Defaults to "items"

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
            # Use provided layout_dir and parent_id to find the layout file
            if layout_dir and parent_id:
                base_layout_path = find_layout_file(layout_dir, parent_id)
                
                with open(base_layout_path) as f:
                    base_layout = json.load(f)
                    # Get absolute coordinates for the specified canvas
                    region_pct = transform_canvas_coordinates(base_layout, canvas_name)
            else:
                print("Warning: No layout_dir/parent_id provided for canvas lookup", file=sys.stderr)

        except Exception as e:
            print(f"Warning: Failed to load layout file: {e}", file=sys.stderr)

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


def generate_layout_json(pdf_path: str, region_pct=None, debug_dir=None, 
                    layout_dir=None, parent_id=None, scenario_id=None, description=None, parent=None,
                    checkbox_region_pct=None, item_canvas_name="items", checkbox_canvas_name="summary"):
    """Generate JSON in layout file format with text-based choices for strikeouts.
    
    Args:
        pdf_path (str): Path to the PDF file to process
        region_pct (list, optional): Region as [x0, y0, x1, y1] in percent coordinates for items
        debug_dir (str, optional): Directory for debug output images
        layout_dir (str, optional): Base layouts directory (e.g. 'layouts')
        parent_id (str, optional): Parent layout ID for finding canvas (e.g. 'pfs2.season5')
        scenario_id (str, optional): ID for the layout (e.g. '5-07')
        description (str, optional): Description of the scenario
        parent (str, optional): Parent layout ID to write to output JSON (e.g. 'pfs2.season5')
        checkbox_region_pct (list, optional): Region as [x0, y0, x1, y1] for checkbox detection
        item_canvas_name (str, optional): Name of the canvas for items (default: "items")
        checkbox_canvas_name (str, optional): Name of the canvas for checkboxes (default: "summary")
    
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

    # Detect checkboxes first
    boxes = image_checkboxes(pdf_path, debug_dir=debug_dir, region_pct=checkbox_region_pct)
    
    # Add required sections
    layout["parameters"] = {
        "Items": {
            "strikeout_item_lines": {
                "type": "choice",
                "description": "Item line text to be struck out",
                "choices": [],  # Will fill with text choices
                "example": ""
            }
        }
    }
    
    # Add checkbox parameters if checkboxes were detected
    if boxes:
        layout["parameters"]["Checkboxes"] = {
            "summary_checkbox": {
                "type": "choice",
                "description": "Checkboxes in the adventure summary that should be selected",
                "choices": list(range(1, len(boxes) + 1)),
                "example": ",".join(str(i) for i in range(1, len(boxes) + 1))
            }
        }
    
    # Initialize presets
    layout["presets"] = {
        "strikeout_item": {
            "canvas": item_canvas_name,
            "color": "black",
            "x": 0.5,
            "x2": 95
        }
    }
    
    # Add checkbox presets if checkboxes were detected
    if boxes:
        layout["presets"]["checkbox"] = {
            "canvas": checkbox_canvas_name,
            "color": "black",
            "size": 1
        }
        for i, box in enumerate(boxes, 1):
            layout["presets"][f"checkbox.{i}"] = {
                "x": box["x"],
                "y": box["y"],
                "x2": box["x2"],
                "y2": box["y2"]
            }
    
    # Initialize content array
    layout["content"] = [
        {
            "type": "choice",
            "choices": "param:strikeout_item_lines",
            "content": {}
        }
    ]

    # Extract text lines
    lines = extract_text_lines(pdf_path, region_pct=region_pct, debug_dir=debug_dir,
                        layout_dir=layout_dir, parent_id=parent_id, canvas_name=item_canvas_name)
    
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
            # Use the first line's y (top) and the last line's y2 (bottom)
            y_start = min(l["top_left_pct"][1] for l in item_lines)
            y_end = max(l["bottom_right_pct"][1] for l in item_lines)
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
        # For multi-line items, find the topmost y and bottommost y2
        y_start = min(l["top_left_pct"][1] for l in item_lines)
        y_end = max(l["bottom_right_pct"][1] for l in item_lines)
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
        
        # Add content entry for this line - use strikeout to fill the entire bounding box
        layout["content"][0]["content"][text] = [{
            "type": "strikeout",
            "presets": ["strikeout_item", preset_name]
        }]

    # Set example using first detected text
    if layout["parameters"]["Items"]["strikeout_item_lines"]["choices"]:
        first_text = layout["parameters"]["Items"]["strikeout_item_lines"]["choices"][0]
        layout["parameters"]["Items"]["strikeout_item_lines"]["example"] = first_text

    # Add checkbox content if checkboxes were detected
    if boxes:
        checkbox_content = {
            "type": "choice",
            "choices": "param:summary_checkbox",
            "content": {}
        }
        for i in range(1, len(boxes) + 1):
            checkbox_content["content"][str(i)] = [{
                "type": "checkbox",
                "presets": ["checkbox", f"checkbox.{i}"]
            }]
        layout["content"].append(checkbox_content)

    return layout

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
            checkbox_canvas_name=args.checkbox_canvas
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
