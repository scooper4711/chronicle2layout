"""Unit tests for item_segmenter.finalize_buffer and segment_items.

Tests item segmentation with empty input, single-line items, multi-line items
with unmatched parentheses, items with exactly 2 parenthesis groups, bare
"items" header skipping, and buffer finalization edge cases.

Requirements: refactor-chronicle2layout 2.2
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from item_segmenter import MAX_PAREN_GROUPS_PER_ITEM, finalize_buffer, segment_items


# ---------------------------------------------------------------------------
# Helper to build line dicts matching extract_text_lines output shape
# ---------------------------------------------------------------------------

def _line(text: str, y_top: float = 0.0, y_bottom: float = 5.0) -> dict:
    """Create a text-line dict matching the shape returned by extract_text_lines."""
    return {
        "text": text,
        "top_left_pct": [0.0, y_top],
        "bottom_right_pct": [100.0, y_bottom],
    }


# ---------------------------------------------------------------------------
# finalize_buffer tests
# ---------------------------------------------------------------------------

class TestFinalizeBuffer:
    """Unit tests for finalize_buffer."""

    def test_empty_buffer_does_nothing(self) -> None:
        """An empty token list produces no item."""
        items: list[dict] = []
        finalize_buffer([], items, 0.0, 5.0)
        assert items == []

    def test_whitespace_only_buffer_does_nothing(self) -> None:
        """Tokens that join to only whitespace produce no item."""
        items: list[dict] = []
        finalize_buffer(["", " ", ""], items, 0.0, 5.0)
        assert items == []

    def test_buffer_with_content_appends_item(self) -> None:
        """Tokens with real content produce a single item dict."""
        items: list[dict] = []
        finalize_buffer(["Longsword", "(1gp)"], items, 10.0, 15.0)
        assert len(items) == 1
        assert items[0] == {"text": "Longsword (1gp)", "y": 10.0, "y2": 15.0}

    def test_buffer_preserves_existing_items(self) -> None:
        """Finalizing appends to the accumulator without clearing it."""
        items: list[dict] = [{"text": "existing", "y": 0.0, "y2": 5.0}]
        finalize_buffer(["new", "item"], items, 20.0, 25.0)
        assert len(items) == 2
        assert items[1]["text"] == "new item"


# ---------------------------------------------------------------------------
# segment_items tests
# ---------------------------------------------------------------------------

class TestSegmentItems:
    """Unit tests for segment_items."""

    def test_empty_input_returns_empty_list(self) -> None:
        """No lines produces no items."""
        assert segment_items([]) == []

    def test_single_line_item_no_parens(self) -> None:
        """A single line without parentheses produces one item."""
        lines = [_line("Longsword")]
        result = segment_items(lines)
        assert len(result) == 1
        assert result[0]["text"] == "Longsword"

    def test_single_line_item_with_one_paren_group(self) -> None:
        """A single line with one parenthesis group produces one item."""
        lines = [_line("Longsword (1 gp)")]
        result = segment_items(lines)
        assert len(result) == 1
        assert result[0]["text"] == "Longsword (1 gp)"

    def test_single_line_with_two_paren_groups_splits(self) -> None:
        """A line with exactly 2 paren groups finalizes after the second group."""
        lines = [_line("Longsword (level 1) (1 gp) Shield (level 1) (2 gp)")]
        result = segment_items(lines)
        assert len(result) == 2
        assert "Longsword" in result[0]["text"]
        assert "(1 gp)" in result[0]["text"]
        assert "Shield" in result[1]["text"]
        assert "(2 gp)" in result[1]["text"]

    def test_multi_line_item_with_unmatched_parens(self) -> None:
        """Unmatched parens cause tokens to span across lines."""
        lines = [
            _line("Longsword (level 1,", y_top=10.0, y_bottom=15.0),
            _line("uncommon) (1 gp)", y_top=16.0, y_bottom=21.0),
        ]
        result = segment_items(lines)
        # The open paren on line 1 keeps accumulating until balanced on line 2,
        # then the second group "(1 gp)" triggers finalization.
        assert len(result) == 1
        assert "Longsword" in result[0]["text"]
        assert "uncommon)" in result[0]["text"]
        assert "(1 gp)" in result[0]["text"]
        # Vertical extent spans both lines
        assert result[0]["y"] == 10.0
        assert result[0]["y2"] == 21.0

    def test_bare_items_header_is_skipped(self) -> None:
        """A line containing just 'Items' (no colon) is skipped."""
        lines = [
            _line("Items"),
            _line("Longsword (1 gp)"),
        ]
        result = segment_items(lines)
        assert len(result) == 1
        assert result[0]["text"] == "Longsword (1 gp)"

    def test_items_header_with_colon_is_not_skipped(self) -> None:
        """A line containing 'Items:' (with colon) is NOT skipped."""
        lines = [_line("Items: Longsword (1 gp)")]
        result = segment_items(lines)
        assert len(result) == 1
        assert "Items:" in result[0]["text"]

    def test_multiple_separate_items(self) -> None:
        """Multiple single-line items on separate lines produce separate items."""
        lines = [
            _line("Longsword (1 gp)", y_top=10.0, y_bottom=15.0),
            _line("Shield (2 gp)", y_top=20.0, y_bottom=25.0),
        ]
        result = segment_items(lines)
        assert len(result) == 2
        assert result[0]["text"] == "Longsword (1 gp)"
        assert result[1]["text"] == "Shield (2 gp)"

    def test_y_coordinates_are_preserved(self) -> None:
        """Item y and y2 reflect the line's vertical position."""
        lines = [_line("Potion (5 gp)", y_top=30.0, y_bottom=35.0)]
        result = segment_items(lines)
        assert result[0]["y"] == 30.0
        assert result[0]["y2"] == 35.0

    def test_hair_space_is_removed(self) -> None:
        """Hair space characters (\\u200a) are cleaned from item text."""
        lines = [_line("Long\u200asword (1 gp)")]
        result = segment_items(lines)
        assert "\u200a" not in result[0]["text"]

    def test_trailing_artifact_u_is_removed(self) -> None:
        """Trailing uppercase U artifact after lowercase letter is removed."""
        lines = [_line("itemU (1 gp)")]
        result = segment_items(lines)
        # The trailing U after lowercase 'm' should be stripped
        assert result[0]["text"] == "item (1 gp)"

    def test_empty_text_lines_are_skipped(self) -> None:
        """Lines with empty or whitespace-only text produce no items."""
        lines = [_line(""), _line("   "), _line("Sword (1 gp)")]
        result = segment_items(lines)
        assert len(result) == 1
        assert result[0]["text"] == "Sword (1 gp)"

    def test_max_paren_groups_constant(self) -> None:
        """MAX_PAREN_GROUPS_PER_ITEM is 2."""
        assert MAX_PAREN_GROUPS_PER_ITEM == 2

    def test_unbalanced_parens_at_eof_flushes_remaining(self) -> None:
        """Tokens with unbalanced parens at end-of-input are still flushed."""
        lines = [_line("Broken item (missing close")]
        result = segment_items(lines)
        assert len(result) == 1
        assert "Broken item" in result[0]["text"]
        assert "(missing close" in result[0]["text"]
