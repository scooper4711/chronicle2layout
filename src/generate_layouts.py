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
import argparse

# Base paths
BASE_DIR = Path("/Users/stephen/git/HelloFoundry/pfs-chronicle-generator")
MODULES_DIR = BASE_DIR / "modules"
LAYOUTS_DIR = BASE_DIR / "layouts/pfs2"
DEBUG_DIR = BASE_DIR / "debug"

# Season configurations
SEASON_CONFIGS = {
    3: {
        "module_name": "pfs-chronicle-generator",
        "chronicles_subdirs": ["assets/chronicles-3"],
        "layouts_dir": "s3",
        "parent_id": "pfs2.season3",
        "layout_id": "Season 3",
        "pdf_pattern": r"3-(\d+)-(.+)\.pdf",
        "default_chronicle_pattern": "modules/pfs-chronicle-generator/{subdir}/{filename}"
    },
    4: {
        "module_name": "pfs-chronicle-generator",
        "chronicles_subdirs": ["assets/chronicles-4"],
        "layouts_dir": "s4",
        "parent_id": "pfs2.season4",
        "layout_id": "Season 4",
        "pdf_pattern": r"4-(\d+)-(.+)\.pdf",
        "default_chronicle_pattern": "modules/pfs-chronicle-generator/{subdir}/{filename}"
    },
    5: {
        "module_name": "pf2e-pfs05-year-of-unfettered-exploration",
        "chronicles_subdirs": ["assets/chronicles-1", "assets/chronicles-2"],
        "layouts_dir": "s5",
        "parent_id": "pfs2.season5",
        "layout_id": "Season 5",
        "pdf_pattern": r"5-(\d+)-(.+)Chronicle\.pdf",
        "default_chronicle_pattern": "modules/pf2e-pfs05-year-of-unfettered-exploration/{subdir}/{filename}"
    },
    6: {
        "module_name": "pf2e-pfs06-year-of-immortal-influence",
        "chronicles_subdirs": ["assets/chronicles-1", "assets/chronicles-2"],
        "layouts_dir": "s6",
        "parent_id": "pfs2.season6",
        "layout_id": "Season 6",
        "pdf_pattern": r"6-(\d+)-(.+)\.pdf",
        "default_chronicle_pattern": "modules/pf2e-pfs06-year-of-immortal-influence/{subdir}/{filename}"
    },
    7: {
        "module_name": "pf2e-pfs07-year-of-battles-spark",
        "chronicles_subdirs": ["assets/chronicles-1", "assets/chronicles-2"],
        "layouts_dir": "s7",
        "parent_id": "pfs2.season7",
        "layout_id": "Season 7",
        "pdf_pattern": r"7(\d+)-chronicle-(.+)\.pdf",
        "default_chronicle_pattern": "modules/pf2e-pfs07-year-of-battles-spark/{subdir}/{filename}"
    }
}

def title_to_description(season_num: int, scenario_num: str, title: str) -> str:
    """Convert a filename title to a proper description."""
    # Split on camelCase
    words = re.findall('[A-Z][^A-Z]*', title)
    if not words:
        # If no camelCase, split on spaces or underscores
        words = title.replace('_', ' ').split()
    
    # Join words with spaces
    formatted_title = ' '.join(words)
    return f"{season_num}-{scenario_num} {formatted_title}"

def process_season(season_num: int, scenario_filter=None):
    """Process chronicles for a given season.
    If scenario_filter is provided (set of scenario numbers as zero-padded strings), only those are processed."""
    config = SEASON_CONFIGS[season_num]
    layouts_path = LAYOUTS_DIR / config["layouts_dir"]
    debug_base = DEBUG_DIR / f"season{season_num}"
    
    # Create directories if they don't exist
    layouts_path.mkdir(parents=True, exist_ok=True)
    debug_base.mkdir(parents=True, exist_ok=True)
    
    # Process each chronicles subdirectory
    for chronicles_subdir in config["chronicles_subdirs"]:
        chronicles_path = MODULES_DIR / config["module_name"] / chronicles_subdir
        
        if not chronicles_path.exists():
            print(f"Skipping {chronicles_subdir} (directory not found)")
            continue
        
        print(f"\nProcessing {chronicles_subdir}...")
        
        # Find all chronicle PDFs for this season
        for pdf_file in chronicles_path.glob("*.pdf"):
            match = re.match(config["pdf_pattern"], pdf_file.name)
            if not match:
                print(f"Warning: Couldn't parse filename {pdf_file.name}, skipping")
                continue
                
            scenario_num = match.group(1).zfill(2)

            # Apply scenario filter if provided
            if scenario_filter and scenario_num not in scenario_filter:
                continue
            title = match.group(2)
            
            # Construct layout filename
            layout_name = f"{season_num}-{scenario_num}-{title}"
            if layout_name.endswith("Chronicle"):
                layout_name = layout_name[:-9]
            layout_file = layouts_path / f"{layout_name}.json"
            
            # Construct defaultChronicleLocation if pattern provided
            default_chronicle_location = None
            if config["default_chronicle_pattern"]:
                default_chronicle_location = config["default_chronicle_pattern"].format(
                    subdir=chronicles_subdir,
                    filename=pdf_file.name
                )
            
            # Create debug directory for this scenario
            debug_dir = debug_base / f"{season_num}-{scenario_num}"
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"  Processing {pdf_file.name}...")
            
            # Generate description
            description = title_to_description(season_num, scenario_num, title)
            
            # Use the virtual environment Python
            python_exe = "/Users/stephen/git/HelloFoundry/.venv/bin/python"
            
            # Run chronicle2layout.py
            # Determine parent layout variant for Season 4
            parent_id = config["parent_id"]
            if season_num == 4:
                sn = int(scenario_num)
                if sn in {1,2,3,8}:
                    parent_id = "pfs2.season4a"
                elif sn in {4,5}:
                    parent_id = "pfs2.season4b"
                elif sn == 6:
                    parent_id = "pfs2.season4c"
                elif sn == 7:
                    parent_id = "pfs2.season4d"
                elif 9 <= sn <= 17:
                    parent_id = "pfs2.season4e"

            cmd = [
                python_exe, "chronicle2layout.py",
                str(pdf_file),
                "--output", str(layout_file),
                "--parent", parent_id,
                "--id", f"pfs2.s{season_num}-{scenario_num}",
                "--description", description,
                "--layout-dir", str(BASE_DIR / "layouts")
            ]
            
            # Add default chronicle location if available
            if default_chronicle_location:
                cmd.extend(["--default-chronicle", default_chronicle_location])
            
            try:
                subprocess.run(cmd, check=True, cwd=BASE_DIR / "chronicle2layout" / "src")
                print(f"  Successfully generated {layout_file.name}")
                
            except subprocess.CalledProcessError as e:
                print(f"  Error processing {pdf_file.name}: {e}")
            except Exception as e:
                print(f"  Unexpected error processing {pdf_file.name}: {e}")

def main():
    """Process chronicles for one or more seasons."""
    parser = argparse.ArgumentParser(description="Generate layout JSONs for PFS chronicles")
    parser.add_argument("--season", "-s", type=int, nargs="*", default=[],
                        help="Season number(s) to process (e.g., -s 6 7). If omitted, process all available seasons.")
    parser.add_argument("--scenarios", "-n", type=str, nargs="*", default=[],
                        help="Specific scenario numbers (e.g., -n 01 02 08). Only applied to listed seasons.")
    args = parser.parse_args()

    seasons = args.season if args.season else sorted(SEASON_CONFIGS.keys())
    scenario_filter = set(args.scenarios) if args.scenarios else None
    for s in seasons:
        if s not in SEASON_CONFIGS:
            print(f"Skipping unknown season {s}")
            continue
        print(f"\nProcessing Season {s}...")
        process_season(s, scenario_filter=scenario_filter if scenario_filter else None)

if __name__ == "__main__":
    main()
