#!/usr/bin/env python3
import yaml
import json
import glob
import os
from pathlib import Path

def convert_yaml_to_json(yaml_file):
    """Convert a YAML file to JSON format"""
    json_file = str(yaml_file).replace('.yml', '.json')
    
    # Read YAML
    with open(yaml_file, 'r') as f:
        yaml_data = yaml.safe_load(f)
    
    # Write JSON
    with open(json_file, 'w') as f:
        json.dump(yaml_data, f, indent=4)
    
    # Remove YAML file
    os.remove(yaml_file)
    print(f"Converted {yaml_file} -> {json_file}")

def main():
    # Get the root directory of the project
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    layouts_dir = root_dir / 'layouts'
    
    # Find all YAML files
    yaml_files = glob.glob(str(layouts_dir / '**/*.yml'), recursive=True)
    
    # Convert each file
    for yaml_file in yaml_files:
        convert_yaml_to_json(yaml_file)
    
    print(f"\nConverted {len(yaml_files)} YAML files to JSON")

if __name__ == '__main__':
    main()
