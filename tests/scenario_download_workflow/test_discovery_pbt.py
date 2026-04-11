"""Property-based tests for scenario_download_workflow.discovery.

Uses hypothesis to verify universal properties of PDF discovery
across randomly generated filesystem entries.
"""

import os
import tempfile
import time
from datetime import timedelta
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from scenario_download_workflow.discovery import discover_recent_pdfs

_PDF_EXTENSIONS = [".pdf", ".PDF", ".Pdf", ".pDf", ".pdF"]
_NON_PDF_EXTENSIONS = [".txt", ".csv", ".png", ".doc", ".xlsx", ""]

_ALL_EXTENSIONS = _PDF_EXTENSIONS + _NON_PDF_EXTENSIONS


@st.composite
def filesystem_entry(draw: st.DrawFn) -> dict:
    """Generate a random filesystem entry descriptor.

    Returns a dict with:
        name: base filename (no extension)
        extension: file extension (may or may not be .pdf)
        is_dir: whether this entry is a directory
        seconds_ago: how many seconds ago the mtime should be set
    """
    name = draw(
        st.text(
            st.characters(
                whitelist_categories=("L", "N"),
                min_codepoint=ord("a"),
                max_codepoint=ord("z"),
            ),
            min_size=1,
            max_size=10,
        )
    )
    extension = draw(st.sampled_from(_ALL_EXTENSIONS))
    is_dir = draw(st.booleans())
    seconds_ago = draw(st.floats(min_value=0, max_value=7200))
    return {
        "name": name,
        "extension": extension,
        "is_dir": is_dir,
        "seconds_ago": seconds_ago,
    }


def _create_entry(
    base_dir: Path, entry: dict
) -> Path:
    """Create a filesystem entry from a descriptor and return its path."""
    full_name = entry["name"] + entry["extension"]
    path = base_dir / full_name
    if entry["is_dir"]:
        path.mkdir(exist_ok=True)
    else:
        path.touch(exist_ok=True)
        target_time = time.time() - entry["seconds_ago"]
        os.utime(path, (target_time, target_time))
    return path


def _is_matching_pdf(entry: dict, window_seconds: float) -> bool:
    """Check if an entry should appear in discovery results."""
    if entry["is_dir"]:
        return False
    if entry["extension"].lower() != ".pdf":
        return False
    return entry["seconds_ago"] <= window_seconds


# Feature: scenario-download-workflow, Property 2: PDF discovery filters by extension and recency
@settings(max_examples=200)
@given(
    entries=st.lists(filesystem_entry(), min_size=0, max_size=15),
    window_minutes=st.integers(min_value=1, max_value=120),
)
def test_discovery_returns_exactly_matching_pdfs_sorted(
    entries: list[dict],
    window_minutes: int,
) -> None:
    """For any set of filesystem entries and any positive recency window,
    discover_recent_pdfs returns exactly the regular files with .pdf
    extension (case-insensitive) modified within the window, sorted
    alphabetically by filename.

    Validates: Requirements 2.1, 2.2, 2.3, 2.4
    """
    window = timedelta(minutes=window_minutes)
    window_seconds = window.total_seconds()

    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)

        # Deduplicate entries by case-insensitive full name to avoid
        # collisions on case-insensitive filesystems (e.g. macOS HFS+)
        seen_names: set[str] = set()
        unique_entries: list[dict] = []
        for entry in entries:
            full_name = entry["name"] + entry["extension"]
            key = full_name.lower()
            if key not in seen_names:
                seen_names.add(key)
                unique_entries.append(entry)

        # Create filesystem entries
        for entry in unique_entries:
            _create_entry(base_dir, entry)

        # Run discovery
        result = discover_recent_pdfs(base_dir, window)

        # Compute expected set of matching filenames
        expected_names = sorted(
            entry["name"] + entry["extension"]
            for entry in unique_entries
            if _is_matching_pdf(entry, window_seconds)
        )

        result_names = [p.name for p in result]

        # Property: result contains exactly the matching files
        assert result_names == expected_names, (
            f"Expected {expected_names}, got {result_names}"
        )

        # Property: result is sorted alphabetically by filename
        assert result_names == sorted(result_names), (
            f"Result not sorted: {result_names}"
        )
