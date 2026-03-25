"""File filtering predicates for scenario PDF identification.

Provides functions to determine whether a directory entry is a processable
scenario PDF: is_pdf_file, is_map_pdf, and is_scenario_pdf.
"""

import os
from pathlib import Path


def is_pdf_file(entry: os.DirEntry) -> bool:
    """Check if a directory entry is a regular file with a .pdf extension.

    Args:
        entry: A directory entry from os.scandir().

    Returns:
        True if the entry is a file with a .pdf extension (case-insensitive).

    Requirements: chronicle-extractor 2.1, 2.3
    """
    return entry.is_file() and entry.name.lower().endswith(".pdf")


def is_map_pdf(stem: str) -> bool:
    """Check if a filename stem indicates a map PDF.

    Args:
        stem: The filename without extension.

    Returns:
        True if the stem ends with 'Map' or 'Maps' (case-insensitive).

    Requirements: chronicle-extractor 2.2
    """
    lower = stem.lower()
    return lower.endswith("map") or lower.endswith("maps")


def is_scenario_pdf(entry: os.DirEntry) -> bool:
    """Check if a directory entry is a processable scenario PDF.

    Combines is_pdf_file and is_map_pdf checks.

    Args:
        entry: A directory entry from os.scandir().

    Returns:
        True if the entry is a PDF file that is not a map PDF.

    Requirements: chronicle-extractor 2.1, 2.2, 2.3
    """
    if not is_pdf_file(entry):
        return False
    stem = Path(entry.name).stem
    return not is_map_pdf(stem)
