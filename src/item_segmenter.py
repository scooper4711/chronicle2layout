"""Item segmentation for chronicle text extraction.

Splits extracted text lines into individual item entries using parenthesis-based
heuristics. The algorithm streams tokens across lines and finalizes an item when:

- Two complete parenthesis groups have been seen and parens are balanced, OR
- End-of-line is reached with balanced parentheses.

This handles multi-line items where parenthesized content (e.g. level ranges,
gold values) spans across line breaks in the PDF text extraction.

Requirements: refactor-chronicle2layout 2.2, 4.3, 8.2, 8.4, 8.5
"""

from __future__ import annotations

import re

MAX_PAREN_GROUPS_PER_ITEM: int = 2
"""Maximum number of fully closed parenthesis groups allowed per item
before forcing a split."""


def finalize_buffer(
    item_tokens: list[str],
    items_accum: list[dict],
    y_start: float,
    y_end: float,
) -> None:
    """Flush accumulated tokens into a completed item entry.

    Joins the token list into a single text string and appends a new item
    dict to *items_accum*. Does nothing when *item_tokens* is empty or
    contains only whitespace.

    Args:
        item_tokens: Words collected for the current item.
        items_accum: Accumulator list that receives the new item dict.
        y_start: Top y-coordinate of the item as a percentage of the region.
        y_end: Bottom y-coordinate of the item as a percentage of the region.
    """
    if not item_tokens:
        return
    text = " ".join(item_tokens).strip()
    if text:
        items_accum.append({"text": text, "y": y_start, "y2": y_end})


def _clean_line_text(text: str) -> str:
    """Clean a single line of extracted text for segmentation.

    Removes trailing uppercase-U artifacts, hair-space characters, and
    leading/trailing whitespace. This is the same cleaning applied by the
    original inline ``clean_text`` helper inside ``generate_layout_json``.

    Args:
        text: Raw text string from PDF extraction.

    Returns:
        Cleaned text ready for tokenization.
    """
    text = text.strip()
    # Fix artifact: remove uppercase U unless preceded by uppercase letter
    text = re.sub(r"([^A-Z])U\b", r"\1", text)
    # Remove hair space character (\u200a)
    text = text.replace("\u200a", "")
    return text


class _ItemAccumulator:
    """Tracks state while accumulating tokens into items."""

    def __init__(self) -> None:
        self.tokens: list[str] = []
        self.open_count: int = 0
        self.groups_completed: int = 0
        self.y_start: float | None = None
        self.y_end: float | None = None

    def process_token(self, tok: str) -> bool:
        """Add a token and return True if the item should be finalized."""
        opens = tok.count("(")
        closes = tok.count(")")
        self.open_count += opens
        for _ in range(closes):
            if self.open_count > 0:
                self.open_count -= 1
                self.groups_completed += 1
        self.tokens.append(tok)
        return self.groups_completed >= MAX_PAREN_GROUPS_PER_ITEM and self.open_count == 0

    def is_balanced(self) -> bool:
        return self.open_count == 0 and bool(self.tokens)

    def flush(self, items: list[dict]) -> None:
        """Finalize the current item and reset state."""
        finalize_buffer(self.tokens, items, self.y_start or 0, self.y_end or 0)
        self.tokens = []
        self.open_count = 0
        self.groups_completed = 0

    def reset_position(self) -> None:
        """Reset vertical position tracking for a new item."""
        self.y_start = None
        self.y_end = None


def segment_items(lines: list[dict]) -> list[dict]:
    """Segment extracted text lines into individual item entries.

    Streams tokens across *lines*, tracking parenthesis depth to decide
    where one item ends and the next begins. The heuristic rules are:

    1. Continue accumulating tokens while parentheses are unbalanced.
    2. A single item never contains more than
       :data:`MAX_PAREN_GROUPS_PER_ITEM` fully closed parenthesis groups.
    3. After the maximum number of groups is reached with balanced parens,
       the current item is finalized and remaining tokens start a new item.
    4. At end-of-line, if parentheses are balanced the item is finalized.

    Lines whose text (lowercased) matches a bare ``"items"`` header (no
    colon) are skipped.

    Args:
        lines: List of text-line dicts as returned by
            :func:`extract_text_lines`. Each dict must contain ``text``
            (str), ``top_left_pct`` ([x, y]), and ``bottom_right_pct``
            ([x, y]).

    Returns:
        List of item dicts, each with keys ``text`` (str), ``y`` (float),
        and ``y2`` (float) representing the cleaned item text and its
        vertical extent as region percentages.
    """
    items: list[dict] = []
    acc = _ItemAccumulator()

    for line in lines:
        raw_line_text: str = line["text"]
        # Skip bare "items" header lines
        if "items" in raw_line_text.lower() and ":" not in raw_line_text:
            continue

        text = _clean_line_text(raw_line_text)
        if not text:
            continue

        tokens = text.split()
        line_y_top: float = line["top_left_pct"][1]
        line_y_bottom: float = line["bottom_right_pct"][1]

        # Initialize current item vertical bounds
        if acc.y_start is None:
            acc.y_start = line_y_top
        acc.y_end = line_y_bottom

        for tok in tokens:
            should_split = acc.process_token(tok)
            if should_split:
                acc.flush(items)
                acc.y_start = line_y_top
                acc.y_end = line_y_bottom

        # End-of-line: finalize if balanced
        if acc.is_balanced():
            acc.flush(items)
            acc.reset_position()
        # Else continue to next line to complete parentheses

    # Flush any remaining tokens (unbalanced at EOF)
    if acc.tokens:
        acc.flush(items)

    return items
