"""Filename construction for chronicle PDF output.

Provides sanitize_name for stripping unsafe characters and spaces from
scenario names, and build_output_path for constructing the full output
path with season-based subdirectories.
"""

from pathlib import Path

from chronicle_extractor.parser import ScenarioInfo, _BOUNTY_SEASON

UNSAFE_CHARACTERS: str = "':;?/\\*<>|\",\u2019"


def sanitize_name(name: str) -> str:
    """Remove spaces and unsafe characters from a scenario name.

    Preserves original letter casing. Strips characters defined in
    UNSAFE_CHARACTERS and removes all spaces.

    Args:
        name: The raw scenario name from the PDF.

    Returns:
        The sanitized name suitable for use in filenames.

    Requirements: chronicle-extractor 5.2, 5.3, 5.4
    """
    return "".join(ch for ch in name if ch != " " and ch not in UNSAFE_CHARACTERS)


def build_output_path(output_dir: Path, info: ScenarioInfo) -> Path:
    """Construct the full output path for a chronicle PDF.

    For scenarios: output_dir/Season {season}/{season}-{scenario}-{sanitized}Chronicle.pdf
    For quests (season=0): output_dir/Quests/Q{scenario}-{sanitized}Chronicle.pdf

    Args:
        output_dir: The base output directory.
        info: The parsed scenario metadata.

    Returns:
        The full Path where the chronicle PDF should be saved.

    Requirements: chronicle-extractor 4.2, 5.1
    """
    sanitized = sanitize_name(info.name)

    if info.season == _BOUNTY_SEASON:
        filename = f"B{info.scenario}-{sanitized}Chronicle.pdf"
        return output_dir / "Bounties" / filename

    if info.season == 0:
        filename = f"Q{info.scenario}-{sanitized}Chronicle.pdf"
        return output_dir / "Quests" / filename

    filename = f"{info.season}-{info.scenario}-{sanitized}Chronicle.pdf"
    return output_dir / f"Season {info.season}" / filename
