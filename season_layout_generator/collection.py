"""Collection name extraction from directory names.

Determines the season number or collection name (Quests, Bounties)
from the input directory basename.
"""

import re

SEASON_PATTERN: re.Pattern[str] = re.compile(
    r"^Season\s+(\d+)$", re.IGNORECASE
)


def extract_collection_name(dir_name: str) -> tuple[str, int | None]:
    """Extract the collection name and optional season number from a directory name.

    Recognizes three patterns:
    - "Season X" where X is a positive integer → returns (str(X), X)
    - "Quests" (case-insensitive) → returns ("Quests", None)
    - "Bounties" (case-insensitive) → returns ("Bounties", None)

    Args:
        dir_name: The input directory's basename (e.g., "Season 5", "Quests").

    Returns:
        A tuple of (collection_name, season_number).
        For seasons: ("5", 5). For Quests/Bounties: ("Quests", None).

    Raises:
        ValueError: If the directory name doesn't match any known pattern.

    Requirements: season-layout-generator 2.1, 2.2, 2.3, 2.4
    """
    match = SEASON_PATTERN.match(dir_name)
    if match:
        season_number = int(match.group(1))
        if season_number < 1:
            raise ValueError(
                f"Invalid season number {season_number} in '{dir_name}'. "
                "Season number must be a positive integer."
            )
        return str(season_number), season_number

    if dir_name.lower() == "quests":
        return "Quests", None

    if dir_name.lower() == "bounties":
        return "Bounties", None

    raise ValueError(
        f"Unrecognized directory name '{dir_name}'. "
        "Expected 'Season X', 'Quests', or 'Bounties'."
    )
