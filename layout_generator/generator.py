"""Core layout assembly: generate_layout_json and build helpers.

Orchestrates the full pipeline from PDF extraction through layout
assembly. Produces a leaf layout JSON dict conforming to LAYOUT_FORMAT.md
with text-based choice parameters, presets, and content entries for
item strikeouts and checkbox marks.

Requirements: layout-generator 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7,
    8.8, 8.9, 8.10, 8.11, 8.12, 11.1, 11.2, 11.3, 11.4, 14.1, 14.2, 14.3
"""

from __future__ import annotations

from pathlib import Path

from layout_generator.checkbox_extractor import (
    detect_checkboxes,
    extract_checkbox_labels,
)
from layout_generator.item_segmenter import segment_items
from layout_generator.text_extractor import extract_text_lines

STRIKEOUT_X_START: float = 0.5
"""Left x-coordinate (percentage) for item strikeout lines."""

STRIKEOUT_X_END: int = 95
"""Right x-coordinate (percentage) for item strikeout lines."""

_SAFE_LABEL_MAX_LENGTH: int = 50
"""Maximum character length for sanitized preset labels."""


def make_safe_label(text: str) -> str:
    """Create a preset-safe label from arbitrary text.

    Replaces spaces with underscores, strips commas, periods,
    parentheses, and quotes, then truncates to 50 characters.

    Args:
        text: Raw label or item text.

    Returns:
        Sanitized string for use as a preset name suffix.

    Requirements: layout-generator 11.1, 11.2, 11.3, 11.4
    """
    label = text.replace(" ", "_")
    for char in (",", ".", "(", ")", "'", '"'):
        label = label.replace(char, "")
    return label[:_SAFE_LABEL_MAX_LENGTH]


def _build_metadata(
    scenario_id: str | None,
    parent: str | None,
    description: str | None,
    default_chronicle_location: str | None,
) -> dict:
    """Build top-level metadata fields, including only non-None values."""
    layout: dict = {}
    if scenario_id is not None:
        layout["id"] = scenario_id
    if parent is not None:
        layout["parent"] = parent
    if description is not None:
        layout["description"] = description
    if default_chronicle_location is not None:
        layout["defaultChronicleLocation"] = default_chronicle_location
    return layout


def _build_items_section(
    items: list[dict],
    canvas_name: str,
) -> tuple[dict, dict, dict, dict]:
    """Build parameters, presets, and content for strikeout items.

    Returns:
        Tuple of (params, base_presets, line_presets, content_entry).
    """
    choices: list[str] = []
    base_presets: dict = {
        "strikeout_item": {
            "canvas": canvas_name,
            "color": "black",
            "x": STRIKEOUT_X_START,
            "x2": STRIKEOUT_X_END,
        },
    }
    line_presets: dict = {}
    content_map: dict = {}

    for item in items:
        text = item["text"].strip()
        if text not in choices:
            choices.append(text)
        safe = make_safe_label(text)
        preset_name = f"item.line.{safe}"
        line_presets[preset_name] = {
            "y": round(item["y"], 1),
            "y2": round(item["y2"], 1),
        }
        content_map[text] = [
            {"type": "strikeout", "presets": ["strikeout_item", preset_name]},
        ]

    params: dict = {
        "Items": {
            "strikeout_item_lines": {
                "type": "choice",
                "description": "Item line text to be struck out",
                "choices": choices,
                "example": choices[0] if choices else "",
            },
        },
    }
    content_entry: dict = {
        "type": "choice",
        "choices": "param:strikeout_item_lines",
        "content": content_map,
    }
    return params, base_presets, line_presets, content_entry


def _build_checkboxes_section(
    checkbox_labels: list[dict],
    canvas_name: str,
) -> tuple[dict, dict, dict]:
    """Build parameters, presets, and content for checkboxes.

    Returns:
        Tuple of (params, presets, content_entry).
    """
    valid_labels = [
        item["label"] for item in checkbox_labels if item["label"]
    ]
    presets: dict = {
        "checkbox": {
            "canvas": canvas_name,
            "color": "black",
            "size": 1,
        },
    }
    content_map: dict = {}

    for item in checkbox_labels:
        if not item["label"]:
            continue
        safe = make_safe_label(item["label"])
        preset_name = f"checkbox.{safe}"
        presets[preset_name] = {
            "x": item["checkbox"]["x"],
            "y": item["checkbox"]["y"],
            "x2": item["checkbox"]["x2"],
            "y2": item["checkbox"]["y2"],
        }
        content_map[item["label"]] = [
            {"type": "checkbox", "presets": ["checkbox", preset_name]},
        ]

    params: dict = {
        "Checkboxes": {
            "summary_checkbox": {
                "type": "choice",
                "description": (
                    "Checkboxes in the adventure summary "
                    "that should be selected"
                ),
                "choices": valid_labels,
                "example": valid_labels[0] if valid_labels else "",
            },
        },
    }
    content_entry: dict = {
        "type": "choice",
        "choices": "param:summary_checkbox",
        "content": content_map,
    }
    return params, presets, content_entry


def generate_layout_json(
    pdf_path: str | Path,
    item_region_pct: list[float] | None = None,
    checkbox_region_pct: list[float] | None = None,
    item_canvas_name: str = "items",
    checkbox_canvas_name: str = "summary",
    scenario_id: str | None = None,
    parent: str | None = None,
    description: str | None = None,
    default_chronicle_location: str | None = None,
) -> dict:
    """Generate a leaf layout JSON dict from a chronicle PDF.

    Orchestrates the full pipeline: text extraction, item segmentation,
    checkbox detection, label extraction, and layout assembly.

    Args:
        pdf_path: Path to the chronicle PDF.
        item_region_pct: [x0, y0, x1, y1] absolute page percentages
            for the items canvas. None skips item extraction.
        checkbox_region_pct: [x0, y0, x1, y1] absolute page percentages
            for the summary canvas. None skips checkbox detection.
        item_canvas_name: Canvas name for items (default "items").
        checkbox_canvas_name: Canvas name for checkboxes (default "summary").
        scenario_id: Layout id for the output.
        parent: Parent layout id.
        description: Layout description.
        default_chronicle_location: defaultChronicleLocation value.

    Returns:
        Layout dict conforming to LAYOUT_FORMAT.md.

    Raises:
        FileNotFoundError: If pdf_path does not exist.

    Requirements: layout-generator 8.1–8.12, 14.1, 14.2, 14.3
    """
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"Chronicle PDF not found: {pdf_path}")

    layout = _build_metadata(
        scenario_id, parent, description, default_chronicle_location,
    )

    items: list[dict] = []
    if item_region_pct is not None:
        lines = extract_text_lines(pdf_path, item_region_pct)
        items = segment_items(lines)

    checkbox_labels: list[dict] = []
    if checkbox_region_pct is not None:
        boxes = detect_checkboxes(pdf_path, checkbox_region_pct)
        if boxes:
            checkbox_labels = extract_checkbox_labels(
                pdf_path, boxes, checkbox_region_pct,
            )
            checkbox_labels = [
                cb for cb in checkbox_labels if cb["label"]
            ]

    if not items and not checkbox_labels:
        return layout

    layout["parameters"] = {}
    layout["presets"] = {}
    layout["content"] = []

    item_line_presets: dict | None = None
    if items:
        item_params, item_base, item_line_presets, item_content = (
            _build_items_section(items, item_canvas_name)
        )
        layout["parameters"].update(item_params)
        layout["presets"].update(item_base)
        layout["content"].append(item_content)

    if checkbox_labels:
        cb_params, cb_presets, cb_content = _build_checkboxes_section(
            checkbox_labels, checkbox_canvas_name,
        )
        layout["parameters"].update(cb_params)
        layout["presets"].update(cb_presets)
        layout["content"].append(cb_content)

    if item_line_presets:
        layout["presets"].update(item_line_presets)

    return layout
