"""Property-based tests for layout_generator.item_segmenter module.

Uses hypothesis to verify universal properties of item segmentation
and text cleaning across randomly generated inputs.
"""

from __future__ import annotations

import re

from hypothesis import given, settings, assume
from hypothesis import strategies as st

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


def collect_cleaned_tokens(lines: list[dict]) -> list[str]:
    """Extract all non-empty tokens from lines after cleaning, skipping headers."""
    tokens: list[str] = []
    for line in lines:
        raw = line["text"]
        if "items" in raw.lower() and ":" not in raw:
            continue
        cleaned = clean_text(raw)
        if not cleaned:
            continue
        tokens.extend(cleaned.split())
    return tokens


def collect_output_tokens(items: list[dict]) -> list[str]:
    """Extract all tokens from segmented item entries."""
    tokens: list[str] = []
    for item in items:
        tokens.extend(item["text"].split())
    return tokens


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Word tokens: alphanumeric with optional parentheses mixed in.
# Avoid generating bare "items" text or empty strings.
_safe_word = st.from_regex(r"[a-z][a-z0-9]{0,7}", fullmatch=True)

# A parenthesized group like "(level 3)" or "(10 gp)"
_paren_group = st.builds(
    lambda w: f"({w})",
    _safe_word,
)

# A token is either a plain word or a parenthesized group
_token = st.one_of(_safe_word, _paren_group)

# Build a line's text from a list of tokens joined by spaces
_line_text = st.lists(_token, min_size=1, max_size=6).map(" ".join)


def _text_lines_strategy() -> st.SearchStrategy[list[dict]]:
    """Generate a list of text line dicts with incrementing y-coordinates.

    Lines are guaranteed to NOT be bare "items" headers and NOT be empty
    after cleaning.
    """
    return st.lists(
        _line_text,
        min_size=1,
        max_size=8,
    ).map(
        lambda texts: [
            make_line(text, y_top=float(i * 10), y_bottom=float(i * 10 + 5))
            for i, text in enumerate(texts)
        ]
    )


# ---------------------------------------------------------------------------
# Property 5: Item segmentation preserves all non-header tokens
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 5: Item segmentation preserves all non-header tokens
@given(lines=_text_lines_strategy())
@settings(max_examples=100, deadline=None)
def test_segmentation_preserves_tokens(lines: list[dict]) -> None:
    """The concatenation of all tokens from segmented items equals the
    concatenation of all cleaned tokens from the input lines.

    Validates: Requirements 5.1, 5.2, 5.3, 5.4

    Strategy:
    - Generate lists of text line dicts with random tokens (avoiding
      bare "items" headers and empty lines).
    - Run segment_items on them.
    - Collect all tokens from input (after clean_text) and all tokens
      from output items.
    - Verify they match — no text is lost or invented during segmentation.
    """
    input_tokens = collect_cleaned_tokens(lines)
    assume(len(input_tokens) > 0)

    items = segment_items(lines)
    output_tokens = collect_output_tokens(items)

    assert output_tokens == input_tokens, (
        f"Token mismatch.\n"
        f"  Input tokens:  {input_tokens}\n"
        f"  Output tokens: {output_tokens}"
    )


# ---------------------------------------------------------------------------
# Strategies for Property 6
# ---------------------------------------------------------------------------

# Arbitrary text that may include hair spaces and trailing-U artifacts.
_hair_space = st.just("\u200a")
_trailing_u_artifact = st.builds(
    lambda prefix: prefix + "U",
    st.from_regex(r"[a-z]{1,5}", fullmatch=True),
)

# Build strings that mix normal text, hair spaces, and U-artifacts
_artifact_text = st.one_of(
    st.text(
        alphabet=st.sampled_from(
            list("abcdefghijklmnopqrstuvwxyz \u200aABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        ),
        min_size=0,
        max_size=40,
    ),
    _trailing_u_artifact,
    st.builds(
        lambda parts: "".join(parts),
        st.lists(
            st.one_of(
                st.from_regex(r"[a-z]{1,4}", fullmatch=True),
                _hair_space,
                st.just("U"),
                st.just(" "),
            ),
            min_size=1,
            max_size=10,
        ),
    ),
)


# ---------------------------------------------------------------------------
# Property 6: Text cleaning removes artifacts and hair spaces
# ---------------------------------------------------------------------------


# Feature: layout-generator, Property 6: Text cleaning removes artifacts and hair spaces
@given(text=_artifact_text)
@settings(max_examples=100, deadline=None)
def test_clean_text_removes_artifacts(text: str) -> None:
    """clean_text produces output with no hair spaces, no trailing-U
    artifacts after lowercase letters, and no leading/trailing whitespace.

    Validates: Requirements 5.5

    Strategy:
    - Generate arbitrary strings including hair spaces (U+200A) and
      trailing uppercase-U artifacts after lowercase letters.
    - Run clean_text.
    - Verify:
      (a) No hair-space characters remain.
      (b) No trailing uppercase-U artifacts after lowercase letters
          (pattern: [a-z]U at a word boundary).
      (c) No leading or trailing whitespace.
    """
    result = clean_text(text)

    # (a) No hair-space characters
    assert "\u200a" not in result, (
        f"Hair space found in result: {result!r} (input: {text!r})"
    )

    # (b) No trailing-U artifacts: a lowercase letter followed by U at
    #     a word boundary should not appear.
    trailing_u_matches = re.findall(r"[a-z]U\b", result)
    assert not trailing_u_matches, (
        f"Trailing-U artifact found: {trailing_u_matches} "
        f"in result: {result!r} (input: {text!r})"
    )

    # (c) No leading or trailing whitespace
    assert result == result.strip(), (
        f"Leading/trailing whitespace in result: {result!r} (input: {text!r})"
    )
