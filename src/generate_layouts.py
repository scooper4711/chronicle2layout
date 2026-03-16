#!/usr/bin/env python3
"""
Script to generate layout files for PFS chronicles from multiple seasons.
This script processes PDF chronicles and generates corresponding layout JSON files
with proper IDs and metadata.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
import subprocess
import argparse


def derive_paths(base_dir: Path) -> tuple[Path, Path, Path]:
    """Derive standard project directories from the base directory.

    Args:
        base_dir: Project root directory.

    Returns:
        A tuple of (modules_dir, layouts_dir, debug_dir).

    Requirements: refactor-chronicle2layout 6.2
    """
    modules_dir = base_dir / "modules"
    layouts_dir = base_dir / "layouts" / "pfs2"
    debug_dir = base_dir / "debug"
    return modules_dir, layouts_dir, debug_dir

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

def process_season(
    season_num: int,
    base_dir: Path,
    modules_dir: Path,
    layouts_dir: Path,
    debug_dir: Path,
    python_exe: str,
    scenario_filter: set[str] | None = None,
) -> None:
    """Process chronicles for a given season.

    Args:
        season_num: The season number to process.
        base_dir: Project root directory.
        modules_dir: Path to the modules directory.
        layouts_dir: Path to the layouts/pfs2 directory.
        debug_dir: Path to the debug output directory.
        python_exe: Path to the Python executable for subprocess calls.
        scenario_filter: If provided, only process these scenario numbers
            (zero-padded strings like "01", "02").

    Requirements: refactor-chronicle2layout 6.1, 6.2, 6.3, 6.4, 6.5
    """
    config = SEASON_CONFIGS[season_num]
    layouts_path = layouts_dir / config["layouts_dir"]
    debug_base = debug_dir / f"season{season_num}"

    # Create directories if they don't exist
    layouts_path.mkdir(parents=True, exist_ok=True)
    debug_base.mkdir(parents=True, exist_ok=True)

    # Process each chronicles subdirectory
    for chronicles_subdir in config["chronicles_subdirs"]:
        chronicles_path = modules_dir / config["module_name"] / chronicles_subdir

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
            scenario_debug_dir = debug_base / f"{season_num}-{scenario_num}"
            scenario_debug_dir.mkdir(parents=True, exist_ok=True)

            print(f"  Processing {pdf_file.name}...")

            # Generate description
            description = title_to_description(season_num, scenario_num, title)

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
                "--layout-dir", str(base_dir / "layouts")
            ]

            # Add default chronicle location if available
            if default_chronicle_location:
                cmd.extend(["--default-chronicle", default_chronicle_location])

            try:
                subprocess.run(cmd, check=True, cwd=base_dir / "chronicle2layout" / "src")
                print(f"  Successfully generated {layout_file.name}")

            except subprocess.CalledProcessError as e:
                print(f"  Error processing {pdf_file.name}: {e}")
            except Exception as e:
                print(f"  Unexpected error processing {pdf_file.name}: {e}")

def main() -> None:
    """Process chronicles for one or more seasons.

    Parses CLI arguments for season selection, scenario filtering, project
    root directory, and Python executable path, then runs chronicle
    processing for each requested season.

    Requirements: refactor-chronicle2layout 6.1, 6.2, 6.3, 6.4, 6.5
    """
    parser = argparse.ArgumentParser(description="Generate layout JSONs for PFS chronicles")
    parser.add_argument("--season", "-s", type=int, nargs="*", default=[],
                        help="Season number(s) to process (e.g., -s 6 7). If omitted, process all available seasons.")
    parser.add_argument("--scenarios", "-n", type=str, nargs="*", default=[],
                        help="Specific scenario numbers (e.g., -n 01 02 08). Only applied to listed seasons.")
    parser.add_argument("--base-dir", type=Path, default=None,
                        help="Project root directory (default: parent of chronicle2layout/)")
    parser.add_argument("--python", type=str, default=None,
                        help="Python executable path (default: sys.executable)")
    args = parser.parse_args()

    base_dir: Path = args.base_dir or Path(__file__).resolve().parents[2]
    python_exe: str = args.python or sys.executable
    modules_dir, layouts_dir, debug_dir = derive_paths(base_dir)

    seasons = args.season if args.season else sorted(SEASON_CONFIGS.keys())
    scenario_filter: set[str] | None = set(args.scenarios) if args.scenarios else None
    for s in seasons:
        if s not in SEASON_CONFIGS:
            print(f"Skipping unknown season {s}")
            continue
        print(f"\nProcessing Season {s}...")
        process_season(
            s,
            base_dir=base_dir,
            modules_dir=modules_dir,
            layouts_dir=layouts_dir,
            debug_dir=debug_dir,
            python_exe=python_exe,
            scenario_filter=scenario_filter,
        )

if __name__ == "__main__":
    main()
