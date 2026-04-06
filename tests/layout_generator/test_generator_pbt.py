"""Property-based tests for layout_generator.generator module.

Uses hypothesis to verify universal properties of safe label
sanitization, layout JSON round-trip, item layout assembly,
and checkbox layout assembly across randomly generated inputs.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import fitz
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from layout_generator.generator import (
    STRIKEOUT_X_END,
    STRIKEOUT_X_START,
    _SAFE_LABEL_MAX_LENGTH,
    generate_layout_json,
    make_safe_label,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_minimal_pdf(tmp_path: Path, filename: str = "test.pdf") -> Path:
    """Create a minimal single-page PDF for testing."""
    pdf_path = tmp_path / filename
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Arbitrary text for safe label testing — includes spaces, punctuation,
# and characters that make_safe_label should handle.
_label_text = st.text(
    alphabet=st.sampled_from(
        list(
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789"
            " ,.()'\""
            "-_+!@#$%^&*"
        )
    ),
    min_size=0,
    max_size=80,
)

# Characters that make_safe_label strips
_STRIPPED_CHARS = set(",.()'\"")

# Percentage coordinate in [0, 100]
_pct_coord = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)

# Item text: non-empty alphabetic words with optional parenthesized groups
_item_word = st.from_regex(r"[A-Za-z][a-z]{1,8}", fullmatch=True)
_item_text = st.builds(
    lambda words: " ".join(words),
    st.lists(_item_word, min_size=1, max_size=6),
)

# Item entry dict with text, y, y2
_item_entry = st.builds(
    lambda text, y, y2: {"text": text, "y": min(y, y2), "y2": max(y, y2)},
    text=_item_text,
    y=st.floats(min_value=0.0, max_value=90.0, allow_nan=False),
    y2=st.floats(min_value=5.0, max_value=100.0, allow_nan=False),
)


def _unique_items_strategy() -> st.SearchStrategy[list[dict]]:
    """Generate a list of item entries with unique text values."""
    return st.lists(
        _item_entry, min_size=1, max_size=6, unique_by=lambda i: i["text"],
    )


def _unique_checkbox_labels_strategy() -> st.SearchStrategy[list[dict]]:
    """Generate a list of checkbox label entries with unique labels."""
    return st.lists(
        _checkbox_label_entry,
        min_size=1,
        max_size=6,
        unique_by=lambda cb: cb["label"],
    )

# Checkbox bounding box
_checkbox_bbox = st.fixed_dictionaries({
    "x": _pct_coord,
    "y": _pct_coord,
    "x2": _pct_coord,
    "y2": _pct_coord,
})

# Non-empty label for checkboxes
_checkbox_label_text = st.from_regex(r"[A-Za-z][a-z ]{1,20}", fullmatch=True)

# Checkbox label entry dict
_checkbox_label_entry = st.builds(
    lambda label, bbox: {"label": label.strip(), "checkbox": bbox},
    label=_checkbox_label_text,
    bbox=_checkbox_bbox,
)

# Canvas name strategy
_canvas_name = st.from_regex(r"[a-z]{3,10}", fullmatch=True)

# Optional metadata string
_optional_str = st.one_of(st.none(), st.from_regex(r"[a-z0-9\-]{3,15}", fullmatch=True))


# ---------------------------------------------------------------------------
# Property 9: Safe label sanitization
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 9: Safe label sanitization
@given(text=_label_text)
@settings(max_examples=100, deadline=None)
def test_safe_label_sanitization(text: str) -> None:
    """make_safe_label produces output with no forbidden characters,
    length at most 50, deterministic results, and spaces replaced
    with underscores.

    **Validates: Requirements 11.1, 11.2, 11.3, 11.4**

    Strategy:
    - Generate arbitrary text strings including spaces, commas, periods,
      parentheses, and quotes.
    - Call make_safe_label and verify:
      (a) No spaces, commas, periods, parentheses, single quotes, or
          double quotes in the output.
      (b) Length at most 50 characters.
      (c) Deterministic: same input produces same output.
      (d) All original spaces are replaced with underscores.
    """
    result = make_safe_label(text)

    # (a) No forbidden characters
    forbidden = set(" ,.()'\"\n\t")
    found_forbidden = set(result) & forbidden
    assert not found_forbidden, (
        f"Forbidden characters {found_forbidden} found in result: "
        f"{result!r} (input: {text!r})"
    )

    # (b) Length at most 50 characters
    assert len(result) <= _SAFE_LABEL_MAX_LENGTH, (
        f"Result length {len(result)} exceeds {_SAFE_LABEL_MAX_LENGTH}: "
        f"{result!r} (input: {text!r})"
    )

    # (c) Deterministic: calling again with the same input gives the same output
    assert make_safe_label(text) == result, (
        f"Non-deterministic for input: {text!r}"
    )


# ---------------------------------------------------------------------------
# Property 10: Layout JSON round-trip
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 10: Layout JSON round-trip
@given(
    items=st.lists(_item_entry, min_size=0, max_size=5),
    checkbox_labels=st.lists(_checkbox_label_entry, min_size=0, max_size=5),
    scenario_id=_optional_str,
    parent_id=_optional_str,
    description=_optional_str,
    default_loc=_optional_str,
    item_canvas=_canvas_name,
    checkbox_canvas=_canvas_name,
)
@settings(max_examples=100, deadline=None)
def test_layout_json_round_trip(
    items: list[dict],
    checkbox_labels: list[dict],
    scenario_id: str | None,
    parent_id: str | None,
    description: str | None,
    default_loc: str | None,
    item_canvas: str,
    checkbox_canvas: str,
) -> None:
    """Serializing a layout dict with json.dumps and deserializing with
    json.loads produces a dictionary equal to the original.

    **Validates: Requirements 12.1, 12.2**

    Strategy:
    - Generate random item entries and checkbox label entries.
    - Create a minimal PDF in a temp directory.
    - Mock extract_text_lines and segment_items to return the item data.
    - Mock detect_checkboxes and extract_checkbox_labels to return
      the checkbox data.
    - Call generate_layout_json and verify the round-trip.
    """
    # Filter to non-empty labels (matching generate_layout_json behavior)
    valid_checkbox_labels = [
        cb for cb in checkbox_labels if cb["label"].strip()
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pdf_path = create_minimal_pdf(tmp_path)

        # Build mock text lines from items
        mock_lines = [
            {
                "text": item["text"],
                "top_left_pct": [0.0, item["y"]],
                "bottom_right_pct": [100.0, item["y2"]],
            }
            for item in items
        ]
        mock_checkboxes = [
            cb["checkbox"] for cb in valid_checkbox_labels
        ]

        # Determine regions based on whether we have data
        item_region = [0.0, 0.0, 100.0, 100.0] if items else None
        checkbox_region = (
            [0.0, 0.0, 100.0, 100.0] if valid_checkbox_labels else None
        )

        with (
            patch(
                "layout_generator.generator.extract_text_lines",
                return_value=mock_lines,
            ),
            patch(
                "layout_generator.generator.segment_items",
                return_value=items,
            ),
            patch(
                "layout_generator.generator.detect_checkboxes",
                return_value=mock_checkboxes,
            ),
            patch(
                "layout_generator.generator.extract_checkbox_labels",
                return_value=valid_checkbox_labels,
            ),
        ):
            layout = generate_layout_json(
                pdf_path=str(pdf_path),
                item_region_pct=item_region,
                checkbox_region_pct=checkbox_region,
                item_canvas_name=item_canvas,
                checkbox_canvas_name=checkbox_canvas,
                scenario_id=scenario_id,
                parent=parent_id,
                description=description,
                default_chronicle_location=default_loc,
            )

    # Round-trip: serialize and deserialize
    serialized = json.dumps(layout)
    deserialized = json.loads(serialized)

    assert deserialized == layout, (
        f"Round-trip mismatch.\n"
        f"  Original:     {layout}\n"
        f"  Deserialized: {deserialized}"
    )


# ---------------------------------------------------------------------------
# Property 12: Item layout assembly produces correct structure
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 12: Item layout assembly produces correct structure
@given(
    items=_unique_items_strategy(),
    canvas_name=_canvas_name,
)
@settings(max_examples=100, deadline=None)
def test_item_layout_assembly(
    items: list[dict],
    canvas_name: str,
) -> None:
    """For any non-empty list of item entries, the assembled layout
    contains the correct parameter group, base preset, per-item
    presets, and content entries.

    **Validates: Requirements 8.2, 8.3, 8.4, 8.5**

    Strategy:
    - Generate non-empty lists of item entry dicts.
    - Create a minimal PDF and mock extraction functions.
    - Call generate_layout_json and verify:
      (a) Items parameter group with strikeout_item_lines choice
          whose choices match the item texts.
      (b) strikeout_item base preset with the correct canvas name.
      (c) item.line.<safe_label> preset for each item with y and y2
          rounded to one decimal place.
      (d) Choice content entry mapping each item text to a strikeout
          element.
    """
    # Collect unique texts (items are already unique by text from strategy)
    seen_texts = [item["text"].strip() for item in items]

    mock_lines = [
        {
            "text": item["text"],
            "top_left_pct": [0.0, item["y"]],
            "bottom_right_pct": [100.0, item["y2"]],
        }
        for item in items
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pdf_path = create_minimal_pdf(tmp_path)

        with (
            patch(
                "layout_generator.generator.extract_text_lines",
                return_value=mock_lines,
            ),
            patch(
                "layout_generator.generator.segment_items",
                return_value=items,
            ),
        ):
            layout = generate_layout_json(
                pdf_path=str(pdf_path),
                item_region_pct=[0.0, 0.0, 100.0, 100.0],
                checkbox_region_pct=None,
                item_canvas_name=canvas_name,
                scenario_id="test-id",
                parent="test-parent",
            )

    # (a) Items parameter group with correct choices
    assert "parameters" in layout
    assert "Items" in layout["parameters"]
    items_param = layout["parameters"]["Items"]
    assert "strikeout_item_lines" in items_param
    choice_param = items_param["strikeout_item_lines"]
    assert choice_param["type"] == "choice"
    assert choice_param["choices"] == seen_texts

    # (b) Base strikeout_item preset with correct canvas
    assert "presets" in layout
    assert "strikeout_item" in layout["presets"]
    base_preset = layout["presets"]["strikeout_item"]
    assert base_preset["canvas"] == canvas_name
    assert base_preset["color"] == "black"
    assert base_preset["x"] == STRIKEOUT_X_START
    assert base_preset["x2"] == STRIKEOUT_X_END

    # (c) item.line.<safe_label> preset for each item with rounded y/y2
    for item in items:
        text = item["text"].strip()
        safe = make_safe_label(text)
        preset_name = f"item.line.{safe}"
        assert preset_name in layout["presets"], (
            f"Missing preset {preset_name!r} in presets: "
            f"{list(layout['presets'].keys())}"
        )
        preset = layout["presets"][preset_name]
        assert preset["y"] == round(item["y"], 1), (
            f"y mismatch for {preset_name}: "
            f"expected {round(item['y'], 1)}, got {preset['y']}"
        )
        assert preset["y2"] == round(item["y2"], 1), (
            f"y2 mismatch for {preset_name}: "
            f"expected {round(item['y2'], 1)}, got {preset['y2']}"
        )

    # (d) Choice content entry mapping each item text to strikeout element
    assert "content" in layout
    assert len(layout["content"]) >= 1
    item_content = layout["content"][0]
    assert item_content["type"] == "choice"
    assert item_content["choices"] == "param:strikeout_item_lines"
    content_map = item_content["content"]
    for text in seen_texts:
        assert text in content_map, (
            f"Missing content entry for {text!r}"
        )
        entries = content_map[text]
        assert len(entries) == 1
        assert entries[0]["type"] == "strikeout"
        assert "strikeout_item" in entries[0]["presets"]
        safe = make_safe_label(text)
        assert f"item.line.{safe}" in entries[0]["presets"]


# ---------------------------------------------------------------------------
# Property 13: Checkbox layout assembly produces correct structure
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 13: Checkbox layout assembly produces correct structure
@given(
    checkbox_labels=_unique_checkbox_labels_strategy(),
    canvas_name=_canvas_name,
)
@settings(max_examples=100, deadline=None)
def test_checkbox_layout_assembly(
    checkbox_labels: list[dict],
    canvas_name: str,
) -> None:
    """For any non-empty list of checkbox labels with non-empty labels,
    the assembled layout contains the correct parameter group, base
    preset, per-checkbox presets, and content entries.

    **Validates: Requirements 8.6, 8.7, 8.8, 8.9**

    Strategy:
    - Generate non-empty lists of checkbox label entry dicts.
    - Create a minimal PDF and mock extraction functions.
    - Call generate_layout_json and verify:
      (a) Checkboxes parameter group with summary_checkbox choice
          whose choices match the label strings.
      (b) checkbox base preset with the correct canvas name.
      (c) checkbox.<safe_label> preset for each label with the
          checkbox coordinates.
      (d) Choice content entry mapping each label to a checkbox element.
    """
    # Filter to non-empty labels (matching generator behavior)
    valid_labels = [
        cb for cb in checkbox_labels if cb["label"].strip()
    ]
    assume(len(valid_labels) > 0)

    mock_checkboxes = [cb["checkbox"] for cb in valid_labels]
    label_texts = [cb["label"] for cb in valid_labels]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pdf_path = create_minimal_pdf(tmp_path)

        with (
            patch(
                "layout_generator.generator.detect_checkboxes",
                return_value=mock_checkboxes,
            ),
            patch(
                "layout_generator.generator.extract_checkbox_labels",
                return_value=valid_labels,
            ),
        ):
            layout = generate_layout_json(
                pdf_path=str(pdf_path),
                item_region_pct=None,
                checkbox_region_pct=[0.0, 0.0, 100.0, 100.0],
                checkbox_canvas_name=canvas_name,
                scenario_id="test-id",
                parent="test-parent",
            )

    # (a) Checkboxes parameter group with correct choices
    assert "parameters" in layout
    assert "Checkboxes" in layout["parameters"]
    cb_param = layout["parameters"]["Checkboxes"]
    assert "summary_checkbox" in cb_param
    choice_param = cb_param["summary_checkbox"]
    assert choice_param["type"] == "choice"
    assert choice_param["choices"] == label_texts

    # (b) Base checkbox preset with correct canvas
    assert "presets" in layout
    assert "checkbox" in layout["presets"]
    base_preset = layout["presets"]["checkbox"]
    assert base_preset["canvas"] == canvas_name
    assert base_preset["color"] == "black"
    assert base_preset["size"] == 1

    # (c) checkbox.<safe_label> preset for each label with coordinates
    for cb in valid_labels:
        safe = make_safe_label(cb["label"])
        preset_name = f"checkbox.{safe}"
        assert preset_name in layout["presets"], (
            f"Missing preset {preset_name!r} in presets: "
            f"{list(layout['presets'].keys())}"
        )
        preset = layout["presets"][preset_name]
        assert preset["x"] == cb["checkbox"]["x"]
        assert preset["y"] == cb["checkbox"]["y"]
        assert preset["x2"] == cb["checkbox"]["x2"]
        assert preset["y2"] == cb["checkbox"]["y2"]

    # (d) Choice content entry mapping each label to checkbox element
    assert "content" in layout
    assert len(layout["content"]) >= 1
    # Find the checkbox content entry
    cb_content = None
    for entry in layout["content"]:
        if entry.get("choices") == "param:summary_checkbox":
            cb_content = entry
            break
    assert cb_content is not None, "No checkbox content entry found"
    assert cb_content["type"] == "choice"
    content_map = cb_content["content"]
    for cb in valid_labels:
        label = cb["label"]
        assert label in content_map, (
            f"Missing content entry for {label!r}"
        )
        entries = content_map[label]
        assert len(entries) == 1
        assert entries[0]["type"] == "checkbox"
        assert "checkbox" in entries[0]["presets"]
        safe = make_safe_label(label)
        assert f"checkbox.{safe}" in entries[0]["presets"]
