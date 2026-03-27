"""Text-based region detection using PyMuPDF.

Extracts text content and positional metadata from chronicle PDF
pages to identify canvas region boundaries by locating characteristic
text labels. Returns percentage-based bounding boxes for each
detected region.

The detection is label-driven: each region is identified by searching
for known text strings (e.g., "Character Name" for player_info,
"Adventure Summary" for summary). The bounding box of the matched
label is returned as a hint; the region_merge module later combines
these hints with image-based boundaries to produce final coordinates.
"""

from __future__ import annotations

import re

import fitz

from season_layout_generator.models import CanvasCoordinates


# --- Label definitions for each region ---

# Player info: top of page, contains character name and society ID fields.
_PLAYER_INFO_LABELS: list[str] = [
    "character name",
    "organized play #",
]

# Adventure summary: identified by its title bar text.
_SUMMARY_LABEL: str = "adventure summary"

# Rewards: right-side column with XP/GP fields. We look for multiple
# labels to confirm the region and derive its vertical extent.
_REWARDS_LABELS: list[str] = [
    "starting xp",
    "xp gained",
    "total xp",
    "final xp",
    "starting gp",
    "gp gained",
    "total gp",
    "gp spent",
]

# Session info: bottom of page with event/GM fields.
_SESSION_INFO_LABELS: list[str] = [
    "event code",
    "gm organized play #",
]

# Notes: identified by a standalone "Notes" label.
_NOTES_LABEL: str = "notes"

# Items: identified by a standalone "Items" label.
_ITEMS_LABEL: str = "items"

# Boons: identified by a standalone "Boons" label.
_BOONS_LABEL: str = "boons"

# Reputation: matches "Reputation", "Reputation/Infamy",
# "Reputation Gained", etc.
_REPUTATION_PATTERN: re.Pattern[str] = re.compile(
    r"^reputation(?:\s|/|$)", re.IGNORECASE
)

# Rewards header: some layouts use a vertical "REWARDS" or "Rewards"
# label as a section header instead of inline field labels.
_REWARDS_HEADER: str = "rewards"

# Minimum number of reward field labels needed to confirm the region.
_MIN_REWARDS_LABEL_MATCHES: int = 2


def _to_pct(bbox: tuple[float, float, float, float],
            width: float, height: float) -> CanvasCoordinates:
    """Convert a point-based bounding box to percentage coordinates.

    Args:
        bbox: (x0, y0, x1, y1) in PDF points.
        width: Page width in points.
        height: Page height in points.

    Returns:
        CanvasCoordinates with values in [0, 100].
    """
    return CanvasCoordinates(
        x=bbox[0] / width * 100.0,
        y=bbox[1] / height * 100.0,
        x2=bbox[2] / width * 100.0,
        y2=bbox[3] / height * 100.0,
    )


def _collect_spans(page: fitz.Page) -> tuple[
    list[tuple[str, tuple[float, float, float, float]]],
    float,
    float,
]:
    """Extract all text spans with their bounding boxes from a page.

    Args:
        page: A PyMuPDF page object.

    Returns:
        A tuple of (spans, page_width, page_height) where spans is a
        list of (text, bbox) pairs. Only non-empty stripped text is
        included.
    """
    data = page.get_text("dict")
    width: float = data["width"]
    height: float = data["height"]

    spans: list[tuple[str, tuple[float, float, float, float]]] = []
    for block in data["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if text:
                    spans.append((text, tuple(span["bbox"])))

    return spans, width, height


def _find_label(
    spans: list[tuple[str, tuple[float, float, float, float]]],
    label: str,
) -> tuple[float, float, float, float] | None:
    """Find the first span whose text matches a label (case-insensitive exact).

    Args:
        spans: List of (text, bbox) pairs.
        label: The label to search for (lowercase).

    Returns:
        The bbox of the first matching span, or None.
    """
    for text, bbox in spans:
        if text.lower() == label:
            return bbox
    return None


def _find_label_startswith(
    spans: list[tuple[str, tuple[float, float, float, float]]],
    prefix: str,
) -> tuple[float, float, float, float] | None:
    """Find the first span whose lowercase text starts with a prefix.

    Args:
        spans: List of (text, bbox) pairs.
        prefix: The prefix to match (lowercase).

    Returns:
        The bbox of the first matching span, or None.
    """
    for text, bbox in spans:
        if text.lower().startswith(prefix):
            return bbox
    return None


def _find_all_matching(
    spans: list[tuple[str, tuple[float, float, float, float]]],
    labels: list[str],
) -> list[tuple[float, float, float, float]]:
    """Find bboxes for all spans matching any label in the list.

    Each label is matched case-insensitively as an exact match.

    Args:
        spans: List of (text, bbox) pairs.
        labels: Labels to search for (lowercase).

    Returns:
        List of bboxes for all matching spans.
    """
    label_set = set(labels)
    return [bbox for text, bbox in spans if text.lower() in label_set]


def _envelope(
    bboxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    """Compute the bounding envelope of multiple bboxes.

    Args:
        bboxes: Non-empty list of (x0, y0, x1, y1) tuples.

    Returns:
        The smallest bbox containing all input bboxes.
    """
    x0 = min(b[0] for b in bboxes)
    y0 = min(b[1] for b in bboxes)
    x1 = max(b[2] for b in bboxes)
    y1 = max(b[3] for b in bboxes)
    return (x0, y0, x1, y1)


def _detect_player_info(
    spans: list[tuple[str, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float] | None:
    """Detect the player info region from characteristic labels.

    Looks for "Character Name" and "Organized Play #" labels and
    returns their combined bounding envelope.

    Args:
        spans: List of (text, bbox) pairs.

    Returns:
        Bounding box of the player info region, or None.
    """
    matches = _find_all_matching(spans, _PLAYER_INFO_LABELS)
    if not matches:
        return None
    return _envelope(matches)


def _detect_summary(
    spans: list[tuple[str, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float] | None:
    """Detect the adventure summary region.

    Looks for a span containing "Adventure Summary" text.

    Args:
        spans: List of (text, bbox) pairs.

    Returns:
        Bounding box of the summary label, or None.
    """
    return _find_label(spans, _SUMMARY_LABEL)


def _detect_rewards(
    spans: list[tuple[str, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float] | None:
    """Detect the rewards region from XP/GP field labels.

    Searches for reward-related labels (Starting XP, XP Gained, etc.)
    and returns their combined bounding envelope. Requires at least
    two matching labels to confirm the region. Also checks for a
    standalone "Rewards" header label as a fallback anchor.

    Args:
        spans: List of (text, bbox) pairs.

    Returns:
        Bounding box of the rewards region, or None.
    """
    matches = _find_all_matching(spans, _REWARDS_LABELS)
    header = _find_label(spans, _REWARDS_HEADER)

    all_bboxes = list(matches)
    if header is not None:
        all_bboxes.append(header)

    if len(matches) < _MIN_REWARDS_LABEL_MATCHES and not all_bboxes:
        return None

    if len(matches) >= _MIN_REWARDS_LABEL_MATCHES:
        return _envelope(all_bboxes)

    # Only header found without enough field labels
    if header is not None:
        return header

    return None


def _detect_session_info(
    spans: list[tuple[str, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float] | None:
    """Detect the session info region from event/GM labels.

    Looks for "EVENT CODE" and "GM Organized Play #" labels.

    Args:
        spans: List of (text, bbox) pairs.

    Returns:
        Bounding box of the session info region, or None.
    """
    matches = _find_all_matching(spans, _SESSION_INFO_LABELS)
    if not matches:
        # Fallback: look for individual labels
        event_bbox = _find_label(spans, "event")
        date_bbox = _find_label(spans, "date")
        fallbacks = [b for b in [event_bbox, date_bbox] if b is not None]
        if not fallbacks:
            return None
        return _envelope(fallbacks)
    return _envelope(matches)


def _detect_notes(
    spans: list[tuple[str, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float] | None:
    """Detect the notes region.

    Looks for a standalone "Notes" label. Ignores longer strings
    that happen to contain "notes" as a substring.

    Args:
        spans: List of (text, bbox) pairs.

    Returns:
        Bounding box of the notes label, or None.
    """
    return _find_label(spans, _NOTES_LABEL)


def _detect_items(
    spans: list[tuple[str, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float] | None:
    """Detect the items region.

    Looks for a standalone "Items" label. Ignores compound labels
    like "Items Sold" or "Items Bought".

    Args:
        spans: List of (text, bbox) pairs.

    Returns:
        Bounding box of the items label, or None.
    """
    return _find_label(spans, _ITEMS_LABEL)


def _detect_boons(
    spans: list[tuple[str, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float] | None:
    """Detect the boons region.

    Looks for a standalone "Boons" label.

    Args:
        spans: List of (text, bbox) pairs.

    Returns:
        Bounding box of the boons label, or None.
    """
    return _find_label(spans, _BOONS_LABEL)


def _detect_reputation(
    spans: list[tuple[str, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float] | None:
    """Detect the reputation region.

    Matches labels starting with "Reputation" (case-insensitive),
    covering variations like "Reputation", "Reputation/Infamy",
    and "Reputation Gained". When multiple reputation labels are
    found (e.g., three "Reputation" rows in early Bounties),
    returns their combined envelope.

    Args:
        spans: List of (text, bbox) pairs.

    Returns:
        Bounding box of the reputation region, or None.
    """
    matches = [
        bbox for text, bbox in spans
        if _REPUTATION_PATTERN.match(text)
    ]
    if not matches:
        return None
    return _envelope(matches)



def extract_text_regions(
    page: fitz.Page,
) -> dict[str, CanvasCoordinates | None]:
    """Extract region hints from PDF text content and positions.

    Uses page.get_text("dict") to get text blocks with bounding boxes.
    Identifies regions by searching for characteristic text labels:

    - player_info: "Character Name", "Organized Play #"
    - summary: "Adventure Summary"
    - rewards: "Starting XP", "XP Gained", "Total XP", "Total GP", etc.
    - session_info: "EVENT CODE", "GM Organized Play #"
    - notes: "Notes"
    - items: "Items"
    - boons: "Boons"
    - reputation: text starting with "Reputation"

    Args:
        page: A PyMuPDF page object.

    Returns:
        Dict mapping region names to detected coordinates
        (percentage-based relative to page dimensions), or None
        for undetected regions.

    Requirements: season-layout-generator 17.1, 17.2, 17.3, 17.4,
        17.5, 17.6, 17.7, 17.8
    """
    spans, width, height = _collect_spans(page)

    detectors: dict[
        str,
        tuple[float, float, float, float] | None,
    ] = {
        "player_info": _detect_player_info(spans),
        "summary": _detect_summary(spans),
        "rewards": _detect_rewards(spans),
        "session_info": _detect_session_info(spans),
        "notes": _detect_notes(spans),
        "items": _detect_items(spans),
        "boons": _detect_boons(spans),
        "reputation": _detect_reputation(spans),
    }

    return {
        name: _to_pct(bbox, width, height) if bbox is not None else None
        for name, bbox in detectors.items()
    }
