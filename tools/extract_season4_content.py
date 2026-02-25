#!/usr/bin/env python3
"""Extract content field positions from Season 4 chronicle PDFs.

This tool detects the bounding boxes for text input fields by finding
horizontal lines that serve as field boundaries, then calculates the
precise coordinates for content placement.

Usage:
    python extract_season4_content.py 4-03
"""
import fitz
from PIL import Image
import numpy as np
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[2]
PDF_DIR = BASE / "modules" / "pfs-chronicle-generator" / "assets" / "chronicles-4"
DEBUG_BASE = BASE / "chronicle2layout" / "debug" / "season4"

SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "4-03"
PDF_NAME = f"{SCENARIO}-*.pdf"

# Find the actual PDF file
import glob
pdf_files = list(PDF_DIR.glob(PDF_NAME))
if not pdf_files:
    print(f"No PDF found matching {PDF_NAME} in {PDF_DIR}")
    sys.exit(1)
PDF_PATH = pdf_files[0]
DEBUG_DIR = DEBUG_BASE / SCENARIO
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

ZOOM = 2


def render_page_to_image(pdf_path, zoom=2):
    doc = fitz.open(str(pdf_path))
    page = doc.load_page(doc.page_count - 1)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return page, img


def find_horizontal_lines(img, threshold=60, min_width_fraction=0.15):
    """Find horizontal lines (like field boundaries)."""
    arr = np.array(img.convert('L'))
    h, w = arr.shape
    row_dark = np.mean(arr < threshold, axis=1)
    
    lines = []
    for y in range(h):
        if row_dark[y] > min_width_fraction:
            lines.append(y)
    
    # Group consecutive lines
    groups = []
    if lines:
        cur = [lines[0]]
        for y in lines[1:]:
            if y == cur[-1] + 1:
                cur.append(y)
            else:
                groups.append((cur[0], cur[-1]))
                cur = [y]
        groups.append((cur[0], cur[-1]))
    
    return groups


def find_vertical_lines(img, threshold=60, min_height_fraction=0.02):
    """Find vertical lines."""
    arr = np.array(img.convert('L'))
    h, w = arr.shape
    col_dark = np.mean(arr < threshold, axis=0)
    
    lines = []
    for x in range(w):
        if col_dark[x] > min_height_fraction:
            lines.append(x)
    
    # Group consecutive lines
    groups = []
    if lines:
        cur = [lines[0]]
        for x in lines[1:]:
            if x == cur[-1] + 1:
                cur.append(x)
            else:
                groups.append((cur[0], cur[-1]))
                cur = [x]
        groups.append((cur[0], cur[-1]))
    
    return groups


def find_grey_boxes(img, grey_min=200, grey_max=240, min_width=50, min_height=20):
    """Find light grey filled rectangles (form fields).
    Returns list of (x0, y0, x1, y1) tuples."""
    arr = np.array(img.convert('L'))
    h, w = arr.shape
    
    # Find horizontal spans of grey pixels
    boxes = []
    for y in range(h):
        in_grey = False
        x_start = 0
        for x in range(w):
            is_grey = grey_min <= arr[y, x] <= grey_max
            if is_grey and not in_grey:
                x_start = x
                in_grey = True
            elif not is_grey and in_grey:
                # End of grey span
                if x - x_start >= min_width:
                    # Check if this span extends vertically to form a box
                    box_height = 1
                    for y2 in range(y + 1, min(y + 100, h)):
                        # Check if this row also has grey in same x range
                        grey_count = np.sum((arr[y2, x_start:x] >= grey_min) & (arr[y2, x_start:x] <= grey_max))
                        if grey_count / (x - x_start) < 0.7:
                            break
                        box_height += 1
                    
                    if box_height >= min_height:
                        # Check if we already have a box at this location
                        is_duplicate = False
                        for bx0, by0, bx1, by1 in boxes:
                            if abs(x_start - bx0) < 5 and abs(y - by0) < 5:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            boxes.append((x_start, y, x, y + box_height))
                in_grey = False
    
    return boxes


def words_positions(page, zoom=2):
    words = page.get_text("words")
    scaled = []
    for w in words:
        x0, y0, x1, y1, text, _, _, _ = w
        scaled.append((text, int(x0 * zoom), int(y0 * zoom), int(x1 * zoom), int(y1 * zoom)))
    return scaled


def find_label(words, label_text):
    """Find a label and return its position."""
    for text, x0, y0, x1, y1 in words:
        if label_text.lower() in text.lower():
            return (text, x0, y0, x1, y1)
    return None


def main():
    page, img = render_page_to_image(PDF_PATH, zoom=ZOOM)
    words = words_positions(page, zoom=ZOOM)
    
    w, h = img.width, img.height
    
    # Find all horizontal and vertical lines
    h_lines = find_horizontal_lines(img)
    v_lines = find_vertical_lines(img)
    
    print(f"Found {len(h_lines)} horizontal line groups")
    print(f"Found {len(v_lines)} vertical line groups")
    
    # Debug: print all vertical lines
    print(f"\nAll vertical lines:")
    for x0, x1 in v_lines:
        print(f"  x={x0}-{x1}")
    
    # Find the "Character" label to locate the character name field
    char_label = find_label(words, "Character")
    if not char_label:
        print("Warning: Could not find 'Character' label")
        return
    
    print(f"\nCharacter label: '{char_label[0]}' at ({char_label[1]}, {char_label[2]})")
    
    # Find the thin line above the character name field
    # This should be the first horizontal line above the Character label
    char_y = char_label[2]
    
    # Find horizontal lines near the character label
    candidate_lines = []
    for y0, y1 in h_lines:
        # Look for lines within ±100 pixels of the character label (expanded range)
        if y0 < char_y < y1 + 100:
            candidate_lines.append((y0, y1, char_y - y1))
    
    # Sort by distance (we want the line just above the label)
    candidate_lines.sort(key=lambda x: abs(x[2]))
    
    print(f"\nCandidate lines near Character label:")
    for y0, y1, dist in candidate_lines[:5]:
        print(f"  Line at y={y0}-{y1}, distance from label={dist}")
    
    # The field boundary line is ABOVE the label (field bottom)
    if candidate_lines:
        # Take the first line that's above the label (closest one)
        char_field_bottom = None
        for y0, y1, dist in candidate_lines:
            if y1 < char_y:  # line is above the label
                char_field_bottom = y1
                break
        
        if not char_field_bottom:
            print("Could not find character field bottom line")
            return
            
        print(f"\nCharacter field bottom line: y={char_field_bottom}")
        
        # Find the line above that (the top boundary)
        char_field_top = None
        for y0, y1 in h_lines:
            if y1 < char_field_bottom - 20:  # at least 20px above the bottom line
                char_field_top = y1
        
        if not char_field_top:
            print("Could not find character field top line")
            return
            
        print(f"Character field top line: y={char_field_top}")
        
        # Character name field bounds
        char_field_y0 = char_field_top + 2
        char_field_y1 = char_field_bottom - 2
        
        # Find vertical boundaries for the character name field
        # Look for vertical lines in the left portion of the page
        left_margin = None
        for x0, x1 in v_lines:
            if x0 < w * 0.1:  # leftmost 10%
                left_margin = x1
                break
        
        # Find the vertical divider between char name and society ID
        # This should be around 60-70% of the page width
        # First try to find an actual vertical line
        char_right = None
        for x0, x1 in v_lines:
            if 0.55 * w < x0 < 0.75 * w and x1 - x0 < 50:  # narrow line only
                char_right = x0
                break
        
        # If no vertical line found, estimate based on the layout
        # The character label is at x=373, and the field typically extends about 2.5x that width
        if not char_right:
            # Estimate: char field takes about 63% of the main area
            # The wide line x=73-1133 defines the form bounds
            form_left = 73
            form_right = 1133
            form_width = form_right - form_left
            char_right = form_left + int(form_width * 0.63)
            print(f"  Estimated char/society divider at x={char_right}")
        
        print(f"\nVertical lines found:")
        print(f"  Left margin: {left_margin}")
        print(f"  Char/society divider: {char_right}")
        
        if not left_margin or not char_right:
            print("Could not find required vertical boundaries")
            return
        
        if left_margin and char_right:
            char_field_x0 = left_margin + 2
            char_field_x1 = char_right - 2
            
            # Convert to main-relative percentages
            # The main canvas is defined in Season4a.json as:
            # "main": { "parent": "page", "x": 0.8, "y": 0.6, "x2": 99.2, "y2": 99.4 }
            # So main canvas in pixels (at 2x zoom):
            main_x_percent = 0.8
            main_y_percent = 0.6
            main_x2_percent = 99.2
            main_y2_percent = 99.4
            
            main_left = int(w * main_x_percent / 100)
            main_top = int(h * main_y_percent / 100)
            main_right = int(w * main_x2_percent / 100)
            main_bottom = int(h * main_y2_percent / 100)
            main_width = main_right - main_left
            main_height = main_bottom - main_top
            
            print(f"\nMain canvas boundaries:")
            print(f"  Pixels: x={main_left}, y={main_top}, x2={main_right}, y2={main_bottom}")
            print(f"  Size: {main_width}x{main_height}")
            
            # Character name field in main-relative %
            char_x = ((char_field_x0 - main_left) / main_width) * 100
            char_x2 = ((char_field_x1 - main_left) / main_width) * 100
            char_y = ((char_field_y0 - main_top) / main_height) * 100
            char_y2 = ((char_field_y1 - main_top) / main_height) * 100
            
            print(f"\nCharacter name field:")
            print(f"  Pixels: x={char_field_x0}, y={char_field_y0}, x2={char_field_x1}, y2={char_field_y1}")
            print(f"  Main %: x={char_x:.1f}, y={char_y:.1f}, x2={char_x2:.1f}, y2={char_y2:.1f}")
            
            # Now find society ID fields (right of the char name field)
            # Society ID has three parts: player number, dash, and character number
            
            # Find the right edge (another vertical line or page edge)
            society_right = None
            for x0, x1 in v_lines:
                if x0 > char_right + 50:  # at least 50px to the right
                    society_right = x0
                    break
            
            if not society_right:
                society_right = w - 10  # use page margin as fallback
            
            society_field_x0 = char_right + 2
            society_field_x1 = society_right - 2
            society_field_width = society_field_x1 - society_field_x0
            
            # Society ID is split into three parts
            # Player number takes ~60%, dash ~10%, char number ~30%
            player_x0 = society_field_x0
            player_x1 = society_field_x0 + int(society_field_width * 0.60)
            
            dash_x0 = player_x1
            dash_x1 = player_x1 + int(society_field_width * 0.10)
            
            char_num_x0 = dash_x1
            char_num_x1 = society_field_x1
            
            # Convert to percentages
            player_x = ((player_x0 - main_left) / main_width) * 100
            player_x2 = ((player_x1 - main_left) / main_width) * 100
            
            dash_x = ((dash_x0 - main_left) / main_width) * 100
            dash_x2 = ((dash_x1 - main_left) / main_width) * 100
            
            char_num_x = ((char_num_x0 - main_left) / main_width) * 100
            char_num_x2 = ((char_num_x1 - main_left) / main_width) * 100
            
            print(f"\nSociety ID player number:")
            print(f"  Main %: x={player_x:.1f}, y={char_y:.1f}, x2={player_x2:.1f}, y2={char_y2:.1f}")
            
            print(f"\nSociety ID dash:")
            print(f"  Main %: x={dash_x:.1f}, y={char_y:.1f}, x2={dash_x2:.1f}, y2={char_y2:.1f}")
            
            print(f"\nSociety ID char number:")
            print(f"  Main %: x={char_num_x:.1f}, y={char_y:.1f}, x2={char_num_x2:.1f}, y2={char_y2:.1f}")
            
            # Save as JSON
            content_positions = {
                "char": {
                    "x": round(char_x, 1),
                    "y": round(char_y, 1),
                    "x2": round(char_x2, 1),
                    "y2": round(char_y2, 1)
                },
                "societyid.player": {
                    "x": round(player_x, 1),
                    "y": round(char_y, 1),
                    "x2": round(player_x2, 1),
                    "y2": round(char_y2, 1)
                },
                "societyid.dash": {
                    "x": round(dash_x, 1),
                    "y": round(char_y, 1),
                    "x2": round(dash_x2, 1),
                    "y2": round(char_y2, 1)
                },
                "societyid.char_without_first_digit": {
                    "x": round(char_num_x, 1),
                    "y": round(char_y, 1),
                    "x2": round(char_num_x2, 1),
                    "y2": round(char_y2, 1)
                }
            }
            
            json_path = DEBUG_DIR / 'content_positions.json'
            with open(json_path, 'w') as f:
                json.dump(content_positions, f, indent=2)
                
                print(f"\nSaved content positions to: {json_path}")


if __name__ == '__main__':
    main()
