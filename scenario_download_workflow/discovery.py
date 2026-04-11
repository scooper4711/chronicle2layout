"""Discover recently modified PDF files in a directory.

Scans the top level of a directory for PDF files modified within a
given recency window. No recursive scanning into subdirectories.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path


def discover_recent_pdfs(
    downloads_dir: Path,
    recency_window: timedelta,
) -> list[Path]:
    """Return PDF files in downloads_dir modified within recency_window.

    Scans only the top level (no recursion). Matches .pdf extension
    case-insensitively. Returns results sorted alphabetically by filename.

    Args:
        downloads_dir: Directory to scan for PDF files.
        recency_window: Maximum age of a file's modification time.

    Returns:
        List of Path objects for matching PDFs, sorted by filename.
    """
    cutoff = datetime.now(tz=timezone.utc) - recency_window
    recent_pdfs: list[Path] = []

    for entry in downloads_dir.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() != ".pdf":
            continue
        mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
        if mtime >= cutoff:
            recent_pdfs.append(entry)

    return sorted(recent_pdfs, key=lambda p: p.name)
