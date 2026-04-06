"""Unit tests for layout_generator.item_segmenter module.

Tests clean_text artifact removal, segment_items with single-line and
multi-line items, parenthesis heuristics, empty input, and header
skipping.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

from __future__ import annotations

from layout_generator.item_segmenter import clean_text, segment_items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_line(text: str, y_top: float = 0.0, y_bottom: float = 5.0) -> dict:
    """Build a text line dict matching extract_text_lines output format."""
    return {
        "text": text,
        "top_left_pct": [0.0, y_top],
        "bottom_right_pct": [100.0, y_bottom],
    }


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------


class TestCleanText:
    """Tests for clean_text artifact and whitespace removal."""

    def test_trailing_uppercase_u_removed(self) -> None:
        """A trailing U after a lowercase letter is stripped."""
        assert clean_text("itemU") == "item"

    def test_trailing_u_after_uppercase_preserved(self) -> None:
        """A trailing U after an uppercase letter is kept (not an artifact)."""
        assert clean_text("GPU") == "GPU"

    def test_hair_space_removed(self) -> None:
        """Hair-space characters (U+200A) are stripped."""
        assert clean_text("hello\u200aworld") == "helloworld"

    def test_whitespace_stripped(self) -> None:
        """Leading and trailing whitespace is removed."""
        assert clean_text("  spaced  ") == "spaced"

    def test_combined_artifacts(self) -> None:
        """All cleaning steps apply together."""
        assert clean_text("  some\u200atextU  ") == "sometext"

    def test_empty_string(self) -> None:
        """An empty string returns empty."""
        assert clean_text("") == ""

    def test_only_hair_spaces(self) -> None:
        """A string of only hair spaces becomes empty."""
        assert clean_text("\u200a\u200a") == ""


# ---------------------------------------------------------------------------
# segment_items — single-line items
# ---------------------------------------------------------------------------


class TestSegmentSingleLine:
    """Tests for segment_items with single-line items."""

    def test_single_item_one_line(self) -> None:
        """A single line with balanced parens produces one item."""
        lines = [make_line("Sword (level 1) (10 gp)", 10.0, 15.0)]
        items = segment_items(lines)

        assert len(items) == 1
        assert items[0]["text"] == "Sword (level 1) (10 gp)"
        assert items[0]["y"] == 10.0
        assert items[0]["y2"] == 15.0

    def test_single_item_no_parens(self) -> None:
        """A line with no parentheses produces one item at end-of-line."""
        lines = [make_line("Simple item", 20.0, 25.0)]
        items = segment_items(lines)

        assert len(items) == 1
        assert items[0]["text"] == "Simple item"


# ---------------------------------------------------------------------------
# segment_items — multi-line items spanning parentheses
# ---------------------------------------------------------------------------


class TestSegmentMultiLine:
    """Tests for items that span multiple lines due to unbalanced parens."""

    def test_multiline_item_unbalanced_parens(self) -> None:
        """An item with an opening paren on one line continues to the next."""
        lines = [
            make_line("Potion of healing (lesser", 10.0, 15.0),
            make_line("healing) (4 gp)", 16.0, 21.0),
        ]
        items = segment_items(lines)

        assert len(items) == 1
        assert "Potion of healing" in items[0]["text"]
        assert "(4 gp)" in items[0]["text"]
        assert items[0]["y"] == 10.0
        assert items[0]["y2"] == 21.0


# ---------------------------------------------------------------------------
# segment_items — two items on consecutive lines
# ---------------------------------------------------------------------------


class TestSegmentConsecutiveItems:
    """Tests for two items on consecutive lines."""

    def test_two_items_consecutive_lines(self) -> None:
        """Two balanced lines produce two separate items."""
        lines = [
            make_line("Sword (level 1) (10 gp)", 10.0, 15.0),
            make_line("Shield (level 2) (20 gp)", 20.0, 25.0),
        ]
        items = segment_items(lines)

        assert len(items) == 2
        assert items[0]["text"] == "Sword (level 1) (10 gp)"
        assert items[1]["text"] == "Shield (level 2) (20 gp)"
        assert items[0]["y"] == 10.0
        assert items[0]["y2"] == 15.0
        assert items[1]["y2"] == 25.0


# ---------------------------------------------------------------------------
# segment_items — empty input
# ---------------------------------------------------------------------------


class TestSegmentEmpty:
    """Tests for empty and trivial inputs."""

    def test_empty_input(self) -> None:
        """An empty list produces no items."""
        assert segment_items([]) == []

    def test_whitespace_only_lines(self) -> None:
        """Lines with only whitespace produce no items."""
        lines = [make_line("   ", 0.0, 5.0)]
        assert segment_items(lines) == []


# ---------------------------------------------------------------------------
# segment_items — bare "items" header skipped
# ---------------------------------------------------------------------------


class TestSegmentHeaderSkipped:
    """Tests that bare 'items' header lines are skipped."""

    def test_bare_items_header_skipped(self) -> None:
        """A line containing 'items' (without colon) is skipped."""
        lines = [
            make_line("Items", 5.0, 10.0),
            make_line("Sword (level 1) (10 gp)", 15.0, 20.0),
        ]
        items = segment_items(lines)

        assert len(items) == 1
        assert items[0]["text"] == "Sword (level 1) (10 gp)"

    def test_items_with_colon_not_skipped(self) -> None:
        """A line containing 'items:' is NOT treated as a bare header."""
        lines = [make_line("Items: special", 5.0, 10.0)]
        items = segment_items(lines)

        assert len(items) == 1
        assert "Items: special" in items[0]["text"]


# ---------------------------------------------------------------------------
# Parenthesis heuristic — two groups force split
# ---------------------------------------------------------------------------


class TestParenthesisHeuristic:
    """Tests for the parenthesis-depth splitting heuristic."""

    def test_two_groups_force_split_mid_line(self) -> None:
        """Two closed paren groups on one line force a split; remaining
        tokens start a new item."""
        lines = [
            make_line(
                "Sword (level 1) (10 gp) Shield (level 2) (20 gp)",
                10.0,
                15.0,
            ),
        ]
        items = segment_items(lines)

        assert len(items) == 2
        assert "Sword" in items[0]["text"]
        assert "Shield" in items[1]["text"]

    def test_unbalanced_paren_continues_to_next_line(self) -> None:
        """An unbalanced opening paren causes accumulation across lines."""
        lines = [
            make_line("Elixir (of", 10.0, 15.0),
            make_line("life) (5 gp)", 16.0, 21.0),
        ]
        items = segment_items(lines)

        assert len(items) == 1
        assert "Elixir" in items[0]["text"]
        assert "(5 gp)" in items[0]["text"]

    def test_single_paren_group_no_split(self) -> None:
        """A line with only one paren group finalizes at end-of-line."""
        lines = [make_line("Potion (healing)", 10.0, 15.0)]
        items = segment_items(lines)

        assert len(items) == 1
        assert items[0]["text"] == "Potion (healing)"

    def test_three_items_on_one_line(self) -> None:
        """Three items packed on one line are split correctly."""
        lines = [
            make_line(
                "A (1) (2 gp) B (3) (4 gp) C (5) (6 gp)",
                10.0,
                15.0,
            ),
        ]
        items = segment_items(lines)

        assert len(items) == 3
        assert "A" in items[0]["text"]
        assert "B" in items[1]["text"]
        assert "C" in items[2]["text"]
