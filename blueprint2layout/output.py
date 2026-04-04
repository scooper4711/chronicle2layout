"""Layout assembly and JSON output.

Assembles the final layout dictionary from resolved canvases and
resolved fields, including only the target Blueprint's own canvases
(not inherited ones), and writes the result as a JSON file with
2-space indentation.
"""

import json
from pathlib import Path

from blueprint2layout.converter import convert_to_parent_relative
from blueprint2layout.models import Blueprint, ResolvedCanvas, ResolvedField

# Styling properties to inline on content elements when non-None.
_STYLING_KEYS = (
    "font", "fontsize", "fontweight", "align",
    "color", "linewidth", "size", "lines",
)


def _generate_content_element(resolved_field: ResolvedField) -> dict:
    """Generate a single content element dict from a resolved field.

    Inlines all non-None properties directly on the element. Wraps
    in a trigger element if the field has a trigger property.

    Args:
        resolved_field: A fully resolved field.

    Returns:
        Content element dict (or trigger wrapper dict).

    Requirements: blueprint-fields 9.1, 9.2, 9.3, 9.4, 9.5, 9.7, 9.9
    """
    element: dict = {}

    if resolved_field.param is not None:
        element["value"] = f"param:{resolved_field.param}"
    elif resolved_field.value is not None:
        element["value"] = resolved_field.value

    element["type"] = resolved_field.type
    element["canvas"] = resolved_field.canvas

    for coord_key in ("x", "y", "x2", "y2"):
        coord_value = getattr(resolved_field, coord_key)
        if coord_value is not None:
            element[coord_key] = coord_value

    for style_key in _STYLING_KEYS:
        style_value = getattr(resolved_field, style_key)
        if style_value is not None:
            element[style_key] = style_value

    if resolved_field.trigger is not None:
        return {
            "type": "trigger",
            "trigger": f"param:{resolved_field.trigger}",
            "content": [element],
        }

    return element


def assemble_layout(
    blueprint: Blueprint,
    resolved_canvases: dict[str, ResolvedCanvas],
    all_canvases: dict[str, ResolvedCanvas],
    resolved_fields: list[ResolvedField] | None = None,
    merged_parameters: dict | None = None,
) -> dict:
    """Assemble the final layout dictionary.

    Extended to include parameters, defaultChronicleLocation, and
    content sections. Output section order:
    id, parent, description, flags, aspectratio,
    defaultChronicleLocation, parameters, canvas, content.

    Args:
        blueprint: The target Blueprint.
        resolved_canvases: All resolved canvases (inherited + target).
        all_canvases: Same as resolved_canvases (for parent lookups).
        resolved_fields: Resolved fields for content generation (or None).
        merged_parameters: Merged parameter dict (or None).

    Returns:
        A dictionary ready for JSON serialization.

    Requirements: chronicle-blueprints 12.1–12.5,
        blueprint-fields 9.1–9.9, 11.1–11.5
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

    if blueprint.default_chronicle_location is not None:
        layout["defaultChronicleLocation"] = blueprint.default_chronicle_location

    if merged_parameters is not None:
        layout["parameters"] = merged_parameters

    canvas_section: dict = {}
    for canvas_entry in blueprint.canvases:
        resolved = resolved_canvases[canvas_entry.name]
        canvas_section[canvas_entry.name] = convert_to_parent_relative(
            resolved, all_canvases
        )
    layout["canvas"] = canvas_section

    if resolved_fields is not None and len(resolved_fields) > 0:
        layout["content"] = [
            _generate_content_element(field) for field in resolved_fields
        ]

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
