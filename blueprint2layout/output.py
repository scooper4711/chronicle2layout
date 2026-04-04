"""Layout assembly and JSON output.

Assembles the final layout dictionary from resolved canvases, including
only the target Blueprint's own canvases (not inherited ones), and
writes the result as a JSON file with 2-space indentation.
"""

import json
from pathlib import Path

from blueprint2layout.converter import convert_to_parent_relative
from blueprint2layout.models import Blueprint, ResolvedCanvas


def assemble_layout(
    blueprint: Blueprint,
    resolved_canvases: dict[str, ResolvedCanvas],
    all_canvases: dict[str, ResolvedCanvas],
) -> dict:
    """Assemble the final layout dictionary.

    Builds the layout.json structure with id, optional parent,
    and canvas section containing only the target Blueprint's
    own canvases (not inherited ones), converted to parent-relative
    percentages.

    Args:
        blueprint: The target Blueprint.
        resolved_canvases: All resolved canvases (inherited + target).
        all_canvases: Same as resolved_canvases (for parent lookups).

    Returns:
        A dictionary ready for JSON serialization.

    Requirements: chronicle-blueprints 12.1, 12.2, 12.3, 12.4, 12.5
    """
    layout: dict = {"id": blueprint.id}

    if blueprint.parent is not None:
        layout["parent"] = blueprint.parent
    if blueprint.description is not None:
        layout["description"] = blueprint.description
    if blueprint.flags:
        layout["flags"] = blueprint.flags
    if blueprint.aspectratio is not None:
        layout["aspectratio"] = blueprint.aspectratio

    canvas_section: dict = {}
    for canvas_entry in blueprint.canvases:
        resolved = resolved_canvases[canvas_entry.name]
        canvas_section[canvas_entry.name] = convert_to_parent_relative(
            resolved, all_canvases
        )

    layout["canvas"] = canvas_section
    return layout


def write_layout(layout: dict, output_path: Path) -> None:
    """Write a layout dictionary to a JSON file with 2-space indent.

    Args:
        layout: The assembled layout dictionary.
        output_path: Path to write the JSON file.

    Requirements: chronicle-blueprints 12.6, 12.7, 12.8
    """
    output_path = Path(output_path)
    output_path.write_text(json.dumps(layout, indent=2))
