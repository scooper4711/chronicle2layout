"""Fill-in blank extraction for leaf layout generation.

Finds underscore runs (player fill-in blanks) in the chronicle text,
derives human-readable field names from surrounding words, assigns each
blank to its containing canvas, and estimates font size from the text.

Unlike structural detection, every run qualifies regardless of width:
leaf content is per-chronicle, so no shared index can shift.
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from layout_generator.checkbox_extractor import CHECKBOX_CHARS

FILLIN_MIN_RUN_LENGTH = 3
RUN_PATTERN = re.compile(r"_{3,}")

# Whole-word delimiters bounding a field name (case-insensitive).
WORD_DELIMITERS = {"or", "and"}

# Sentence punctuation delimiters (colon deliberately excluded: labels
# like "Adventure Completed:" keep their colon-stripped form instead).
PUNCT_DELIMITERS = {".", ",", ";"}

# Bracket pairs around blanks: closers bound the name, openers are
# transparent so "(_____) or" still names from behind when needed.
_CLOSERS = {")", "]", "}"}
_OPENERS = {"(", "[", "{"}


def _is_bare_opener(text: str) -> bool:
    """Check whether text is only opening brackets."""
    stripped = text.strip()
    return bool(stripped) and all(char in _OPENERS for char in stripped)

# Characters stripped from token ends (parens kept out of names but do
# not stop the scan, so "adopted a pet (" still yields "adopted a pet").
STRIP_CHARS = "()\"'.,!?;:\u2014\u2013-\u2022\u25e6\u00b7"

MAX_FORWARD_WORDS = 2
MAX_BACKWARD_WORDS = 3
MAX_NAME_CHARS = 60


def _strip_token(token: str) -> str:
    """Remove checkbox glyphs and surrounding punctuation from a token."""
    for char in CHECKBOX_CHARS:
        token = token.replace(char, "")
    return token.strip().strip(STRIP_CHARS).strip()


def _is_word_delimiter(token: str) -> bool:
    """Check whether a cleaned token is a word boundary."""
    return token.lower() in WORD_DELIMITERS


def _has_checkbox_char(token: str) -> bool:
    """Check whether the raw token contains a checkbox glyph."""
    return any(char in token for char in CHECKBOX_CHARS)


def _ends_sentence(token: str) -> bool:
    """Check whether the raw token ends with sentence punctuation."""
    stripped = token.strip()
    return bool(stripped) and stripped[-1] in PUNCT_DELIMITERS


def _scan_tokens(tokens: list[str], limit: int) -> list[str]:
    """Collect name words until a boundary token.

    Opening brackets are transparent (a parenthesized blank still takes
    its name from outside the parens); closing brackets, word
    delimiters, checkbox glyphs, and sentence punctuation stop the scan.
    """
    words: list[str] = []
    for token in tokens:
        stripped = token.strip()
        if _has_checkbox_char(token):
            cleaned = _strip_token(token)
            if cleaned:
                words.append(cleaned)
            break
        if stripped in _CLOSERS or stripped in PUNCT_DELIMITERS:
            break
        if stripped[:1] in _CLOSERS or stripped[:1] in PUNCT_DELIMITERS:
            # Closer/sentence punct glued to the next word still bounds.
            break
        cleaned = _strip_token(token)
        if not cleaned:
            continue
        if _is_word_delimiter(cleaned):
            break
        words.append(cleaned)
        if _ends_sentence(token):
            break
        if len(words) >= limit:
            break
    return words


def derive_fillin_name(before: list[str], after: list[str]) -> str | None:
    """Derive a field name from tokens around an underscore run.

    Takes up to the first words after the run; when nothing usable
    follows, takes up to the last words before the run instead.

    Args:
        before: Line tokens before the run, in reading order.
        after: Line tokens after the run, in reading order.

    Returns:
        The field name, or None when neither side yields words.
    """
    forward = _scan_tokens(after, MAX_FORWARD_WORDS)
    if forward:
        return " ".join(forward)[:MAX_NAME_CHARS].rstrip()
    backward = _scan_tokens(list(reversed(before))[:25], MAX_BACKWARD_WORDS)
    if not backward:
        return None
    return " ".join(reversed(backward))[:MAX_NAME_CHARS].rstrip()


def _unique_names(names: list[str]) -> list[str]:
    """Deduplicate field names, suffixing repeats with _2, _3, ..."""
    seen: dict[str, int] = {}
    unique: list[str] = []
    for name in names:
        count = seen.get(name, 0) + 1
        seen[name] = count
        unique.append(name if count == 1 else f"{name}_{count}")
    return unique


def _deepest_canvas(
    x: float,
    y: float,
    canvas_rects: dict[str, list[float]],
) -> str | None:
    """Find the smallest-area canvas containing a point (percentages)."""
    best: str | None = None
    best_area: float | None = None
    for name in sorted(canvas_rects):
        x0, y0, x1, y1 = canvas_rects[name]
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        area = (x1 - x0) * (y1 - y0)
        if best_area is None or area < best_area:
            best = name
            best_area = area
    return best


def extract_fillins(
    pdf_path: str | Path,
    canvas_rects: dict[str, list[float]],
    label_overrides: dict[str, str] | None = None,
) -> list[dict]:
    """Extract fill-in blanks from the chronicle's last page.

    Args:
        pdf_path: Path to the chronicle PDF.
        canvas_rects: Map of canvas names to absolute page percentage
            rects ([x0, y0, x1, y1]) from the parent layout chain.
        label_overrides: Map of derived names to replacement lead text,
            applied before deduplication.

    Returns:
        List of dicts with name, canvas, x, y, x2, y2 (canvas-relative
        percentages), and fontsize. Blanks outside every canvas or
        without a derivable name are skipped.
    """
    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        return []
    if doc.page_count == 0:
        doc.close()
        return []

    page = doc[doc.page_count - 1]
    page_width = page.rect.width
    page_height = page.rect.height
    words = page.get_text("words")

    # Word indexes holding underscore runs, in reading order.
    run_indexes = [
        idx for idx, word in enumerate(words)
        if RUN_PATTERN.search(word[4])
    ]

    raw: list[dict] = []
    for pos, idx in enumerate(run_indexes):
        prev_idx = run_indexes[pos - 1] if pos > 0 else -1
        next_idx = (
            run_indexes[pos + 1] if pos + 1 < len(run_indexes) else len(words)
        )
        before, after, run_box = _split_context(words, idx, prev_idx, next_idx)
        name = derive_fillin_name(before, after)
        if not name:
            continue
        if label_overrides and name in label_overrides:
            name = label_overrides[name]
        x0, x1 = run_box
        _, word_y0, _, word_y1 = words[idx][0:4]
        span_size = _run_font_size(page, (x0 + x1) / 2, (word_y0 + word_y1) / 2)
        raw.append(
            {
                "name": name,
                "bbox": [x0, word_y0, x1, word_y1],
                "fontsize": span_size,
            }
        )
    doc.close()

    names = _unique_names([entry["name"] for entry in raw])
    fillins: list[dict] = []
    for entry, name in zip(raw, names):
        x0, y0, x1, y1 = entry["bbox"]
        cx = (x0 + x1) / 2 / page_width * 100
        cy = (y0 + y1) / 2 / page_height * 100
        canvas = _deepest_canvas(cx, cy, canvas_rects)
        if canvas is None:
            continue
        rx0, ry0, rx1, ry1 = canvas_rects[canvas]
        fillins.append(
            {
                "name": name,
                "canvas": canvas,
                "x": round((x0 / page_width * 100 - rx0) / (rx1 - rx0) * 100, 1),
                "y": round((y0 / page_height * 100 - ry0) / (ry1 - ry0) * 100, 1),
                "x2": round((x1 / page_width * 100 - rx0) / (rx1 - rx0) * 100, 1),
                "y2": round((y1 / page_height * 100 - ry0) / (ry1 - ry0) * 100, 1),
                "fontsize": entry["fontsize"],
            }
        )
    return fillins


def _run_box(word: tuple, run_len: int) -> tuple[float, float]:
    """Locate an underscore run inside its word via proportional offset.

    Mirrors the checkbox glyph positioning: characters are assumed
    evenly spaced across the word box.
    """
    x0, _, x1, _, text = word[0], word[1], word[2], word[3], word[4]
    start = text.find("_" * run_len)
    char_width = (x1 - x0) / len(text)
    return (x0 + char_width * start, x0 + char_width * (start + run_len))


def _split_context(
    words: list[tuple],
    idx: int,
    prev_idx: int,
    next_idx: int,
) -> tuple[list[str], list[str], tuple[float, float]]:
    """Split surrounding words into before/after lists around a run.

    Context is bounded by the neighboring run words and restricted to
    the run's own row: words only qualify when their box overlaps the
    run word's box vertically, so adjacent lines never leak in. A word
    overlapping the run contributes its non-underscore flanks.

    Returns:
        Tuple of (before tokens, after tokens, (run_x0, run_x1)).
    """
    run_word = words[idx]
    run_text: str = run_word[4]
    match = RUN_PATTERN.search(run_text)
    run_len = len(match.group(0)) if match else 0
    run_x0, run_x1 = _run_box(run_word, run_len)
    _, run_y0, _, run_y1 = run_word[0:4]

    def overlaps(row: tuple) -> bool:
        return row[1] < run_y1 and row[3] > run_y0

    before: list[str] = []
    for other in words[prev_idx + 1 : idx]:
        if not overlaps(other):
            continue
        before.append(other[4])
    # The run word's own left flank belongs to the before side,
    # unless it is a bare opener (which must not block the
    # previous-row fallback).
    if match and match.start() > 0:
        flank = run_text[: match.start()].replace("_", "")
        if flank and not _is_bare_opener(flank):
            before.append(flank)
    if not before:
        # The run may open its row with the label trailing on the
        # previous row; fall back to that row's tail.
        above = [w for w in words[:idx] if w[3] <= run_y0]
        if above:
            nearest = max(w[3] for w in above)
            before = [w[4] for w in above if w[3] >= nearest - 2.0]

    after: list[str] = []
    if match and match.end() < len(run_text):
        flank = run_text[match.end() :].replace("_", "")
        if flank and not _is_bare_opener(flank):
            after.append(flank)
    for other in words[idx + 1 : next_idx]:
        if not overlaps(other):
            continue
        after.append(other[4])
    return before, after, (run_x0, run_x1)


def _run_font_size(page, run_cx: float, run_cy: float) -> int:
    """Read the font size of the span containing a point."""
    for block in page.get_text("rawdict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                x0, y0, x1, y1 = span.get("bbox", [0, 0, 0, 0])
                if x0 <= run_cx <= x1 and y0 <= run_cy <= y1:
                    return int(round(float(span.get("size", 10))))
    return 10
