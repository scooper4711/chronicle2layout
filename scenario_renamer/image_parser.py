"""Image filename pattern extraction for scenario identification.

Parses PZOPFS and season-number patterns from image filename stems
to extract scenario identifiers and descriptive suffixes. Used during
Pass 2 to resolve image files against the scenario lookup table.

Key public items:
    ImageScenarioId: Frozen dataclass holding extracted scenario identifier.
    extract_image_scenario_id: Extract scenario ID and suffix from a stem.
"""

import re
from dataclasses import dataclass

# Matches PZOPFS prefix: PZOPFS followed by 4+ digits, optional edition letter
PZOPFS_PATTERN: re.Pattern[str] = re.compile(
    r"PZOPFS(\d{2})(\d{2})\w?", re.IGNORECASE
)

# Matches season-number pattern: X-YY anywhere in the stem
SEASON_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"(?:PFS\s*)?(\d+)-(\d{2,})"
)


@dataclass(frozen=True)
class ImageScenarioId:
    """Scenario identifier extracted from an image filename.

    Attributes:
        season: The season number.
        scenario: The zero-padded scenario number string.
        suffix: The descriptive suffix after the scenario identifier
                (e.g., "Maps", "A-Nighttime Ambush", "Map-1").
                Empty string if no suffix.
    """

    season: int
    scenario: str
    suffix: str


def extract_image_scenario_id(stem: str) -> ImageScenarioId | None:
    """Extract the scenario identifier and suffix from an image filename stem.

    Tries the PZOPFS pattern first, then the season-number pattern.
    The suffix is everything after the scenario identifier, stripped
    of leading whitespace and separators.

    Examples:
        "PZOPFS0107E Maps" → ImageScenarioId(1, "07", "Maps")
        "PZOPFS0409 A-Nighttime Ambush" → ImageScenarioId(4, "09", "A-Nighttime Ambush")
        "2-03-Map-1" → ImageScenarioId(2, "03", "Map-1")
        "PFS 2-21 Map 1" → ImageScenarioId(2, "21", "Map 1")

    Args:
        stem: The filename stem (without extension).

    Returns:
        An ImageScenarioId if a pattern matches, or None.

    Requirements: scenario-renamer 13.3, 13.4, 13.5, 13.6, 13.7
    """
    # Try PZOPFS pattern first (e.g., "PZOPFS0107E Maps")
    match = PZOPFS_PATTERN.search(stem)
    if match:
        season = int(match.group(1))
        scenario = match.group(2)
        suffix = _extract_suffix(stem, match.end())
        return ImageScenarioId(season, scenario, suffix)

    # Try season-number pattern (e.g., "2-03-Map-1", "PFS 2-21 Map 1")
    match = SEASON_NUMBER_PATTERN.search(stem)
    if match:
        season = int(match.group(1))
        scenario = match.group(2)
        suffix = _extract_suffix(stem, match.end())
        return ImageScenarioId(season, scenario, suffix)

    return None


def _extract_suffix(stem: str, match_end: int) -> str:
    """Extract the descriptive suffix from the remainder of a stem.

    Takes everything after the regex match end position and strips
    leading whitespace and leading hyphens/dashes.

    Args:
        stem: The full filename stem.
        match_end: The end position of the regex match.

    Returns:
        The cleaned suffix string, or empty string if nothing remains.
    """
    remainder = stem[match_end:]
    return remainder.lstrip(" \t-")
