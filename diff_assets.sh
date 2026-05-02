#!/usr/bin/env zsh

# Compares JSON files in modules/pfs-chronicle-generator/assets against
# ../pfs-chronicle-generator/assets. Uses timestamp as a fast first pass,
# then cmp to skip identical content. Offers to show a diff for each
# genuinely changed file.
#
# Usage: ./diff_assets.sh

SCRIPT_DIR="${0:A:h}"
SOURCE_DIR="${SCRIPT_DIR}/modules/pfs-chronicle-generator/assets"
TARGET_DIR="${SCRIPT_DIR}/../pfs-chronicle-generator/assets"

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: source directory not found: $SOURCE_DIR"
    exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: target directory not found: $TARGET_DIR"
    exit 1
fi

updated=0

for source_file in "$SOURCE_DIR"/**/*.json(.N); do
    relative_path="${source_file#$SOURCE_DIR/}"
    target_file="${TARGET_DIR}/${relative_path}"

    # Timestamp first (fast), then content compare only if newer
    if [[ -f "$target_file" ]] && [[ "$source_file" -nt "$target_file" ]] && ! cmp -s "$source_file" "$target_file"; then
        updated=$((updated + 1))
        echo ""
        echo "Changed: $relative_path"
        echo -n "  Show diff? [y/N] "
        read -r answer < /dev/tty
        if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
            diff --color=auto -u "$target_file" "$source_file" || true
        fi
    fi
done

echo ""
if [[ $updated -eq 0 ]]; then
    echo "No changed JSON files found."
else
    echo "$updated changed JSON file(s) found."
fi
