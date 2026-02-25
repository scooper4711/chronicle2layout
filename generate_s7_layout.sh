#!/bin/bash

# Script to generate season 7 chronicle layouts
# Usage: ./generate_s7_layout.sh <path-to-chronicle-pdf>
#
# Example: ./generate_s7_layout.sh modules/pf2e-pfs07-year-of-battles-spark/assets/chronicles-1/710-chronicle-ShatteredBlades.pdf

set -e

if [ $# -ne 1 ]; then
    echo "Usage: $0 <path-to-chronicle-pdf>"
    echo "Example: $0 modules/pf2e-pfs07-year-of-battles-spark/assets/chronicles-1/710-chronicle-ShatteredBlades.pdf"
    exit 1
fi

PDF_PATH="$1"

# Check if file exists
if [ ! -f "$PDF_PATH" ]; then
    echo "Error: File not found: $PDF_PATH"
    exit 1
fi

# Extract filename from path
FILENAME=$(basename "$PDF_PATH" .pdf)

# Extract scenario number (e.g., "710" from "710-chronicle-ShatteredBlades")
SCENARIO_NUM=$(echo "$FILENAME" | sed -E 's/^([0-9]+)-chronicle-.*/\1/')

# Extract scenario name (e.g., "ShatteredBlades" from "710-chronicle-ShatteredBlades")
SCENARIO_NAME=$(echo "$FILENAME" | sed -E 's/^[0-9]+-chronicle-(.*)/\1/')

# Format scenario number as "7-XX"
FORMATTED_NUM="7-$(echo $SCENARIO_NUM | sed 's/^7//')"

# Convert PascalCase to space-separated words
# This handles most common cases like "ShatteredBlades" -> "Shattered Blades"
DESCRIPTION=$(echo "$SCENARIO_NAME" | sed -E 's/([a-z])([A-Z])/\1 \2/g' | sed -E 's/([A-Z]+)([A-Z][a-z])/\1 \2/g')

# Create full description with scenario number
FULL_DESCRIPTION="$FORMATTED_NUM $DESCRIPTION"

# Create layout ID
LAYOUT_ID="pfs2.s$FORMATTED_NUM"

# Create output filename
OUTPUT_FILE="layouts/pfs2/s7/$FORMATTED_NUM-$SCENARIO_NAME.json"

echo "Generating layout for: $FULL_DESCRIPTION"
echo "  Input:  $PDF_PATH"
echo "  Output: $OUTPUT_FILE"
echo "  ID:     $LAYOUT_ID"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find Python executable (prefer venv if available)
if [ -f "$PROJECT_ROOT/../.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/../.venv/bin/python"
else
    PYTHON="python3"
fi

# Run the chronicle2layout script
cd "$PROJECT_ROOT"
"$PYTHON" chronicle2layout/src/chronicle2layout.py \
  "$PDF_PATH" \
  --layout-dir layouts \
  --parent pfs2.season7 \
  --id "$LAYOUT_ID" \
  --description "$FULL_DESCRIPTION" \
  --default-chronicle "$PDF_PATH" \
  --output "$OUTPUT_FILE"

echo ""
echo "✓ Successfully generated: $OUTPUT_FILE"
