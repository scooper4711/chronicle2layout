"""Layout JSON construction for season layout files.

Builds the output JSON structure with id, description, parent,
and canvas fields following the LAYOUT_FORMAT.md specification.

Public functions:
    build_layout_json: Construct the season layout JSON dict.
    build_output_path: Construct the output file path for a variant.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from season_layout_generator.models import CanvasCoordinates, PageRegions

# Coordinate tuple for the full-page canvas (always covers 0–100 on both axes)
_PAGE_COORDS: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)

# Region field names on PageRegions that are written to the canvas section
# (excludes 'main', which is handled separately with parent='page')
_REGION_FIELDS: tuple[str, ...] = tuple(
    f.name for f in fields(PageRegions) if f.name != "main"
)


def _variant_suffix(variant_index: int) -> str:
    """Return the alphabetical suffix for a variant index.

    Index 0 → "" (no suffix), index 1 → "a", index 2 → "b", etc.

    Args:
        variant_index: 0-based variant index.

    Returns:
        Empty string for the first variant; lowercase letter for subsequent ones.
    """
    if variant_index == 0:
        return ""
    return chr(ord("a") + variant_index - 1)


def _build_id(
    collection_name: str,
    season_number: int | None,
    suffix: str,
) -> str:
    """Construct the layout id field.

    Args:
        collection_name: Collection identifier ("5", "Quests", "Bounties").
        season_number: Season number, or None for Quests/Bounties.
        suffix: Variant suffix ("", "a", "b", …).

    Returns:
        Layout id string (e.g., "pfs2.season5", "pfs2.quests", "pfs2.bountiesa").
    """
    if season_number is not None:
        return f"pfs2.season{season_number}{suffix}"
    return f"pfs2.{collection_name.lower()}{suffix}"


def _build_description(
    collection_name: str,
    season_number: int | None,
    variant_index: int,
    first_scenario: str,
) -> str:
    """Construct the layout description field.

    Args:
        collection_name: Collection identifier ("5", "Quests", "Bounties").
        season_number: Season number, or None for Quests/Bounties.
        variant_index: 0-based variant index.
        first_scenario: Scenario ID of the first PDF in this variant group.

    Returns:
        Human-readable description string.
    """
    if season_number is not None:
        base = f"Season {season_number} Base Layout"
    else:
        base = f"{collection_name} Base Layout"

    if variant_index == 0:
        return base
    return f"{base} (starting {first_scenario})"


def _build_canvas(consensus: PageRegions) -> dict[str, dict[str, float | str]]:
    """Construct the canvas section of the layout JSON.

    Always includes 'page' at (0, 0, 100, 100) and 'main' (with parent 'page').
    All other non-None regions from consensus are included with parent 'main'.

    Args:
        consensus: Consensus PageRegions for this variant.

    Returns:
        Dict mapping canvas region names to their coordinate dicts.
    """
    canvas: dict[str, dict[str, float | str]] = {
        "page": {
            "x": _PAGE_COORDS[0],
            "y": _PAGE_COORDS[1],
            "x2": _PAGE_COORDS[2],
            "y2": _PAGE_COORDS[3],
        },
    }

    if consensus.main is not None:
        canvas["main"] = _coords_with_parent(consensus.main, "page")

    for region_name in _REGION_FIELDS:
        coords: CanvasCoordinates | None = getattr(consensus, region_name)
        if coords is not None:
            canvas[region_name] = _coords_with_parent(coords, "main")

    return canvas


def _coords_with_parent(
    coords: CanvasCoordinates,
    parent: str,
) -> dict[str, float | str]:
    """Convert CanvasCoordinates to a canvas entry dict with a parent field.

    Args:
        coords: The canvas coordinates.
        parent: Name of the parent canvas.

    Returns:
        Dict with 'parent', 'x', 'y', 'x2', 'y2' keys.
    """
    return {
        "parent": parent,
        "x": coords.x,
        "y": coords.y,
        "x2": coords.x2,
        "y2": coords.y2,
    }


def build_layout_json(
    collection_name: str,
    season_number: int | None,
    consensus: PageRegions,
    variant_index: int,
    first_scenario: str,
) -> dict:
    """Construct the season layout JSON structure.

    Builds the complete JSON dict with id, description, parent, and
    canvas fields following the LAYOUT_FORMAT.md specification.

    Args:
        collection_name: The collection identifier ("5", "Quests", etc.).
        season_number: The season number, or None for Quests/Bounties.
        consensus: Consensus PageRegions for this variant.
        variant_index: 0 for first variant, 1+ for subsequent.
        first_scenario: Scenario ID of the first PDF in this variant group.

    Returns:
        Dict ready for json.dumps().

    Requirements: season-layout-generator 15.1, 15.2, 15.3, 15.4, 15.5,
        15.6, 15.7, 15.8
    """
    suffix = _variant_suffix(variant_index)
    return {
        "id": _build_id(collection_name, season_number, suffix),
        "description": _build_description(
            collection_name, season_number, variant_index, first_scenario
        ),
        "parent": "pfs2",
        "canvas": _build_canvas(consensus),
    }


def build_output_path(
    output_dir: Path,
    collection_name: str,
    season_number: int | None,
    variant_index: int,
) -> Path:
    """Construct the output file path for a layout variant.

    Season paths:   {output_dir}/Season {X}/Season{X}.json
                    {output_dir}/Season {X}/Season{X}{suffix}.json
    Quests/Bounties:{output_dir}/{Collection_Name}/{Collection_Name}.json
                    {output_dir}/{Collection_Name}/{Collection_Name}{suffix}.json

    Args:
        output_dir: Base output directory.
        collection_name: The collection identifier ("5", "Quests", "Bounties").
        season_number: The season number, or None for Quests/Bounties.
        variant_index: 0 for first variant, 1+ for subsequent.

    Returns:
        Full path for the output JSON file.

    Requirements: season-layout-generator 15.9, 15.10, 15.11
    """
    suffix = _variant_suffix(variant_index)

    if season_number is not None:
        subdir = f"Season {season_number}"
        filename = f"Season{season_number}{suffix}.json"
    else:
        subdir = collection_name
        filename = f"{collection_name}{suffix}.json"

    return output_dir / subdir / filename

