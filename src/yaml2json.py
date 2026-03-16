#!/usr/bin/env python3
"""YAML to JSON converter for layout files.

Finds all ``.yml`` files under the project's ``layouts/`` directory, converts
each to JSON format, and removes the original YAML file.

Requirements: refactor-chronicle2layout 8.1, 8.4, 8.5
"""

import glob
import json
import os
from pathlib import Path

import yaml


def convert_yaml_to_json(yaml_file: str) -> None:
    """Convert a single YAML file to JSON and delete the original.

    Args:
        yaml_file: Filesystem path to the ``.yml`` file to convert.
    """
    json_file = str(yaml_file).replace('.yml', '.json')

    with open(yaml_file, 'r') as f:
        yaml_data = yaml.safe_load(f)

    with open(json_file, 'w') as f:
        json.dump(yaml_data, f, indent=4)

    os.remove(yaml_file)
    print(f"Converted {yaml_file} -> {json_file}")


def main() -> None:
    """Find and convert all YAML layout files to JSON.

    Scans the ``layouts/`` directory tree (relative to the project root)
    for ``.yml`` files and converts each one in place.
    """
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    layouts_dir = root_dir / 'layouts'

    yaml_files = glob.glob(str(layouts_dir / '**/*.yml'), recursive=True)

    for yaml_file in yaml_files:
        convert_yaml_to_json(yaml_file)

    print(f"\nConverted {len(yaml_files)} YAML files to JSON")


if __name__ == '__main__':
    main()
