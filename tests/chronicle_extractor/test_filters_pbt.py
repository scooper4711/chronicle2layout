"""Property-based tests for chronicle_extractor.filters.

Uses hypothesis to verify universal properties of file filtering
predicates across randomly generated inputs.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

from hypothesis import given
from hypothesis import strategies as st

from chronicle_extractor.filters import is_map_pdf, is_pdf_file


def _make_dir_entry(name: str, *, is_file: bool = True) -> os.DirEntry:
    """Create a mock os.DirEntry with the given name and file status."""
    entry = MagicMock(spec=os.DirEntry)
    entry.name = name
    entry.is_file.return_value = is_file
    return entry


# Feature: chronicle-extractor, Property 1: PDF extension filtering
@given(name=st.text(min_size=1, max_size=50))
def test_pdf_extension_filtering(name: str) -> None:
    """is_pdf_file returns True iff the entry is a file with .pdf extension.

    Validates: Requirements 2.1
    """
    entry = _make_dir_entry(name, is_file=True)
    expected = name.lower().endswith(".pdf")
    assert is_pdf_file(entry) is expected, (
        f"is_pdf_file({name!r}) returned {not expected}, expected {expected}"
    )

    # Non-file entries should always return False regardless of name
    non_file = _make_dir_entry(name, is_file=False)
    assert is_pdf_file(non_file) is False, "Non-file entries should return False"


# Feature: chronicle-extractor, Property 2: Map PDF detection
@given(stem=st.text(min_size=0, max_size=50))
def test_map_pdf_detection(stem: str) -> None:
    """is_map_pdf returns True iff stem ends with 'Map' or 'Maps' (case-insensitive).

    Validates: Requirements 2.2
    """
    lower = stem.lower()
    expected = lower.endswith("map") or lower.endswith("maps")
    assert is_map_pdf(stem) is expected, (
        f"is_map_pdf({stem!r}) returned {not expected}, expected {expected}"
    )
