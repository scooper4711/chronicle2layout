"""Unit tests for layout_generator helper functions.

Tests clean_text (hair space removal, trailing artifact cleanup, empty string)
and has_unmatched_parens (balanced parens, unmatched open, no parens at all).

Requirements: refactor-chronicle2layout 2.4, 2.5
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from layout_generator import (
    STRIKEOUT_X_END,
    STRIKEOUT_X_START,
    clean_text,
    has_unmatched_parens,
)


# ---------------------------------------------------------------------------
# clean_text tests
# ---------------------------------------------------------------------------

class TestCleanText:
    """Unit tests for clean_text."""

    def test_empty_string(self) -> None:
        """Empty input returns empty output."""
        assert clean_text("") == ""

    def test_whitespace_only(self) -> None:
        """Whitespace-only input returns empty string."""
        assert clean_text("   ") == ""

    def test_hair_space_removal(self) -> None:
        """Hair space characters (U+200A) are removed."""
        assert clean_text("Long\u200asword") == "Longsword"

    def test_multiple_hair_spaces(self) -> None:
        """Multiple hair spaces are all removed."""
        assert clean_text("\u200aHello\u200a World\u200a") == "Hello World"

    def test_trailing_artifact_u_after_lowercase(self) -> None:
        """Trailing uppercase U after a lowercase letter is removed."""
        assert clean_text("itemU") == "item"

    def test_trailing_artifact_u_after_uppercase_preserved(self) -> None:
        """Uppercase U after another uppercase letter is preserved."""
        assert clean_text("ITEMU") == "ITEMU"

    def test_u_in_middle_of_word_preserved(self) -> None:
        """Uppercase U that is not at a word boundary is preserved."""
        assert clean_text("Unusual") == "Unusual"

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Leading and trailing whitespace is stripped."""
        assert clean_text("  Longsword  ") == "Longsword"

    def test_normal_text_unchanged(self) -> None:
        """Normal text without artifacts passes through unchanged."""
        assert clean_text("Longsword (level 1) (1 gp)") == "Longsword (level 1) (1 gp)"


# ---------------------------------------------------------------------------
# has_unmatched_parens tests
# ---------------------------------------------------------------------------

class TestHasUnmatchedParens:
    """Unit tests for has_unmatched_parens."""

    def test_no_parens(self) -> None:
        """Text with no parentheses returns False."""
        assert has_unmatched_parens("Longsword") is False

    def test_balanced_parens(self) -> None:
        """Text with balanced parentheses returns False."""
        assert has_unmatched_parens("Longsword (level 1)") is False

    def test_multiple_balanced_groups(self) -> None:
        """Text with multiple balanced groups returns False."""
        assert has_unmatched_parens("item (level 1) (1 gp)") is False

    def test_unmatched_open(self) -> None:
        """Text with an unmatched opening paren returns True."""
        assert has_unmatched_parens("Longsword (level 1,") is True

    def test_nested_balanced(self) -> None:
        """Nested balanced parentheses return False."""
        assert has_unmatched_parens("item ((nested))") is False

    def test_extra_close_returns_false(self) -> None:
        """Extra closing parens do not count as unmatched opens."""
        assert has_unmatched_parens("item )extra)") is False

    def test_empty_string(self) -> None:
        """Empty string returns False."""
        assert has_unmatched_parens("") is False

    def test_just_open_paren(self) -> None:
        """A single open paren returns True."""
        assert has_unmatched_parens("(") is True

    def test_just_close_paren(self) -> None:
        """A single close paren returns False (no unmatched opens)."""
        assert has_unmatched_parens(")") is False


# ---------------------------------------------------------------------------
# Named constants tests
# ---------------------------------------------------------------------------

class TestNamedConstants:
    """Verify named constants have expected values."""

    def test_strikeout_x_start(self) -> None:
        assert STRIKEOUT_X_START == 0.5

    def test_strikeout_x_end(self) -> None:
        assert STRIKEOUT_X_END == 95.0
