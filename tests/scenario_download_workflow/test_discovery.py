"""Unit tests for scenario_download_workflow.discovery.

Tests concrete examples and edge cases for discover_recent_pdfs.
"""

import os
from datetime import timedelta
from pathlib import Path

import pytest

from scenario_download_workflow.discovery import discover_recent_pdfs


def _set_mtime_seconds_ago(path: Path, seconds_ago: float) -> None:
    """Set a file's modification time to `seconds_ago` seconds in the past."""
    import time

    target = time.time() - seconds_ago
    os.utime(path, (target, target))


class TestEmptyAndNoMatches:
    """Tests for directories with no matching PDFs."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert result == []

    def test_no_pdf_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").touch()
        (tmp_path / "data.csv").touch()
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert result == []

    def test_all_pdfs_too_old(self, tmp_path: Path) -> None:
        pdf = tmp_path / "old.pdf"
        pdf.touch()
        _set_mtime_seconds_ago(pdf, 7200)  # 2 hours ago
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert result == []


class TestExtensionMatching:
    """Tests for case-insensitive .pdf extension matching."""

    def test_lowercase_pdf(self, tmp_path: Path) -> None:
        (tmp_path / "scenario.pdf").touch()
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert len(result) == 1
        assert result[0].name == "scenario.pdf"

    def test_uppercase_pdf(self, tmp_path: Path) -> None:
        (tmp_path / "scenario.PDF").touch()
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert len(result) == 1
        assert result[0].name == "scenario.PDF"

    def test_mixed_case_pdf(self, tmp_path: Path) -> None:
        (tmp_path / "scenario.Pdf").touch()
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert len(result) == 1
        assert result[0].name == "scenario.Pdf"

    def test_mixed_file_types(self, tmp_path: Path) -> None:
        (tmp_path / "scenario.pdf").touch()
        (tmp_path / "readme.txt").touch()
        (tmp_path / "image.png").touch()
        (tmp_path / "another.PDF").touch()
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert len(result) == 2


class TestRecencyBoundary:
    """Tests for recency window boundary conditions."""

    def test_just_inside_window(self, tmp_path: Path) -> None:
        pdf = tmp_path / "recent.pdf"
        pdf.touch()
        _set_mtime_seconds_ago(pdf, 3500)  # ~58 min ago, within 1h
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert len(result) == 1

    def test_just_outside_window(self, tmp_path: Path) -> None:
        pdf = tmp_path / "old.pdf"
        pdf.touch()
        _set_mtime_seconds_ago(pdf, 3700)  # ~62 min ago, outside 1h
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert result == []


class TestSubdirectoryExclusion:
    """Tests that subdirectories are not scanned."""

    def test_pdf_in_subdirectory_excluded(self, tmp_path: Path) -> None:
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.pdf").touch()
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert result == []

    def test_directory_with_pdf_suffix_excluded(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "tricky.pdf"
        fake_dir.mkdir()
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        assert result == []


class TestSortOrder:
    """Tests that results are sorted alphabetically by filename."""

    def test_alphabetical_sort(self, tmp_path: Path) -> None:
        (tmp_path / "charlie.pdf").touch()
        (tmp_path / "alpha.pdf").touch()
        (tmp_path / "bravo.pdf").touch()
        result = discover_recent_pdfs(tmp_path, timedelta(hours=1))
        names = [p.name for p in result]
        assert names == ["alpha.pdf", "bravo.pdf", "charlie.pdf"]
