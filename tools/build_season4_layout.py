#!/usr/bin/env python3
"""Build a Season 4 parent layout JSON from extracted canvas coordinates.

Reads canvases.json from a debug directory and merges with template metadata
(loaded from season4_template.json) to produce a complete layout file.

Usage:
  python build_season4_layout.py 4-03 4a
  python build_season4_layout.py 4-04 4b
  python build_season4_layout.py 4-06 4c
  python build_season4_layout.py 4-07 4d
  python build_season4_layout.py 4-09 4e
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent.parent
DEBUG_BASE = SCRIPT_DIR.parent / "debug" / "season4"

# Variant metadata
VARIANT_INFO = {
    "4a": {
        "id": "pfs2.season4a",
        "description": "PFS2 Chronicle Sheet for Season 4 adventure scenarios 1, 2, 3, and 8"
    },
    "4b": {
        "id": "pfs2.season4b",
        "description": "PFS2 Chronicle Sheet for Season 4 adventure scenarios 4 and 5"
    },
    "4c": {
        "id": "pfs2.season4c",
        "description": "PFS2 Chronicle Sheet for Season 4 adventure scenario 6"
    },
    "4d": {
        "id": "pfs2.season4d",
        "description": "PFS2 Chronicle Sheet for Season 4 adventure scenario 7"
    },
    "4e": {
        "id": "pfs2.season4e",
        "description": "PFS2 Chronicle Sheet for Season 4 adventure scenarios 9-17"
    }
}

# Load template from external JSON file
with open(SCRIPT_DIR / "season4_template.json") as _f:
    TEMPLATE: dict = json.load(_f)


def main():
    if len(sys.argv) < 3:
        print("Usage: python build_season4_layout.py <scenario> <variant>")
        print("Examples:")
        print("  python build_season4_layout.py 4-03 4a")
        print("  python build_season4_layout.py 4-04 4b")
        print("  python build_season4_layout.py 4-06 4c")
        print("  python build_season4_layout.py 4-07 4d")
        print("  python build_season4_layout.py 4-09 4e")
        sys.exit(1)
    
    scenario = sys.argv[1]
    variant = sys.argv[2]
    
    if variant not in VARIANT_INFO:
        print(f"Error: Unknown variant '{variant}'")
        print(f"Valid variants: {', '.join(VARIANT_INFO.keys())}")
        sys.exit(1)
    
    canvases_path = DEBUG_BASE / scenario / "canvases.json"
    
    if not canvases_path.exists():
        print(f"Error: {canvases_path} not found")
        print(f"Run extract_season4_canvases.py {scenario} first")
        sys.exit(1)
    
    with open(canvases_path) as f:
        canvas_data = json.load(f)
    
    # Build output with variant-specific metadata
    output = TEMPLATE.copy()
    output["id"] = VARIANT_INFO[variant]["id"]
    output["description"] = VARIANT_INFO[variant]["description"]
    output["canvas"] = canvas_data["canvas"]
    
    # Write to Season4{variant}.generated.json
    output_filename = f"Season{variant}.generated.json"
    output_path = BASE / "layouts" / "pfs2" / "s4" / output_filename
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Generated: {output_path}")
    
    # Compare with existing
    existing_filename = f"Season{variant}.json"
    existing_path = BASE / "layouts" / "pfs2" / "s4" / existing_filename
    print(f"Compare with: {existing_path}")
    
    if existing_path.exists():
        with open(existing_path) as f:
            existing = json.load(f)
        if "canvas" in existing and "items" in existing["canvas"]:
            ex_items = existing["canvas"]["items"]
            gen_items = output["canvas"]["items"]
            print(f"\nItems canvas comparison:")
            print(f"  Generated: x={gen_items['x']}, y={gen_items['y']}, "
                  f"x2={gen_items['x2']}, y2={gen_items['y2']}")
            # Handle both x/y/x2/y2 and x1/y1/x2/y2 formats
            if 'x' in ex_items:
                print(f"  Existing:  x={ex_items['x']}, y={ex_items['y']}, "
                      f"x2={ex_items['x2']}, y2={ex_items['y2']}")
            elif 'x1' in ex_items:
                print(f"  Existing:  x1={ex_items['x1']}, y1={ex_items['y1']}, "
                      f"x2={ex_items['x2']}, y2={ex_items['y2']}")
            else:
                print(f"  Existing format not recognized: {ex_items}")


if __name__ == '__main__':
    main()
