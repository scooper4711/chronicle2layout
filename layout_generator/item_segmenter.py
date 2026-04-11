"""Item text segmentation by parenthesis depth.

Splits extracted text lines into individual item entries using a
parenthesis-tracking heuristic. Items are finalized when two complete
parenthesis groups close with balanced parens, or at end-of-line with
balanced parens.

Requirements: layout-generator 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
"""

from __future__ import annotations

import re

MAX_PAREN_GROUPS_PER_ITEM: int = 2
"""Maximum closed parenthesis groups before forcing a split."""


def clean_text(text: str) -> str:
    """Clean extracted text by removing OCR artifacts and invisible characters.

    Strips trailing uppercase-U artifacts after lowercase letters,
    removes hair-space characters (U+200A), and strips whitespace.

    Args:
        text: Raw text from PDF extraction.

    Returns:
        Cleaned text string.

    Requirements: layout-generator 5.5
    """
    text = text.strip()
    # Remove uppercase U that trails a non-uppercase letter (OCR artifact)
    text = re.sub(r"([^A-Z])U\b", r"\1", text)
    # Remove hair-space characters
    text = text.replace("\u200a", "")
    return text.strip()


_SUBTIER_PATTERN = re.compile(r"^\d+\s*[\u2013\u2014–-]\s*\d+$")
"""Matches subtier range headers like '1–2', '3–4', '5 – 6'."""


def _is_header_line(raw_text: str) -> bool:
    """Return True if the line is a non-item header to skip.

    Skips bare "items" headers, all-uppercase labels (e.g. SUBTIER),
    and subtier range lines (e.g. '1–2', '3–4').
    """
    stripped = raw_text.strip()
    if not stripped:
        return False
    if "items" in stripped.lower() and ":" not in stripped:
        return True
    if stripped.isupper():
        return True
    if _SUBTIER_PATTERN.match(stripped):
        return True
    return False


def _finalize_tokens(
    tokens: list[str],
    items: list[dict],
    y_start: float,
    y_end: float,
) -> None:
    """Join tokens into text and append an item entry if non-empty."""
    if not tokens:
        return
    text = " ".join(tokens).strip()
    if text:
        items.append({"text": text, "y": y_start, "y2": y_end})


class _ItemAccumulator:
    """Tracks parenthesis depth and token state for the current item."""

    def __init__(self) -> None:
        self.tokens: list[str] = []
        self.open_count: int = 0
        self.groups_completed: int = 0
        self.y_start: float | None = None
        self.y_end: float | None = None

    def process_token(self, token: str) -> bool:
        """Add a token and return True if the item should be finalized."""
        self.open_count += token.count("(")
        for _ in range(token.count(")")):
            if self.open_count > 0:
                self.open_count -= 1
                self.groups_completed += 1
        self.tokens.append(token)
        return (
            self.groups_completed >= MAX_PAREN_GROUPS_PER_ITEM
            and self.open_count == 0
        )

    def is_balanced(self) -> bool:
        """Return True when parens are balanced and tokens exist."""
        return self.open_count == 0 and bool(self.tokens)

    def flush(self, items: list[dict]) -> None:
        """Finalize the current item and reset token/paren state."""
        _finalize_tokens(
            self.tokens, items, self.y_start or 0, self.y_end or 0,
        )
        self.tokens = []
        self.open_count = 0
        self.groups_completed = 0
        self.y_start = None
        self.y_end = None


def _process_line(
    line: dict,
    accumulator: _ItemAccumulator,
    items: list[dict],
) -> None:
    """Process a single text line, updating the accumulator and items list."""
    raw_text: str = line["text"]
    if _is_header_line(raw_text):
        return

    text = clean_text(raw_text)
    if not text:
        return

    line_y_top: float = line["top_left_pct"][1]
    line_y_bottom: float = line["bottom_right_pct"][1]

    if accumulator.y_start is None:
        accumulator.y_start = line_y_top
    accumulator.y_end = line_y_bottom

    tokens = text.split()
    for idx, token in enumerate(tokens):
        if accumulator.process_token(token):
            accumulator.flush(items)
            if idx < len(tokens) - 1:
                accumulator.y_start = line_y_top
                accumulator.y_end = line_y_bottom

    if accumulator.is_balanced():
        accumulator.flush(items)


def _resolve_overlapping_bounds(items: list[dict]) -> None:
    """Adjust adjacent item y-bounds so they don't overlap.

    When one item's y2 exceeds the next item's y, both are set to
    the midpoint between them.
    """
    for i in range(len(items) - 1):
        if items[i]["y2"] > items[i + 1]["y"]:
            mid = (items[i]["y2"] + items[i + 1]["y"]) / 2
            items[i]["y2"] = round(mid, 3)
            items[i + 1]["y"] = round(mid, 3)


def segment_items(lines: list[dict]) -> list[dict]:
    """Segment text lines into individual item entries.

    Streams tokens across lines, tracking parenthesis depth.
    Finalizes items when two parenthesis groups close with balanced
    parens, or at end-of-line with balanced parens. Adjacent items
    with overlapping y-bounds are adjusted to share a midpoint
    boundary.

    Args:
        lines: Text line dicts from extract_text_lines.

    Returns:
        List of item dicts with 'text', 'y', 'y2' keys.

    Requirements: layout-generator 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
    """
    items: list[dict] = []
    accumulator = _ItemAccumulator()

    for line in lines:
        _process_line(line, accumulator, items)

    # Flush remaining tokens at end of input (unbalanced at EOF)
    if accumulator.tokens:
        accumulator.flush(items)

    _resolve_overlapping_bounds(items)

    return items
