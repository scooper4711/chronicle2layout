#!/usr/bin/env python3
"""
Extract content field positions from Season 4 PDF chronicles by detecting grey form field boxes.
"""

import sys
import json
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import numpy as np

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
LAYOUTS_DIR = REPO_ROOT / 'layouts' / 'pfs2' / 's4'
DEBUG_DIR = SCRIPT_DIR.parent / 'debug' / 'season4'

ZOOM = 2  # 2x zoom for better detection


def get_pdf_path_from_layout(scenario):
    """Get PDF path by reading the layout JSON's defaultChronicleLocation."""
    # Find the layout JSON file for this scenario
    layout_files = list(LAYOUTS_DIR.glob(f"{scenario}-*.json"))
    if not layout_files:
        print(f"Error: Could not find layout file for scenario {scenario}")
        return None
    
    layout_path = layout_files[0]
    with open(layout_path) as f:
        layout = json.load(f)
    
    default_location = layout.get('defaultChronicleLocation')
    if not default_location:
        print(f"Error: No defaultChronicleLocation in {layout_path}")
        return None
    
    # defaultChronicleLocation is like "modules/pfs-chronicle-generator/assets/chronicles-4/4-03-LinnormsLegacyChronicle.pdf"
    # Convert to actual file path
    pdf_path = REPO_ROOT / default_location.replace('modules/pfs-chronicle-generator/', '')
    
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return None
    
    return pdf_path


def render_page_to_image(pdf_path, zoom=2):
    """Render the last page of a PDF to an image."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(doc.page_count - 1)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return page, img


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


def remove_overlapping_boxes(boxes):
    """
    Remove boxes that are contained within or heavily overlap with larger boxes.
    Keep the largest box in each overlapping group.
    """
    if not boxes:
        return []
    
    # Sort by area (largest first)
    sorted_boxes = sorted(boxes, key=lambda b: (b[2]-b[0]) * (b[3]-b[1]), reverse=True)
    
    kept_boxes = []
    for box in sorted_boxes:
        x0, y0, x1, y1 = box
        
        # Check if this box overlaps significantly with any kept box
        is_redundant = False
        for kept in kept_boxes:
            kx0, ky0, kx1, ky1 = kept
            
            # Calculate intersection
            ix0 = max(x0, kx0)
            iy0 = max(y0, ky0)
            ix1 = min(x1, kx1)
            iy1 = min(y1, ky1)
            
            if ix0 < ix1 and iy0 < iy1:
                # There is overlap
                intersection_area = (ix1 - ix0) * (iy1 - iy0)
                box_area = (x1 - x0) * (y1 - y0)
                
                # If >80% of this box overlaps with a kept box, it's redundant
                if intersection_area / box_area > 0.8:
                    is_redundant = True
                    break
        
        if not is_redundant:
            kept_boxes.append(box)
    
    return kept_boxes


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
    if len(sys.argv) < 2:
        print("Usage: extract_season4_content_v2.py <scenario>")
        print("Example: extract_season4_content_v2.py 4-03")
        sys.exit(1)
    
    scenario = sys.argv[1]
    
    PDF_PATH = get_pdf_path_from_layout(scenario)
    if not PDF_PATH:
        sys.exit(1)
    
    # Create debug directory
    debug_dir = DEBUG_DIR / scenario
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    page, img = render_page_to_image(PDF_PATH, zoom=ZOOM)
    words = words_positions(page, zoom=ZOOM)
    
    w, h = img.width, img.height
    
    # Find grey boxes (form fields)
    grey_boxes = find_grey_boxes(img)
    grey_boxes = remove_overlapping_boxes(grey_boxes)
    
    print(f"Found {len(grey_boxes)} grey boxes (form fields)")
    
    # Find labels to identify fields
    char_label = find_label(words, "Character")
    org_play_label = find_label(words, "Organized Play")
    starting_xp_label = find_label(words, "Starting XP")
    
    if not char_label:
        print("Warning: Could not find 'Character' label")
        return
    
    char_label_x = char_label[1]
    char_label_y = char_label[2]
    
    print(f"\nCharacter label at: ({char_label_x}, {char_label_y})")
    if org_play_label:
        print(f"Organized Play label at: ({org_play_label[1]}, {org_play_label[2]})")
    if starting_xp_label:
        print(f"Starting XP label at: ({starting_xp_label[1]}, {starting_xp_label[2]})")
    
    # All grey boxes are on the RIGHT side of the page (x > w/2)
    # Filter to right side boxes only
    right_boxes = [(x0, y0, x1, y1) for x0, y0, x1, y1 in grey_boxes if x0 > w / 2]
    
    print(f"\nFound {len(right_boxes)} grey boxes on right side")
    
    # Player info boxes are in the TOP area (y < 250 at 2x zoom)
    # Society ID boxes (Organized Play # and Character #)
    society_boxes = []
    for x0, y0, x1, y1 in right_boxes:
        if y0 < 250:  # Top area only
            if y1 - y0 > 25 and y1 - y0 < 80:  # Reasonable field height
                society_boxes.append((x0, y0, x1, y1))
                print(f"  Society ID box: x={x0}-{x1}, y={y0}-{y1}, size={x1-x0}x{y1-y0}")
    
    # Reward boxes (XP/GP fields) are below the society ID boxes
    # Look for Starting XP label to find the start of reward fields
    reward_boxes = []
    for x0, y0, x1, y1 in right_boxes:
        if y0 >= 250 and y0 < 1400:  # Reward fields area
            if y1 - y0 > 40:  # Reward boxes are taller
                reward_boxes.append((x0, y0, x1, y1))
                print(f"  Reward box: x={x0}-{x1}, y={y0}-{y1}, size={x1-x0}x{y1-y0}")
    
    if len(society_boxes) < 2:
        print(f"\nWarning: Expected 2 society ID boxes, found {len(society_boxes)}")
        print("Skipping society ID field detection")
        society_boxes = []
    
    if len(reward_boxes) < 6:
        print(f"\nWarning: Expected at least 6 reward boxes (Starting XP, XP Gained, Total XP, Starting GP, GP Spent, Total GP), found {len(reward_boxes)}")
    
    # Sort boxes top to bottom
    society_boxes.sort(key=lambda b: (b[1], b[0]))
    reward_boxes.sort(key=lambda b: b[1])
    
    # Convert to main-relative and rightbar-relative percentages
    # The main canvas is defined in Season4a.json as:
    # "main": { "parent": "page", "x": 0.8, "y": 0.6, "x2": 99.2, "y2": 99.4 }
    # "rightbar": { "parent": "main", "x": 78.8, "y": 32.0, "x2": 94.5, "y2": 81.5 }
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
    
    print(f"\nMain canvas: x={main_left}, y={main_top}, x2={main_right}, y2={main_bottom}")
    print(f"Main size: {main_width}x{main_height}")
    
    # Rightbar canvas is defined within main
    rightbar_x_percent = 78.8
    rightbar_y_percent = 32.0
    rightbar_x2_percent = 94.5
    rightbar_y2_percent = 81.5
    
    rightbar_left = main_left + int(main_width * rightbar_x_percent / 100)
    rightbar_top = main_top + int(main_height * rightbar_y_percent / 100)
    rightbar_right = main_left + int(main_width * rightbar_x2_percent / 100)
    rightbar_bottom = main_top + int(main_height * rightbar_y2_percent / 100)
    rightbar_width = rightbar_right - rightbar_left
    rightbar_height = rightbar_bottom - rightbar_top
    
    print(f"Rightbar canvas: x={rightbar_left}, y={rightbar_top}, x2={rightbar_right}, y2={rightbar_bottom}")
    print(f"Rightbar size: {rightbar_width}x{rightbar_height}")
    
    content_positions = {}
    # Improved character name field detection: find left vertical boundary and inner top line
    if society_boxes:
        soc_y0 = society_boxes[0][1]
        soc_y1 = society_boxes[0][3]
        char_y = ((soc_y0 - main_top) / main_height) * 100
        char_y2 = ((soc_y1 - main_top) / main_height) * 100
        gray_arr = np.array(img.convert('L'))
        # 1. Detect vertical left boundary line (dark pixels spanning most of society box height)
        vertical_dark_thresh = 100
        min_vertical_coverage = 0.6  # at least 60% of height dark
        height_span = soc_y1 - soc_y0
        vertical_candidates = []
        scan_x_end = max(0, society_boxes[0][0] - 20)  # stay left of first society box
        for x in range(main_left, scan_x_end):
            dark_count = 0
            for y in range(soc_y0, soc_y1 + 1):
                if gray_arr[y, x] < vertical_dark_thresh:
                    dark_count += 1
            if dark_count / max(1, height_span) >= min_vertical_coverage:
                vertical_candidates.append(x)
        left_boundary_x = None
        if vertical_candidates:
            # Choose longest contiguous streak start
            streak_start = vertical_candidates[0]
            prev = vertical_candidates[0]
            best_streak = (streak_start, streak_start)
            for x in vertical_candidates[1:]:
                if x == prev + 1:
                    best_streak = (streak_start, x)
                else:
                    streak_start = x
                prev = x
            left_boundary_x = best_streak[0]
        # 2. Detect inner horizontal line for character field top (below left boundary region)
        # Search a band around soc_y0+ (upper third) to soc_y1- (lower third)
        horizontal_band_top = soc_y0 + int((soc_y1 - soc_y0) * 0.15)
        horizontal_band_bottom = soc_y0 + int((soc_y1 - soc_y0) * 0.55)
        inner_line_run = None
        dark_thresh = 110
        min_run_len = 120
        if left_boundary_x is None:
            left_boundary_x = main_left  # fallback
        search_start_x = left_boundary_x + 25  # skip blank space
        search_end_x = society_boxes[0][0] - 25
        for y_scan in range(horizontal_band_top, horizontal_band_bottom):
            run_start = None
            for x in range(search_start_x, search_end_x):
                is_dark = gray_arr[y_scan, x] < dark_thresh
                if is_dark:
                    if run_start is None:
                        run_start = x
                else:
                    if run_start is not None:
                        run_len = x - run_start
                        if run_len >= min_run_len:
                            if inner_line_run is None or run_len > (inner_line_run[1] - inner_line_run[0]):
                                inner_line_run = (run_start, x - 1, y_scan)
                        run_start = None
            if run_start is not None:
                run_len = search_end_x - run_start
                if run_len >= min_run_len and (inner_line_run is None or run_len > (inner_line_run[1] - inner_line_run[0])):
                    inner_line_run = (run_start, search_end_x - 1, y_scan)
        if inner_line_run:
            line_x0, line_x1, line_y = inner_line_run
            char_x = ((line_x0 - main_left) / main_width) * 100
            char_x2 = ((line_x1 - main_left) / main_width) * 100
            content_positions['char'] = {
                'x': round(char_x, 1),
                'y': round(char_y, 1),
                'x2': round(char_x2, 1),
                'y2': round(char_y2, 1)
            }
            print(f"\nCharacter inner line detected at y={line_y}, x={line_x0}-{line_x1}")
            print(f"Character field (main %): x={char_x:.1f}, y={char_y:.1f}, x2={char_x2:.1f}, y2={char_y2:.1f}")
        else:
            print("\nWarning: Could not detect inner character line; char field will require manual adjustment.")
    
    # Process society ID boxes if we found them
    if len(society_boxes) >= 2:
        org_play_box = society_boxes[0]  # "Organized Play #" (societyid.player)
        char_num_box = society_boxes[1]  # "Character #" (societyid.char_without_first_digit)
        
        # Convert to main-relative %
        org_x = ((org_play_box[0] - main_left) / main_width) * 100
        org_y = ((org_play_box[1] - main_top) / main_height) * 100
        org_x2 = ((org_play_box[2] - main_left) / main_width) * 100
        org_y2 = ((org_play_box[3] - main_top) / main_height) * 100
        
        char_num_x = ((char_num_box[0] - main_left) / main_width) * 100
        char_num_y = ((char_num_box[1] - main_top) / main_height) * 100
        char_num_x2 = ((char_num_box[2] - main_left) / main_width) * 100
        char_num_y2 = ((char_num_box[3] - main_top) / main_height) * 100
        
        # Society ID player number - split the org_play box for player number and dash
        org_box_width = org_play_box[2] - org_play_box[0]
        player_x1_px = org_play_box[0] + int(org_box_width * 0.85)  # Player number takes 85%
        
        player_x = org_x
        player_x2 = ((player_x1_px - main_left) / main_width) * 100
        
        dash_x = player_x2
        dash_x2 = org_x2
        
        content_positions["societyid.player"] = {
            "x": round(player_x, 1),
            "y": round(org_y, 1),
            "x2": round(player_x2, 1),
            "y2": round(org_y2, 1)
        }
        content_positions["societyid.dash"] = {
            "x": round(dash_x, 1),
            "y": round(org_y, 1),
            "x2": round(dash_x2, 1),
            "y2": round(org_y2, 1)
        }
        content_positions["societyid.char_without_first_digit"] = {
            "x": round(char_num_x, 1),
            "y": round(char_num_y, 1),
            "x2": round(char_num_x2, 1),
            "y2": round(char_num_y2, 1)
        }
        
        print(f"\nSociety ID player number:")
        print(f"  Main %: x={player_x:.1f}, y={org_y:.1f}, x2={player_x2:.1f}, y2={org_y2:.1f}")
        print(f"\nSociety ID dash:")
        print(f"  Main %: x={dash_x:.1f}, y={org_y:.1f}, x2={dash_x2:.1f}, y2={org_y2:.1f}")
        print(f"\nSociety ID char number:")
        print(f"  Main %: x={char_num_x:.1f}, y={char_num_y:.1f}, x2={char_num_x2:.1f}, y2={char_num_y2:.1f}")
    
    # Process reward boxes
    reward_field_names = [
        "starting_xp",
        "xp_gained",
        "total_xp",
        "starting_gp",
        "gp_spent",
        "total_gp"
    ]
    
    for i, box in enumerate(reward_boxes[:6]):  # Only process first 6 boxes
        if i >= len(reward_field_names):
            break
        
        field_name = reward_field_names[i]
        
        # Convert to rightbar-relative %
        box_x = ((box[0] - rightbar_left) / rightbar_width) * 100
        box_y = ((box[1] - rightbar_top) / rightbar_height) * 100
        box_x2 = ((box[2] - rightbar_left) / rightbar_width) * 100
        box_y2 = ((box[3] - rightbar_top) / rightbar_height) * 100
        
        content_positions[field_name] = {
            "x": round(box_x, 1),
            "y": round(box_y, 1),
            "x2": round(box_x2, 1),
            "y2": round(box_y2, 1)
        }
        
        print(f"\n{field_name}:")
        print(f"  Rightbar %: x={box_x:.1f}, y={box_y:.1f}, x2={box_x2:.1f}, y2={box_y2:.1f}")
    
    # ---- Bottom event info fields detection ----
    # Each field has a thin line above its label: Event, Event Code, Date, GM Organized Play #
    # We'll detect horizontal dark runs above each label and use those as field x/x2; keep y/y2 equal to existing layout row if possible.
    def find_words_line(words_list, tokens):
        """Find a sequence of tokens on one horizontal line; return combined bbox or None."""
        lowered = [(t.lower(), x0, y0, x1, y1) for (t, x0, y0, x1, y1) in words_list]
        for i, (tw, x0, y0, x1, y1) in enumerate(lowered):
            if tw == tokens[0].lower():
                line_y0 = y0
                line_y1 = y1
                match = True
                cur_x0 = x0
                cur_x1 = x1
                idx = 1
                j = i + 1
                while idx < len(tokens) and j < len(lowered):
                    nw, nx0, ny0, nx1, ny1 = lowered[j]
                    if nw == tokens[idx].lower() and abs(ny0 - line_y0) < 5:
                        cur_x1 = nx1
                        line_y0 = min(line_y0, ny0)
                        line_y1 = max(line_y1, ny1)
                        idx += 1
                    j += 1
                if idx == len(tokens):
                    return (cur_x0, line_y0, cur_x1, line_y1)
        return None

    bottom_labels = {
        'event': ['event'],
        'eventcode': ['event', 'code'],
        'date': ['date'],
        'gmid': ['gm', 'organized', 'play', '#']
    }

    # Determine approximate bottom row y from labels; collect label bboxes
    label_bboxes = {}
    for key, seq in bottom_labels.items():
        bbox = find_words_line(words, seq)
        if bbox:
            label_bboxes[key] = bbox
    if label_bboxes:
        # Use image gray array for line detection
        arr_gray = np.array(img.convert('L'))
        dark_thresh = 120
        min_run = 80
        # Compute average label vertical bounds to derive y/y2 percentages (use society row height pattern ~2.6%)
        # We'll set y/y2 from first label bbox relative to main
        first_key = next(iter(label_bboxes))
        fy0 = label_bboxes[first_key][1]
        fy1 = label_bboxes[first_key][3]
        # Assume line is above label; search band 5-50 px above
        line_band_top = max(0, fy0 - 50)
        line_band_bottom = max(0, fy0 - 5)
        # Helper to detect line horizontally spanning above a given label
        def detect_field_line(label_bbox):
            lx0, ly0, lx1, ly1 = label_bbox
            best_run = None
            for y_scan in range(line_band_top, line_band_bottom):
                run_start = None
                for x in range(main_left, main_right):
                    val = arr_gray[y_scan, x]
                    if val < dark_thresh:
                        if run_start is None:
                            run_start = x
                    else:
                        if run_start is not None:
                            run_len = x - run_start
                            if run_len >= min_run:
                                # Choose run that overlaps label x-range
                                if (run_start <= lx1 and x >= lx0):
                                    if best_run is None or run_len > (best_run[1] - best_run[0]):
                                        best_run = (run_start, x - 1, y_scan)
                            run_start = None
                if run_start is not None:
                    run_len = main_right - run_start
                    if run_len >= min_run and (run_start <= lx1 and main_right >= lx0):
                        if best_run is None or run_len > (best_run[1] - best_run[0]):
                            best_run = (run_start, main_right - 1, y_scan)
            return best_run
        # Establish common y/y2 row using existing layout percentages if present
        # Fallback: approximate row height using label height*1.5
        row_height_px = int((fy1 - fy0) * 1.5)
        # Use line y if detected to anchor top
        bottom_row_y = None
        lines_detected = {}
        for key, bbox in label_bboxes.items():
            line_run = detect_field_line(bbox)
            if line_run:
                lines_detected[key] = line_run
                if bottom_row_y is None or line_run[2] < bottom_row_y:
                    bottom_row_y = line_run[2]
        if bottom_row_y is None:
            bottom_row_y = line_band_top + 10
        # Compute y/y2 percentages
        field_y_percent = ((bottom_row_y - main_top) / main_height) * 100
        field_y2_percent = ((bottom_row_y + row_height_px - main_top) / main_height) * 100
        # Build ordered list of labels by center x
        ordered = []
        for key, bbox in label_bboxes.items():
            cx = (bbox[0] + bbox[2]) / 2.0
            ordered.append((cx, key, bbox))
        ordered.sort()
        # Determine partition boundaries using midpoints between centers
        partitions = []
        for i, (cx, key, bbox) in enumerate(ordered):
            if i == 0:
                left_bound = max(main_left, bbox[0] - 40)
            else:
                prev_cx = ordered[i-1][0]
                left_bound = int((prev_cx + cx) / 2)
            if i == len(ordered) - 1:
                right_bound = min(main_right, bbox[2] + 40)
            else:
                next_cx = ordered[i+1][0]
                right_bound = int((cx + next_cx) / 2)
            partitions.append((key, left_bound, right_bound, bbox))
        # Local line search in each partition
        for key, p_left, p_right, bbox in partitions:
            best_run = None
            for y_scan in range(line_band_top, line_band_bottom):
                run_start = None
                for x in range(p_left, p_right):
                    val = arr_gray[y_scan, x]
                    if val < dark_thresh:
                        if run_start is None:
                            run_start = x
                    else:
                        if run_start is not None:
                            run_len = x - run_start
                            if run_len >= min_run:
                                if best_run is None or run_len > (best_run[1] - best_run[0]):
                                    best_run = (run_start, x - 1, y_scan)
                            run_start = None
                if run_start is not None:
                    run_len = p_right - run_start
                    if run_len >= min_run and (best_run is None or run_len > (best_run[1] - best_run[0])):
                        best_run = (run_start, p_right - 1, y_scan)
            if best_run:
                lx0, lx1, ly = best_run
            else:
                lx0, lx1 = p_left, p_right
                ly = bottom_row_y
            fx = ((lx0 - main_left) / main_width) * 100
            fx2 = ((lx1 - main_left) / main_width) * 100
            content_positions[key] = {
                'x': round(fx, 1),
                'y': round(field_y_percent, 1),
                'x2': round(fx2, 1),
                'y2': round(field_y2_percent, 1)
            }
            print(f"\nSegmented bottom field '{key}': part x={lx0}-{lx1}, row y={ly}")
            print(f"  Main %: x={fx:.1f}, y={field_y_percent:.1f}, x2={fx2:.1f}, y2={field_y2_percent:.1f}")
    else:
        print("\nWarning: Bottom event labels not found; skipping bottom field detection.")

    # Save as JSON
    json_path = debug_dir / 'content_positions.json'
    with open(json_path, 'w') as f:
        json.dump(content_positions, f, indent=2)
        
    print(f"\nSaved content positions to: {json_path}")


if __name__ == '__main__':
    main()
