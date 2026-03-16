"""Layout JSON generation from extracted items and checkboxes.

Assembles the final layout JSON structure including parameters, presets,
and content entries for strikeout items and checkbox choices. This module
is the core transformation step that converts raw PDF extraction results
into the layout file format consumed by the chronicle generator.

Requirements: refactor-chronicle2layout 2.4, 2.5, 3.1, 4.5, 5.4, 8.4, 8.5, 10.2
"""

from __future__ import annotations

import re
from typing import Optional

from checkbox_extractor import extract_checkbox_labels, image_checkboxes
from item_segmenter import segment_items

STRIKEOUT_X_START: float = 0.5
"""Left x-coordinate (percentage) for item strikeout lines."""

STRIKEOUT_X_END: float = 95.0
"""Right x-coordinate (percentage) for item strikeout lines."""


def clean_text(text: str) -> str:
    """Clean extracted text by removing OCR artifacts and invisible characters.

    Strips leading/trailing whitespace, removes trailing uppercase-U artifacts
    that appear after lowercase letters (a common PyMuPDF extraction quirk),
    and removes hair-space characters (U+200A).

    Args:
        text: Raw text string from PDF extraction.

    Returns:
        Cleaned text string.
    """
    text = text.strip()
    text = re.sub(r"([^A-Z])U\b", r"\1", text)
    text = text.replace("\u200a", "")
    return text


def has_unmatched_parens(text: str) -> bool:
    """Check whether *text* has more opening than closing parentheses.

    Args:
        text: The string to inspect.

    Returns:
        ``True`` if the count of ``(`` exceeds the count of ``)``.
    """
    return text.count("(") > text.count(")")


def _make_safe_label(text: str) -> str:
    """Create a preset-safe label from arbitrary text.

    Truncates to 50 characters and strips characters that are invalid in
    JSON preset keys (spaces, punctuation, quotes).

    Args:
        text: Raw label or item text.

    Returns:
        Sanitized string suitable for use as a preset name suffix.
    """
    return (
        text[:50]
        .replace(" ", "_")
        .replace(",", "")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("'", "")
        .replace('"', "")
    )


def _build_metadata(
    scenario_id: Optional[str],
    description: Optional[str],
    parent: Optional[str],
    default_chronicle_location: Optional[str],
) -> dict:
    """Build the top-level metadata fields for a layout dict.

    Only includes keys whose values are truthy.

    Args:
        scenario_id: Optional layout ID (e.g. ``'5-07'``).
        description: Optional scenario description.
        parent: Optional parent layout ID.
        default_chronicle_location: Optional default PDF path.

    Returns:
        Dict with the applicable metadata keys.
    """
    layout: dict = {}
    if scenario_id:
        layout["id"] = scenario_id
    if description:
        layout["description"] = description
    if parent:
        layout["parent"] = parent
    if default_chronicle_location:
        layout["defaultChronicleLocation"] = default_chronicle_location
    return layout


def _build_items_section(
    items: list[dict],
    item_canvas_name: str,
) -> tuple[dict, dict, dict]:
    """Build parameters, presets, and content entries for strikeout items.

    Args:
        items: Segmented item dicts with ``text``, ``y``, ``y2`` keys.
        item_canvas_name: Canvas name for the items region.

    Returns:
        Tuple of (parameters_dict, presets_dict, content_entry) for items.
    """
    parameters: dict = {
        "Items": {
            "strikeout_item_lines": {
                "type": "choice",
                "description": "Item line text to be struck out",
                "choices": [],
                "example": "",
            }
        }
    }

    presets: dict = {
        "strikeout_item": {
            "canvas": item_canvas_name,
            "color": "black",
            "x": STRIKEOUT_X_START,
            "x2": STRIKEOUT_X_END,
        }
    }

    content_entry: dict = {
        "type": "choice",
        "choices": "param:strikeout_item_lines",
        "content": {},
    }

    choices = parameters["Items"]["strikeout_item_lines"]["choices"]

    for item in items:
        text = item["text"].strip()
        if text not in choices:
            choices.append(text)

        safe_text = _make_safe_label(text)
        preset_name = f"item.line.{safe_text}"
        presets[preset_name] = {
            "y": round(item["y"], 1),
            "y2": round(item["y2"], 1),
        }
        content_entry["content"][text] = [
            {"type": "strikeout", "presets": ["strikeout_item", preset_name]}
        ]

    if choices:
        parameters["Items"]["strikeout_item_lines"]["example"] = choices[0]

    return parameters, presets, content_entry


def _build_checkboxes_section(
    checkbox_labels: list[dict],
    checkbox_canvas_name: str,
) -> tuple[dict, dict, dict]:
    """Build parameters, presets, and content entries for checkboxes.

    Args:
        checkbox_labels: Label dicts with ``checkbox`` and ``label`` keys.
        checkbox_canvas_name: Canvas name for the checkbox region.

    Returns:
        Tuple of (parameters_dict, presets_dict, content_entry) for checkboxes.
    """
    valid_labels = [item["label"] for item in checkbox_labels if item["label"]]

    parameters: dict = {
        "Checkboxes": {
            "summary_checkbox": {
                "type": "choice",
                "description": "Checkboxes in the adventure summary that should be selected",
                "choices": valid_labels,
                "example": valid_labels[0] if valid_labels else "",
            }
        }
    }

    presets: dict = {
        "checkbox": {
            "canvas": checkbox_canvas_name,
            "color": "black",
            "size": 1,
        }
    }

    content_entry: dict = {
        "type": "choice",
        "choices": "param:summary_checkbox",
        "content": {},
    }

    for item in checkbox_labels:
        if not item["label"]:
            continue
        safe_label = _make_safe_label(item["label"])
        preset_name = f"checkbox.{safe_label}"
        presets[preset_name] = {
            "x": item["checkbox"]["x"],
            "y": item["checkbox"]["y"],
            "x2": item["checkbox"]["x2"],
            "y2": item["checkbox"]["y2"],
        }
        content_entry["content"][item["label"]] = [
            {"type": "checkbox", "presets": ["checkbox", preset_name]}
        ]

    return parameters, presets, content_entry


def generate_layout_json(
    pdf_path: str,
    region_pct: Optional[list[float]] = None,
    debug_dir: Optional[str] = None,
    layout_dir: Optional[str] = None,
    parent_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    description: Optional[str] = None,
    parent: Optional[str] = None,
    checkbox_region_pct: Optional[list[float]] = None,
    item_canvas_name: str = "items",
    checkbox_canvas_name: str = "summary",
    default_chronicle_location: Optional[str] = None,
) -> dict:
    """Generate a layout JSON dict with text-based choices for strikeouts.

    Orchestrates checkbox detection, text extraction, item segmentation,
    and assembly of the final layout structure. The returned dict conforms
    to the layout file format expected by the chronicle generator.

    Args:
        pdf_path: Path to the PDF file to process.
        region_pct: Region as [x0, y0, x1, y1] in percent for item extraction.
        debug_dir: Optional directory for debug output images.
        layout_dir: Base layouts directory (e.g. ``'layouts'``).
        parent_id: Parent layout ID for canvas lookup.
        scenario_id: ID for the layout (e.g. ``'5-07'``).
        description: Description of the scenario.
        parent: Parent layout ID to write to output JSON.
        checkbox_region_pct: Region as [x0, y0, x1, y1] for checkbox detection.
        item_canvas_name: Canvas name for items (default ``"items"``).
        checkbox_canvas_name: Canvas name for checkboxes (default ``"summary"``).
        default_chronicle_location: Default path to the blank chronicle PDF.

    Returns:
        Layout JSON dict with detected items and checkboxes.
    """
    # Import here to avoid circular dependency: chronicle2layout imports us,
    # and we need its extract_text_lines.
    from chronicle2layout import extract_text_lines

    layout = _build_metadata(scenario_id, description, parent, default_chronicle_location)

    # Detect checkboxes
    boxes = image_checkboxes(pdf_path, debug_dir=debug_dir, region_pct=checkbox_region_pct)
    checkbox_labels: list[dict] = []
    if boxes and checkbox_region_pct:
        checkbox_labels = extract_checkbox_labels(
            pdf_path, boxes, checkbox_region_pct, debug_dir=debug_dir
        )

    # Extract and segment items
    lines = extract_text_lines(
        pdf_path,
        region_pct=region_pct,
        debug_dir=debug_dir,
        layout_dir=layout_dir,
        parent_id=parent_id,
        canvas_name=item_canvas_name,
    )
    items = segment_items(lines)

    if not items and not checkbox_labels:
        return layout

    layout["parameters"] = {}
    layout["presets"] = {}
    layout["content"] = []

    if items:
        item_params, item_presets, item_content = _build_items_section(items, item_canvas_name)
        layout["parameters"].update(item_params)
        layout["presets"].update(item_presets)
        layout["content"].append(item_content)

    if checkbox_labels:
        cb_params, cb_presets, cb_content = _build_checkboxes_section(
            checkbox_labels, checkbox_canvas_name
        )
        layout["parameters"].update(cb_params)
        layout["presets"].update(cb_presets)
        layout["content"].append(cb_content)

    return layout
