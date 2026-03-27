"""Output filename construction for scenario PDFs and images.

Builds descriptive output filenames and subdirectory paths using
extracted scenario metadata. Reuses sanitize_name from the
chronicle_extractor package for consistent filename sanitization.

Key public functions:
    subdirectory_for_season: Map season number to subdirectory name.
    build_scenario_filename: Construct output filename for a scenario PDF.
    sanitize_image_suffix: Sanitize an image suffix for filename use.
    build_image_filename: Construct output filename for a scenario image.
"""

from chronicle_extractor.filename import UNSAFE_CHARACTERS, sanitize_name
from chronicle_extractor.parser import ScenarioInfo, _BOUNTY_SEASON


def subdirectory_for_season(season: int) -> str:
    """Return the subdirectory name for a given season number.

    Args:
        season: The season number. 0 for quests, -1 for bounties.

    Returns:
        "Season X" for positive seasons, "Quests" for 0, "Bounties" for -1.

    Requirements: scenario-renamer 6.1, 6.2, 6.3
    """
    if season == _BOUNTY_SEASON:
        return "Bounties"
    if season == 0:
        return "Quests"
    return f"Season {season}"


def build_scenario_filename(info: ScenarioInfo) -> str:
    """Construct the output filename for a scenario PDF (no Chronicle suffix).

    Format varies by type:
    - Scenarios: "{season}-{scenario}-{SanitizedName}.pdf"
    - Quests: "Q{scenario}-{SanitizedName}.pdf"
    - Bounties: "B{scenario}-{SanitizedName}.pdf"

    Args:
        info: The parsed scenario metadata.

    Returns:
        The constructed filename string.

    Requirements: scenario-renamer 5.1, 5.2, 5.3, 5.4
    """
    sanitized = sanitize_name(info.name)

    if info.season == _BOUNTY_SEASON:
        return f"B{info.scenario}-{sanitized}.pdf"
    if info.season == 0:
        return f"Q{info.scenario}-{sanitized}.pdf"
    return f"{info.season}-{info.scenario}-{sanitized}.pdf"


def sanitize_image_suffix(suffix: str) -> str:
    """Sanitize the image suffix for use in filenames.

    Removes spaces and unsafe characters (same rules as sanitize_name)
    while preserving hyphens as word separators.

    Args:
        suffix: The raw image suffix (e.g., "A-Nighttime Ambush",
            "Maps", "Map 1").

    Returns:
        The sanitized suffix (e.g., "A-NighttimeAmbush", "Maps", "Map1").

    Requirements: scenario-renamer 14.2
    """
    return "".join(
        ch for ch in suffix if ch != " " and ch not in UNSAFE_CHARACTERS
    )


def build_image_filename(
    season: int,
    scenario: str,
    sanitized_name: str,
    image_suffix: str,
    extension: str,
) -> str:
    """Construct the output filename for a scenario image.

    Format: "{season}-{scenario}-{SanitizedName}{SanitizedSuffix}.{ext}"

    Examples:
        (1, "07", "FloodedKingsCourt", "Maps", "pdf")
            → "1-07-FloodedKingsCourtMaps.pdf"
        (4, "09", "PerilousExperiment", "A-NighttimeAmbush", "jpg")
            → "4-09-PerilousExperimentA-NighttimeAmbush.jpg"

    Args:
        season: The season number.
        scenario: The zero-padded scenario number string.
        sanitized_name: The sanitized scenario name from the lookup table.
        image_suffix: The sanitized image suffix.
        extension: The file extension without dot (e.g., "pdf", "jpg").

    Returns:
        The constructed filename string.

    Requirements: scenario-renamer 14.1, 14.2, 14.3
    """
    return f"{season}-{scenario}-{sanitized_name}{image_suffix}.{extension}"
