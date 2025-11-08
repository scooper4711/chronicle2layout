#!/usr/bin/env python3
"""
Script to generate layout files for PFS chronicles from multiple seasons.
This script processes PDF chronicles and generates corresponding layout JSON files
with proper IDs and metadata.
"""

import os
import re
import json
from pathlib import Path
import subprocess

# Base paths
BASE_DIR = Path("/Users/stephen/git/HelloFoundry/pfs-chronicle-generator")
CHRONICLES_DIR = BASE_DIR / "chronicles"
LAYOUTS_DIR = BASE_DIR / "layouts/pfs2"
DEBUG_DIR = BASE_DIR / "debug"

# Season configurations
SEASON_CONFIGS = {
    5: {
        "chronicles_dir": "Season 5",
        "layouts_dir": "s5",
        "parent_id": "pfs2.season5",
        "layout_id": "Season 5",
        "pdf_pattern": r"5-(\d+)-(.+)Chronicle\.pdf"
    },
    6: {
        "chronicles_dir": "Season 6",
        "layouts_dir": "s6",
        "parent_id": "pfs2.season6",
        "layout_id": "Season 6",
        "pdf_pattern": r"6-(\d+)-(.+)\.pdf"
    },
    7: {
        "chronicles_dir": "Season 7",
        "layouts_dir": "s7",
        "parent_id": "pfs2.season7",
        "layout_id": "Season 7",
        "pdf_pattern": r"7(\d+)-chronicle-(.+)\.pdf"
    }
}

def title_to_description(scenario_num: str, title: str) -> str:
    """Convert a filename title to a proper description."""
    # Remove any file extension
    title = os.path.splitext(title)[0]
    # Split on camelCase
    words = re.findall('[A-Z][^A-Z]*', title)
    if not words:
        # If no camelCase, split on spaces or underscores
        words = title.replace('_', ' ').split()
    
    # Join words and capitalize first letter of each
    formatted_title = ' '.join(word.capitalize() for word in words)
    return f"PFS2 Chronicle Sheet for {scenario_num}: {formatted_title}"

def process_season(season_num: int):
    """Process all chronicles for a given season."""
    config = SEASON_CONFIGS[season_num]
    chronicles_path = CHRONICLES_DIR / config["chronicles_dir"]
    layouts_path = LAYOUTS_DIR / config["layouts_dir"]
    debug_base = DEBUG_DIR / f"season{season_num}"
    
    # Create directories if they don't exist
    layouts_path.mkdir(parents=True, exist_ok=True)
    debug_base.mkdir(parents=True, exist_ok=True)
    
    # Find all chronicle PDFs for this season
    for pdf_file in chronicles_path.glob("*.pdf"):
        match = re.match(config["pdf_pattern"], pdf_file.name)
        if not match:
            print(f"Warning: Couldn't parse filename {pdf_file.name}, skipping")
            continue
            
        scenario_num = match.group(1).zfill(2)
        title = match.group(2)
        
        # Construct layout filename
        layout_name = f"{season_num}-{scenario_num}-{title}"
        if layout_name.endswith("Chronicle"):
            layout_name = layout_name[:-9]
        layout_file = layouts_path / f"{layout_name}.json"
        
        # Create debug directory for this scenario
        debug_dir = debug_base / f"{season_num}-{scenario_num}"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nProcessing {pdf_file.name}...")
        
        # Run chronicle2layout.py
        cmd = [
            "python3", "chronicle2layout.py",
            str(pdf_file),
            "--layout-dir", str(layouts_path),
            "--layout-id", config["layout_id"],
            "-o", str(layout_file),
            "--debug-dir", str(debug_dir)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            
            # Read generated JSON
            with open(layout_file) as f:
                layout_data = json.load(f)
            
            # Add required metadata
            layout_data["id"] = f"pfs2.s{season_num}-{scenario_num}"
            layout_data["description"] = f"{season_num}-{scenario_num} {title}"
            layout_data["parent"] = config["parent_id"]
            
            # Write back updated JSON
            with open(layout_file, 'w') as f:
                json.dump(layout_data, f, indent=2)
                
            print(f"Successfully generated {layout_file.name}")
            
        except subprocess.CalledProcessError as e:
            print(f"Error processing {pdf_file.name}: {e}")
        except Exception as e:
            print(f"Unexpected error processing {pdf_file.name}: {e}")

def main():
    """Process chronicles from seasons 5, 6, and 7."""
    for season in [5, 6, 7]:
        print(f"\nProcessing Season {season}...")
        process_season(season)

if __name__ == "__main__":
    main()
