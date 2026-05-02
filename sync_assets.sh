#!/usr/bin/env zsh

# Pushes newer generated files from modules/pfs-chronicle-generator/assets
# out to the sibling ../pfs-chronicle-generator/assets repo.
# Uses timestamp as a fast first pass, then cmp to skip identical content.
#
# Usage: ./sync_assets.sh [--dry-run]
#   --dry-run   Show what would be copied without actually copying.

SCRIPT_DIR="${0:A:h}"
SOURCE_DIR="${SCRIPT_DIR}/modules/pfs-chronicle-generator/assets"
TARGET_DIR="${SCRIPT_DIR}/../pfs-chronicle-generator/assets"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: source directory not found: $SOURCE_DIR"
    exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: target directory not found: $TARGET_DIR"
    exit 1
fi

copied=0
skipped=0

for source_file in "$SOURCE_DIR"/**/*(.N); do
    relative_path="${source_file#$SOURCE_DIR/}"

    # Skip .DS_Store files
    if [[ "${relative_path:t}" == ".DS_Store" ]]; then
        continue
    fi

    target_file="${TARGET_DIR}/${relative_path}"

    if [[ ! -f "$target_file" ]]; then
        if $DRY_RUN; then
            echo "[new]     $relative_path"
        else
            mkdir -p "${target_file:h}"
            cp "$source_file" "$target_file"
            echo "[new]     $relative_path"
        fi
        copied=$((copied + 1))
    elif [[ "$source_file" -nt "$target_file" ]] && ! cmp -s "$source_file" "$target_file"; then
        # Newer AND content actually differs
        if $DRY_RUN; then
            echo "[updated] $relative_path"
        else
            cp "$source_file" "$target_file"
            echo "[updated] $relative_path"
        fi
        copied=$((copied + 1))
    else
        skipped=$((skipped + 1))
    fi
done

echo ""
if $DRY_RUN; then
    echo "Dry run complete. $copied file(s) would be copied, $skipped unchanged file(s) skipped."
else
    echo "Sync complete. $copied file(s) copied, $skipped unchanged file(s) skipped."
fi
