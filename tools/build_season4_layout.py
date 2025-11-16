#!/usr/bin/env python3
"""Build a Season 4 parent layout JSON from extracted canvas coordinates.

Reads canvases.json from a debug directory and merges with template metadata
to produce a complete layout file.

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

BASE = Path(__file__).resolve().parents[2]
DEBUG_BASE = BASE / "chronicle2layout" / "debug" / "season4"

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

# Template for Season 4 parent layouts
TEMPLATE = {
    "id": "pfs2.season4a",
    "description": "PFS2 Chronicle Sheet for Season 4 adventure scenarios 1, 2, 3, and 8",
    "parent": "pfs2",
    "flags": ["hidden"],
    "aspectratio": "603:783",
    "parameters": {
        "Event Info": {
            "event": {
                "type": "text",
                "description": "Event name",
                "example": "PaizoCon"
            },
            "eventcode": {
                "type": "text",
                "description": "Event code",
                "example": 1234
            },
            "date": {
                "type": "text",
                "description": "The date on which the game session took place",
                "example": "27.06.2020"
            },
            "gmid": {
                "type": "text",
                "description": "Gamemasters PFS ID",
                "example": 654321
            }
        },
        "Player Info": {
            "char": {
                "type": "text",
                "description": "Players character name",
                "example": "Stormageddon"
            },
            "societyid": {
                "type": "societyid",
                "description": "Pathfinder Society ID",
                "example": "123456-2001"
            }
        },
        "Rewards": {
            "starting_xp": {
                "type": "text",
                "description": "Starting XP",
                "example": 2
            },
            "xp_gained": {
                "type": "text",
                "description": "XP Gained",
                "example": 4
            },
            "total_xp": {
                "type": "text",
                "description": "Total XP",
                "example": 6
            },
            "starting_gp": {
                "type": "text",
                "description": "Starting GP",
                "example": "1cp"
            },
            "treasure_bundles_gp": {
                "type": "text",
                "description": "Gold from treasure bundles",
                "example": 23
            },
            "income_earned": {
                "type": "text",
                "description": "Income earned (gp)",
                "example": 1.8
            },
            "gp_gained": {
                "type": "text",
                "description": "GP Gained",
                "example": "4gp 2sp"
            },
            "gp_spent": {
                "type": "text",
                "description": "GP Spent",
                "example": "5sp"
            },
            "total_gp": {
                "type": "text",
                "description": "Total GP",
                "example": "3gp 7sp 1cp"
            }
        },
        "Checkboxes, Reputation and Items": {
            "reputation": {
                "type": "multiline",
                "description": "Reputation Gained",
                "example": "Grand Archive: +4",
                "lines": 3
            }
        },
        "Notes": {
            "notes": {
                "type": "multiline",
                "description": "Notes on the chronicle sheet",
                "example": "This is a player note",
                "lines": 12
            }
        }
    },
    "presets": {
        "defaultfont": {
            "font": "Helvetica",
            "fontsize": 14
        },
        "player.infoline": {
            "presets": ["defaultfont"],
            "canvas": "main",
            "y": 1.0,
            "y2": 4.0,
            "align": "CM"
        },
        "rightbar": {
            "presets": ["defaultfont"],
            "canvas": "rightbar",
            "fontsize": 14,
            "x": 0.0,
            "x2": 100.0,
            "align": "CM"
        },
        "event.infoline": {
            "presets": ["defaultfont"],
            "canvas": "main",
            "y": 94.8,
            "y2": 97.8,
            "align": "CB"
        },
        "max_area": {
            "x": 0.0,
            "y": 0.0,
            "x2": 100.0,
            "y2": 100.0
        },
        "reputation": {
            "presets": ["defaultfont", "max_area"],
            "canvas": "reputation",
            "align": "LM",
            "lines": 3
        },
        "notes": {
            "presets": ["defaultfont", "max_area"],
            "canvas": "notes",
            "align": "LM",
            "lines": 12,
            "fontsize": 12
        }
    },
    "content": [
        {
            "value": "param:char",
            "type": "text",
            "presets": ["player.infoline"],
            "fontweight": "bold",
            "align": "LB",
            "x": 1.5,
            "x2": 63.5
        },
        {
            "type": "trigger",
            "trigger": "param:societyid",
            "content": [
                {
                    "value": "param:societyid.player",
                    "type": "text",
                    "fontsize": 9,
                    "fontweight": "bold",
                    "presets": ["player.infoline"],
                    "x": 67.2,
                    "x2": 87.3,
                    "align": "RM"
                },
                {
                    "value": "-",
                    "type": "text",
                    "fontsize": 9,
                    "fontweight": "bold",
                    "presets": ["player.infoline"],
                    "x": 87.3,
                    "x2": 89.2,
                    "align": "CM"
                },
                {
                    "value": "param:societyid.char_without_first_digit",
                    "type": "text",
                    "presets": ["player.infoline"],
                    "fontsize": 9,
                    "fontweight": "bold",
                    "x": 90.8,
                    "x2": 97.8,
                    "align": "LM"
                }
            ]
        },
        {
            "value": "param:starting_xp",
            "type": "text",
            "presets": ["rightbar"],
            "y": 4.9,
            "y2": 13.8
        },
        {
            "value": "param:xp_gained",
            "type": "text",
            "presets": ["rightbar"],
            "y": 19,
            "y2": 28
        },
        {
            "value": "param:total_xp",
            "type": "text",
            "presets": ["rightbar"],
            "y": 33.2,
            "y2": 42
        },
        {
            "value": "param:starting_gp",
            "type": "text",
            "presets": ["rightbar"],
            "y": 46.9,
            "y2": 56.7
        },
        {
            "value": "Treasure:",
            "type": "text",
            "presets": ["rightbar"],
            "align": "LB",
            "fontsize": 9,
            "y": 62,
            "y2": 65
        },
        {
            "value": "param:treasure_bundles_gp",
            "type": "text",
            "presets": ["rightbar"],
            "align": "RB",
            "fontsize": 9,
            "x": 50,
            "y": 62,
            "y2": 65
        },
        {
            "value": "Income:",
            "type": "text",
            "presets": ["rightbar"],
            "align": "LB",
            "fontsize": 9,
            "y": 65,
            "y2": 68
        },
        {
            "value": "param:income_earned",
            "type": "text",
            "presets": ["rightbar"],
            "align": "RB",
            "fontsize": 9,
            "x": 50,
            "y": 65,
            "y2": 68
        },
        {
            "value": "GP Gained:",
            "type": "text",
            "presets": ["rightbar"],
            "align": "LB",
            "fontsize": 9,
            "y": 68,
            "y2": 71
        },
        {
            "value": "total_line",
            "type": "line",
            "presets": ["rightbar"],
            "color": "black",
            "linewidth": 0.5,
            "x": 50,
            "y": 68,
            "y2": 68.1
        },
        {
            "value": "param:gp_gained",
            "type": "text",
            "presets": ["rightbar"],
            "align": "RB",
            "fontsize": 9,
            "x": 50,
            "y": 68,
            "y2": 71
        },
        {
            "value": "param:gp_spent",
            "type": "text",
            "presets": ["rightbar"],
            "y": 77.2,
            "y2": 86.2
        },
        {
            "value": "param:total_gp",
            "type": "text",
            "presets": ["rightbar"],
            "y": 92,
            "y2": 99
        },
        {
            "value": "param:event",
            "type": "text",
            "presets": ["event.infoline"],
            "align": "LB",
            "x": 2,
            "x2": 45.2
        },
        {
            "value": "param:eventcode",
            "type": "text",
            "presets": ["event.infoline"],
            "align": "LB",
            "x": 47.2,
            "x2": 62.2
        },
        {
            "value": "param:date",
            "type": "text",
            "presets": ["event.infoline"],
            "x": 64.0,
            "x2": 78.6
        },
        {
            "value": "param:gmid",
            "type": "text",
            "presets": ["event.infoline"],
            "x": 80.1,
            "x2": 99.4
        },
        {
            "value": "param:reputation",
            "type": "multiline",
            "presets": ["reputation"],
            "canvas": "reputation",
            "align": "LM",
            "lines": 3,
            "x": 1
        },
        {
            "value": "param:notes",
            "type": "multiline",
            "presets": ["notes"],
            "canvas": "notes",
            "align": "LM",
            "lines": 12,
            "x": 1,
            "y": 3.8
        }
    ]
}


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
