#!/usr/bin/env python3
"""Extract canvases from the last page of a Season 4 chronicle PDF.

Saves cropped images to the debug directory for review.

This script uses PyMuPDF to render the page and Pillow to do simple image scans
for vertical/horizontal black lines. It's heuristic and intended for iterative
improvement.

Usage: run from project root with project's venv python.
    python extract_season4_canvases.py [scenario_number]
    Example: python extract_season4_canvases.py 4-04
"""
from PIL import Image
import numpy as np
import sys
from pathlib import Path

# Allow importing from src/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from shared_utils import render_page_to_image, words_positions

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
PDF_DIR = REPO_ROOT / "modules" / "pfs-chronicle-generator" / "assets" / "chronicles-4"

# Get scenario from command line or default to 4-03
SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "4-03"
PDF_NAME = f"{SCENARIO}-*.pdf"
# Find the actual PDF file
pdf_files = list(PDF_DIR.glob(PDF_NAME))
if not pdf_files:
    print(f"No PDF found matching {PDF_NAME} in {PDF_DIR}")
    sys.exit(1)
PDF_PATH = pdf_files[0]
PDF_NAME = PDF_PATH.name

DEBUG_DIR = SCRIPT_DIR.parent / "debug" / "season4" / SCENARIO
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# Render settings
ZOOM = 2  # rendering scale


def find_label_y(words, candidates):
    # return y (top) of first matching word from candidates
    low = None
    for text,x0,y0,x1,y1 in words:
        t = text.lower()
        for c in candidates:
            if c.lower() in t:
                return y0
    return None


def find_vertical_borders(img, threshold=60, min_height_fraction=0.6):
    # img is PIL Image RGB
    arr = np.array(img.convert('L'))
    h,w = arr.shape
    col_dark = np.mean(arr < threshold, axis=0)  # fraction of dark pixels per column
    borders = []
    for x,frac in enumerate(col_dark):
        if frac > min_height_fraction:
            borders.append(x)
    # group contiguous columns
    groups = []
    if borders:
        cur = [borders[0]]
        for x in borders[1:]:
            if x == cur[-1] + 1:
                cur.append(x)
            else:
                groups.append((cur[0], cur[-1]))
                cur = [x]
        groups.append((cur[0], cur[-1]))
    return groups  # list of (x0,x1)


def find_horizontal_borders(img, threshold=60, min_width_fraction=0.6):
    arr = np.array(img.convert('L'))
    h,w = arr.shape
    row_dark = np.mean(arr < threshold, axis=1)
    borders = []
    for y,frac in enumerate(row_dark):
        if frac > min_width_fraction:
            borders.append(y)
    groups = []
    if borders:
        cur = [borders[0]]
        for y in borders[1:]:
            if y == cur[-1] + 1:
                cur.append(y)
            else:
                groups.append((cur[0], cur[-1]))
                cur = [y]
        groups.append((cur[0], cur[-1]))
    return groups


def crop_and_save(img, box, name):
    crop = img.crop(box)
    out = DEBUG_DIR / name
    crop.save(out)
    print('Saved', out)
    return out


def main():
    if not PDF_PATH.exists():
        print('PDF not found:', PDF_PATH)
        return
    page, img = render_page_to_image(PDF_PATH, zoom=ZOOM)
    words = words_positions(page, zoom=ZOOM)

    # Save the full rendered page for reference
    (DEBUG_DIR / 'page.png').write_bytes(img.tobytes()) if False else img.save(DEBUG_DIR / 'page.png')
    print('Rendered page saved to', DEBUG_DIR / 'page.png')

    # Find label y positions
    y_starting_xp = find_label_y(words, ['Starting', 'Starting XP', 'Starting_XP'])
    y_total_gp = find_label_y(words, ['Total GP', 'Total_GP', 'GP Gained', 'GP Gained'])
    y_adventure_summary = find_label_y(words, ['Adventure', 'Adventure Summary'])
    y_boons = find_label_y(words, ['Boons'])
    y_items = find_label_y(words, ['Items'])
    y_notes = find_label_y(words, ['Notes'])
    y_reputation = find_label_y(words, ['Reputation', 'Reputation/Infamy', 'Infamy'])

    print('Label y positions (px):', {
        'starting_xp': y_starting_xp,
        'total_gp': y_total_gp,
        'adventure_summary': y_adventure_summary,
        'boons': y_boons,
        'items': y_items,
        'notes': y_notes,
        'reputation': y_reputation
    })

    # detect vertical borders from whole image
    vgroups = find_vertical_borders(img)
    hgroups = find_horizontal_borders(img)
    print('Vertical groups:', vgroups)
    print('Horizontal groups:', hgroups)

    h,w = img.height, img.width
    
    # Define main canvas (page with margins clipped)
    # Main canvas typically has small margins from page edges
    MARGIN = 10  # typical margin in scaled pixels
    main_left = MARGIN
    main_top = MARGIN
    main_right = w - MARGIN
    main_bottom = h - MARGIN
    
    # find leftmost and rightmost vertical border groups (thin lines)
    left_border = vgroups[0][1] if vgroups else main_left
    right_border = vgroups[-1][0] if vgroups else main_right

    # Determine if there's a middle vertical divider (for sections like rightbar)
    # If we have exactly 2 vertical groups, they're left and right page edges
    # Look for a middle divider by scanning for vertical lines in the middle region
    middle_divider = None
    if len(vgroups) >= 2:
        # Check if there might be a middle divider we missed (use lower threshold)
        middle_groups = find_vertical_borders(img, threshold=60, min_height_fraction=0.3)
        for (x0,x1) in middle_groups:
            if 0.5*w < x0 < 0.9*w:  # roughly in right half
                middle_divider = x1
                break

    # Summary: starts below Adventure Summary black header
    y_top_sum = None
    if y_adventure_summary:
        for (y0,y1) in hgroups:
            if y0 <= y_adventure_summary <= y1 + 20:
                y_top_sum = y1 + 2
                break
    if not y_top_sum:
        y_top_sum = y_adventure_summary + 10 if y_adventure_summary else int(h*0.08)
    
    # find a horizontal border below as bottom (should be the Boons header)
    y_bottom_sum = None
    for (y0,y1) in hgroups:
        if y0 > y_top_sum + 20:
            y_bottom_sum = y0 - 2
            break
    if not y_bottom_sum:
        y_bottom_sum = int(h*0.3)

    # Boons: starts below Boons black header
    y_top_boons = None
    if y_boons:
        for (y0,y1) in hgroups:
            if y0 <= y_boons <= y1 + 20:
                y_top_boons = y1 + 2
                break
    if not y_top_boons:
        y_top_boons = y_boons + 10 if y_boons else int(h*0.3)
    
    # bottom: find horizontal border before Items/Reputation (whichever comes first)
    # In 4-07, Reputation comes before Items
    y_bottom_boons = None
    next_section_y = min(y for y in [y_items, y_reputation] if y is not None)
    if next_section_y:
        for (y0,y1) in hgroups:
            if y0 <= next_section_y <= y1 + 20:
                y_bottom_boons = y0 - 2
                break
    if not y_bottom_boons:
        y_bottom_boons = int(h*0.6)

    # Items: below 'Items' black header to bottom border
    y_top_items = None
    if y_items:
        for (y0,y1) in hgroups:
            if y0 <= y_items <= y1 + 20:
                y_top_items = y1 + 2
                break
    if not y_top_items:
        y_top_items = y_items + 10 if y_items else int(h*0.35)
    
    # bottom = find next horizontal border after y_top_items
    y_bottom_items = None
    for (y0,y1) in hgroups:
        if y0 > y_top_items + 10:
            y_bottom_items = y0 - 2
            break
    if not y_bottom_items:
        y_bottom_items = int(h*0.65)
    
    x_left_items = left_border + 2
    
    # Find the vertical divider between Items and whatever is beside it
    # Look for a vertical line around 40-60% of page width
    items_sample = img.crop((int(w*0.3), y_top_items, int(w*0.7), min(y_top_items + 100, y_bottom_items)))
    arr_items = np.array(items_sample.convert('L'))
    h_items_sample, w_items_sample = arr_items.shape
    
    items_divider_x = None
    for x_rel in range(w_items_sample):
        col = arr_items[:, x_rel]
        dark_frac = np.mean(col < 60)
        if dark_frac > 0.7:  # vertical line
            items_divider_x = int(w*0.3) + x_rel
            break
    
    if items_divider_x:
        x_right_items = items_divider_x - 2
        print(f'  Found Items divider at x={items_divider_x}')
    else:
        x_right_items = int(w*0.5)  # fallback
    
    items_rel = (x_left_items - main_left, y_top_items - main_top, x_right_items - main_left, y_bottom_items - main_top)
    crop_and_save(img, (x_left_items, y_top_items, x_right_items, y_bottom_items), 'items.png')
    print(f'Items (main-relative): x={items_rel[0]}, y={items_rel[1]}, w={items_rel[2]-items_rel[0]}, h={items_rel[3]-items_rel[1]}')

    # Notes: Check if it's at the bottom (4-07) or beside Items (normal)
    # If Notes y-position is greater than Reputation y-position, it's at the bottom
    notes_below_reputation = y_notes and y_reputation and y_notes > y_reputation
    
    y_top_notes = None
    if y_notes:
        for (y0,y1) in hgroups:
            if y0 <= y_notes <= y1 + 20:
                y_top_notes = y1 + 2
                break
    if not y_top_notes:
        y_top_notes = y_notes + 10 if y_notes else int(h*0.5)

    gold_box_x = None  # Initialize for both cases
    
    if notes_below_reputation:
        # Special case: Notes spans full width at bottom (where Reputation normally is)
        x_left_notes = left_border + 2
        x_right_notes = right_border - 2
        y_bottom_notes = hgroups[-2][0] - 2 if len(hgroups) >= 2 else int(h*0.85)
        
        notes_rel = (x_left_notes - main_left, y_top_notes - main_top, x_right_notes - main_left, y_bottom_notes - main_top)
        crop_and_save(img, (x_left_notes, y_top_notes, x_right_notes, y_bottom_notes), 'notes.png')
    else:
        # Normal case: Notes is beside Items
        x_left_notes = x_right_items + 2  # add small gap past the divider
        
        # right bound: temporary - we'll scan to find the Gold box
        x_right_notes_temp = right_border - 2
        
        # bottom: find horizontal border before reputation (reputation header is the bottom bound)
        y_bottom_notes = None
        if y_reputation:
            for (y0,y1) in hgroups:
                if y0 <= y_reputation <= y1 + 20:
                    y_bottom_notes = y0 - 2  # stop before reputation header
                    break
        if not y_bottom_notes:
            y_bottom_notes = hgroups[-2][0] - 2 if len(hgroups) >= 2 else int(h*0.85)
        
        # Scan for the vertical black bar (Gold box) within the notes region
        # Look for a vertical line of dark pixels around 2/3 of the way across
        notes_crop_initial = img.crop((x_left_notes, y_top_notes, x_right_notes_temp, y_bottom_notes))
        arr_notes = np.array(notes_crop_initial.convert('L'))
        arr_notes = np.array(notes_crop_initial.convert('L'))
        h_notes, w_notes = arr_notes.shape
        
        # Scan columns starting from 50% to 90% of notes width
        gold_box_x_rel = None
        for x_rel in range(int(w_notes*0.5), int(w_notes*0.9)):
            col = arr_notes[:, x_rel]
            dark_frac = np.mean(col < 60)  # fraction of dark pixels
            if dark_frac > 0.7:  # if more than 70% of column is dark
                gold_box_x_rel = x_rel
                break
        
        # Calculate the actual gold box position in page coordinates
        gold_box_x = None
        if gold_box_x_rel:
            gold_box_x = x_left_notes + gold_box_x_rel
            x_right_notes = gold_box_x - 2
            print(f'  Found vertical black bar (Gold box) at x={gold_box_x}')
        else:
            x_right_notes = x_right_notes_temp
        
        notes_rel = (x_left_notes - main_left, y_top_notes - main_top, x_right_notes - main_left, y_bottom_notes - main_top)
        crop_and_save(img, (x_left_notes, y_top_notes, x_right_notes, y_bottom_notes), 'notes.png')
    print(f'Notes (main-relative): x={notes_rel[0]}, y={notes_rel[1]}, w={notes_rel[2]-notes_rel[0]}, h={notes_rel[3]-notes_rel[1]}')
    
    # Now calculate Summary and Boons using the discovered gold box position
    # Summary right edge extends to the right border (same width as entire page content)
    x_left_sum = left_border + 2
    x_right_sum = right_border - 2  # extends to right edge
    sum_rel = (x_left_sum - main_left, y_top_sum - main_top, x_right_sum - main_left, y_bottom_sum - main_top)
    crop_and_save(img, (x_left_sum, y_top_sum, x_right_sum, y_bottom_sum), 'summary.png')
    print(f'Summary (main-relative): x={sum_rel[0]}, y={sum_rel[1]}, w={sum_rel[2]-sum_rel[0]}, h={sum_rel[3]-sum_rel[1]}')
    
    # Boons has the same left as summary, right edge is the gold box (same as Notes right edge)
    # If no gold box (4-07 case), scan for rightbar divider
    x_left_boons = left_border + 2
    if gold_box_x:
        x_right_boons = gold_box_x - 2
    else:
        # Scan Boons region for vertical divider (rightbar boundary)
        boons_sample = img.crop((int(w*0.7), y_top_boons, right_border, min(y_top_boons + 100, h)))
        arr_boons = np.array(boons_sample.convert('L'))
        h_boons_sample, w_boons_sample = arr_boons.shape
        
        rightbar_divider_x = None
        for x_rel in range(w_boons_sample):
            col = arr_boons[:, x_rel]
            dark_frac = np.mean(col < 60)
            if dark_frac > 0.7:  # vertical line
                rightbar_divider_x = int(w*0.7) + x_rel
                break
        
        if rightbar_divider_x:
            x_right_boons = rightbar_divider_x - 2
            gold_box_x = rightbar_divider_x  # Set for rightbar calculation
            print(f'  Found Boons/Rightbar divider at x={rightbar_divider_x}')
        else:
            x_right_boons = int(w*0.75)
    
    boons_rel = (x_left_boons - main_left, y_top_boons - main_top, x_right_boons - main_left, y_bottom_boons - main_top)
    crop_and_save(img, (x_left_boons, y_top_boons, x_right_boons, y_bottom_boons), 'boons.png')
    print(f'Boons (main-relative): x={boons_rel[0]}, y={boons_rel[1]}, w={boons_rel[2]-boons_rel[0]}, h={boons_rel[3]-boons_rel[1]}')

    # Calculate rightbar y coordinates first
    # y_top from starting_xp - find horizontal border group containing this y and start below it
    y_top_rb = None
    if y_starting_xp:
        for (y0,y1) in hgroups:
            if y0 <= y_starting_xp <= y1 + 20:  # label is in or just below this border
                y_top_rb = y1 + 2  # start below the black bar
                break
    if not y_top_rb:
        y_top_rb = y_starting_xp + 10 if y_starting_xp else int(h*0.1)
    
    # y_bottom: should extend to reputation header (not cut off early)
    y_bottom_rb = None
    if y_reputation:
        for (y0,y1) in hgroups:
            if y0 <= y_reputation <= y1 + 20:
                y_bottom_rb = y0 - 2  # stop before reputation header
                break
    if not y_bottom_rb:
        y_bottom_rb = hgroups[-2][0] - 2 if len(hgroups) >= 2 else int(h*0.85)

    # Rightbar: left edge is the gold box, right edge is page border
    # The left edge is the same black bar that bounds Notes on the right
    if gold_box_x:
        # Scan the rightbar region to find where the black header ends
        # The gold box border itself is black, so we need to find the right edge of it
        x_left_rb_temp = gold_box_x + 2
        x_right_rb = right_border - 2
        
        # Extract a sample column from the rightbar region to find where black ends
        rb_sample = img.crop((x_left_rb_temp, y_top_rb, x_right_rb, min(y_top_rb + 100, h)))
        arr_rb = np.array(rb_sample.convert('L'))
        h_rb_sample, w_rb_sample = arr_rb.shape
        
        # Scan columns from left to find first non-black column
        gold_box_right = None
        for x_rel in range(min(50, w_rb_sample)):  # scan first 50 pixels
            col = arr_rb[:, x_rel]
            dark_frac = np.mean(col < 60)
            if dark_frac < 0.5:  # if less than 50% is dark, we've passed the header
                gold_box_right = x_rel
                break
        
        if gold_box_right:
            x_left_rb = x_left_rb_temp + gold_box_right
            print(f'  Found Gold box right edge at relative x={gold_box_right}, rightbar left={x_left_rb}')
        else:
            x_left_rb = x_left_rb_temp
    else:
        x_left_rb = int(w*0.8)
    x_right_rb = right_border - 2
    
    # Convert rightbar to main-relative coordinates
    rb_rel = (x_left_rb - main_left, y_top_rb - main_top, x_right_rb - main_left, y_bottom_rb - main_top)
    crop_and_save(img, (x_left_rb, y_top_rb, x_right_rb, y_bottom_rb), 'rightbar.png')
    print(f'Rightbar (main-relative): x={rb_rel[0]}, y={rb_rel[1]}, w={rb_rel[2]-rb_rel[0]}, h={rb_rel[3]-rb_rel[1]}')

    # Reputation: handle two cases
    # Normal: below Notes at bottom of page
    # 4-07 special: between Items and Notes (where Notes header is)
    if notes_below_reputation:
        # Special case: Reputation is above Notes, spanning full width
        y_top_rep = None
        if y_reputation:
            for (y0,y1) in hgroups:
                if y0 <= y_reputation <= y1 + 20:
                    y_top_rep = y1 + 2
                    break
        if not y_top_rep:
            y_top_rep = y_reputation + 10 if y_reputation else int(h*0.5)
        
        # bottom: find horizontal border before Notes header
        y_bottom_rep = None
        if y_notes:
            for (y0,y1) in hgroups:
                if y0 <= y_notes <= y1 + 20:
                    y_bottom_rep = y0 - 2
                    break
        if not y_bottom_rep:
            y_bottom_rep = y_notes - 10 if y_notes else int(h*0.8)
    else:
        # Normal case: Reputation is at the bottom
        y_top_rep = None
        if y_reputation:
            for (y0,y1) in hgroups:
                if y0 <= y_reputation <= y1 + 20:
                    y_top_rep = y1 + 2
                    break
        if not y_top_rep:
            y_top_rep = y_reputation + 10 if y_reputation else int(h*0.82)
        
        # bottom: find a horizontal group after y_top_rep
        y_bottom_rep = None
        for (y0,y1) in hgroups:
            if y0 > y_top_rep + 5:
                y_bottom_rep = y0 - 2
                break
        if not y_bottom_rep:
            y_bottom_rep = int(h*0.9)
    
    x_left_rep = left_border + 2
    x_right_rep = right_border - 2
    rep_rel = (x_left_rep - main_left, y_top_rep - main_top, x_right_rep - main_left, y_bottom_rep - main_top)
    crop_and_save(img, (x_left_rep, y_top_rep, x_right_rep, y_bottom_rep), 'reputation.png')
    print(f'Reputation (main-relative): x={rep_rel[0]}, y={rep_rel[1]}, w={rep_rel[2]-rep_rel[0]}, h={rep_rel[3]-rep_rel[1]}')

    print('Done. Crops in', DEBUG_DIR)
    
    # Generate JSON output with precise percentages
    main_width = main_right - main_left
    main_height = main_bottom - main_top
    page_width = w
    page_height = h
    
    def to_main_pct(x_rel, y_rel, x2_rel, y2_rel):
        """Convert main-relative pixel coordinates to main-relative percentages."""
        return {
            "x": round((x_rel / main_width) * 100.0, 1),
            "y": round((y_rel / main_height) * 100.0, 1),
            "x2": round((x2_rel / main_width) * 100.0, 1),
            "y2": round((y2_rel / main_height) * 100.0, 1)
        }
    
    def to_page_pct(x_px, y_px, x2_px, y2_px):
        """Convert absolute pixel coordinates to page percentages."""
        return {
            "x": round((x_px / page_width) * 100.0, 1),
            "y": round((y_px / page_height) * 100.0, 1),
            "x2": round((x2_px / page_width) * 100.0, 1),
            "y2": round((y2_px / page_height) * 100.0, 1)
        }
    
    # Build canvas dict
    canvases = {
        "page": {
            "x": 0.0,
            "y": 0.0,
            "x2": 100.0,
            "y2": 100.0
        },
        "main": {
            "parent": "page",
            **to_page_pct(main_left, main_top, main_right, main_bottom)
        },
        "summary": {
            "parent": "main",
            **to_main_pct(*sum_rel)
        },
        "boons": {
            "parent": "main",
            **to_main_pct(*boons_rel)
        },
        "items": {
            "parent": "main",
            **to_main_pct(*items_rel)
        },
        "notes": {
            "parent": "main",
            **to_main_pct(*notes_rel)
        },
        "rightbar": {
            "parent": "main",
            **to_main_pct(*rb_rel)
        },
        "reputation": {
            "parent": "main",
            **to_main_pct(*rep_rel)
        }
    }
    
    import json
    json_output = {
        "canvas": canvases,
        "_metadata": {
            "source_pdf": PDF_NAME,
            "zoom": ZOOM,
            "page_size_px": {"width": w, "height": h},
            "main_size_px": {"width": main_width, "height": main_height}
        }
    }
    
    json_path = DEBUG_DIR / 'canvases.json'
    with open(json_path, 'w') as f:
        json.dump(json_output, f, indent=2)
    print(f'\nGenerated canvas JSON: {json_path}')

if __name__ == '__main__':
    main()
