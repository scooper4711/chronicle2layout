#!/usr/bin/env bash
set -euo pipefail

# Generate layout JSON files from all leaf blueprint files.
# Activates the project virtualenv, then runs blueprint2layout for each
# blueprint that has a matching chronicle PDF.

SCRIPT_DIR="$(dirname "$0")"
BLUEPRINTS_DIR="${SCRIPT_DIR}/Blueprints"
LAYOUTS_BASE="${SCRIPT_DIR}/modules/pfs-chronicle-generator/assets/layouts"

source "${SCRIPT_DIR}/.venv/bin/activate"

success_count=0
fail_count=0
skip_count=0

while IFS= read -r -d '' blueprint_path; do
    # Read id and defaultChronicleLocation from the blueprint JSON
    read_result="$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
bp_id = d.get('id', '')
loc = d.get('defaultChronicleLocation', '')
print(bp_id)
print(loc)
" "$blueprint_path")"
    blueprint_id="$(echo "$read_result" | sed -n '1p')"
    chronicle_location="$(echo "$read_result" | sed -n '2p')"

    # Skip parent/root blueprints (no defaultChronicleLocation)
    if [[ -z "$chronicle_location" ]]; then
        echo "SKIP (no defaultChronicleLocation): $blueprint_path"
        skip_count=$((skip_count + 1))
        continue
    fi

    chronicle_pdf="${SCRIPT_DIR}/${chronicle_location}"
    if [[ ! -f "$chronicle_pdf" ]]; then
        echo "SKIP (chronicle PDF not found: ${chronicle_location}): $blueprint_path"
        skip_count=$((skip_count + 1))
        continue
    fi

    # Extract the relative path under Blueprints/, e.g. pfs/bounties/b13.blueprint.json
    rel_path="${blueprint_path#"${BLUEPRINTS_DIR}/"}"
    # Directory portion, e.g. pfs/bounties
    rel_dir="$(dirname "$rel_path")"

    # Output filename derived from blueprint id, e.g. pfs2.bounty-layout-b13 → bounty-layout-b13.json
    output_name="${blueprint_id#*.}"
    layout_dir="${LAYOUTS_BASE}/${rel_dir}"
    output_path="${layout_dir}/${output_name}.json"

    mkdir -p "$layout_dir"

    echo "Processing: $blueprint_path"
    echo "  PDF:    $chronicle_pdf"
    echo "  Output: $output_path"

    if python -m blueprint2layout "$blueprint_path" "$chronicle_pdf" "$output_path" --blueprints-dir "$BLUEPRINTS_DIR"; then
        success_count=$((success_count + 1))
    else
        echo "  FAILED"
        fail_count=$((fail_count + 1))
    fi
done < <(find "$BLUEPRINTS_DIR" -name '*.blueprint.json' -print0 | sort -z)

echo ""
echo "Done: ${success_count} succeeded, ${fail_count} failed, ${skip_count} skipped"
