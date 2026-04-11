"""Detect the game system (Pathfinder or Starfinder) from PDF text.

Classifies a scenario PDF by searching the first page text for
"Pathfinder Society" or "Starfinder Society" (case-insensitive).
Pathfinder takes precedence when both strings are present.
"""

from enum import Enum


class GameSystem(Enum):
    """Tabletop RPG system a scenario belongs to."""

    PFS = "pfs"
    SFS = "sfs"


_SYSTEM_PREFIXES = {
    GameSystem.PFS: "pfs2",
    GameSystem.SFS: "sfs2",
}


def detect_game_system(first_page_text: str) -> GameSystem | None:
    """Classify a PDF as Pathfinder or Starfinder from first page text.

    Searches for "Pathfinder Society" and "Starfinder Society"
    case-insensitively. Pathfinder takes precedence when both are present.

    Args:
        first_page_text: Text content extracted from the PDF's first page.

    Returns:
        GameSystem.PFS, GameSystem.SFS, or None if neither is found.
    """
    lowered = first_page_text.lower()
    if "pathfinder society" in lowered:
        return GameSystem.PFS
    if "starfinder society" in lowered:
        return GameSystem.SFS
    return None


def system_prefix(system: GameSystem) -> str:
    """Return the directory prefix for a game system.

    Args:
        system: The game system enum value.

    Returns:
        'pfs2' for PFS, 'sfs2' for SFS.
    """
    return _SYSTEM_PREFIXES[system]
