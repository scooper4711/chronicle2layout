"""File classification for scenario PDF and image identification.

Classifies files in the input directory tree as scenario PDFs,
scenario images, as-is copies, or skipped files based on extension
and filename patterns. Uses PZOPFS and season-number regex patterns
for image detection.

Key public functions:
    has_scenario_pattern: Check if a stem contains a scenario identifier.
    classify_file: Classify a file by extension and stem pattern.
"""

import re
from pathlib import Path

from chronicle_extractor.filters import is_map_pdf

# Supported image extensions (case-insensitive)
IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png"}

# PZOPFS pattern for quick stem check
PZOPFS_PREFIX: re.Pattern[str] = re.compile(r"PZOPFS\d{4}", re.IGNORECASE)

# Season-number pattern for quick stem check
SEASON_NUMBER_PREFIX: re.Pattern[str] = re.compile(r"\d+-\d{2,}")


def has_scenario_pattern(stem: str) -> bool:
    """Check if a filename stem contains a PZOPFS or season-number pattern.

    Args:
        stem: The filename stem (without extension).

    Returns:
        True if the stem contains a recognizable scenario identifier.

    Requirements: scenario-renamer 13.1, 13.3, 13.5
    """
    return bool(PZOPFS_PREFIX.search(stem) or SEASON_NUMBER_PREFIX.search(stem))


def classify_file(
    path: Path,
    input_dir: Path,
) -> tuple[str, Path]:
    """Classify a file as 'scenario_pdf', 'scenario_image', 'as_is', or 'skip'.

    Classification logic:
    - PDF files whose stem is a map pattern → 'scenario_image'
    - PDF files whose stem is not a map pattern → 'scenario_pdf'
    - JPG/PNG files with a PZOPFS or season-number pattern → 'scenario_image'
    - JPG/PNG files without a scenario pattern → 'as_is'
    - All other extensions → 'skip'

    Args:
        path: Absolute path to the file.
        input_dir: The root input directory (for relative path computation).

    Returns:
        A tuple of (classification, relative_path) where classification
        is one of 'scenario_pdf', 'scenario_image', 'as_is', or 'skip'.

    Requirements: scenario-renamer 2.1, 2.2, 2.3, 2.4, 2.5
    """
    relative_path = path.relative_to(input_dir)

    if not path.is_file():
        return ("skip", relative_path)

    ext = path.suffix.lower()
    stem = path.stem

    if ext == ".pdf":
        if is_map_pdf(stem):
            return ("scenario_image", relative_path)
        return ("scenario_pdf", relative_path)

    if ext in IMAGE_EXTENSIONS:
        if has_scenario_pattern(stem):
            return ("scenario_image", relative_path)
        return ("as_is", relative_path)

    return ("skip", relative_path)
