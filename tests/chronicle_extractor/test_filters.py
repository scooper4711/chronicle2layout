"""Unit tests for chronicle_extractor.filters.

Tests concrete examples and edge cases for is_pdf_file, is_map_pdf,
and is_scenario_pdf predicates.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from chronicle_extractor.filters import is_map_pdf, is_pdf_file, is_scenario_pdf


def _make_dir_entry(name: str, *, is_file: bool = True) -> os.DirEntry:
    """Create a mock os.DirEntry with the given name and file status."""
    entry = MagicMock(spec=os.DirEntry)
    entry.name = name
    entry.is_file.return_value = is_file
    return entry


class TestIsPdfFile:
    """Tests for is_pdf_file predicate."""

    def test_lowercase_pdf(self) -> None:
        entry = _make_dir_entry("scenario.pdf")
        assert is_pdf_file(entry) is True

    def test_uppercase_pdf(self) -> None:
        entry = _make_dir_entry("scenario.PDF")
        assert is_pdf_file(entry) is True

    def test_mixed_case_pdf(self) -> None:
        entry = _make_dir_entry("scenario.Pdf")
        assert is_pdf_file(entry) is True

    def test_non_pdf_extension(self) -> None:
        entry = _make_dir_entry("PZOPFS0207 C2 The Foals of Szuriel.jpg")
        assert is_pdf_file(entry) is False

    def test_no_extension(self) -> None:
        entry = _make_dir_entry("README")
        assert is_pdf_file(entry) is False

    def test_directory_entry(self) -> None:
        entry = _make_dir_entry("somedir.pdf", is_file=False)
        assert is_pdf_file(entry) is False

    def test_symlink_not_file(self) -> None:
        entry = _make_dir_entry("link.pdf", is_file=False)
        assert is_pdf_file(entry) is False


class TestIsMapPdf:
    """Tests for is_map_pdf predicate."""

    def test_ends_with_maps_uppercase(self) -> None:
        assert is_map_pdf("PZOPFS0204E MAPS") is True

    def test_ends_with_map_mixed_case(self) -> None:
        assert is_map_pdf("PZOPFS0208E Map") is True

    def test_ends_with_maps_lowercase(self) -> None:
        assert is_map_pdf("some maps") is True

    def test_scenario_stem(self) -> None:
        assert is_map_pdf("PZOPFS0204E") is False

    def test_map_in_middle(self) -> None:
        assert is_map_pdf("Map of the World Extra") is False

    def test_empty_stem(self) -> None:
        assert is_map_pdf("") is False


class TestIsScenarioPdf:
    """Tests for is_scenario_pdf predicate."""

    def test_regular_scenario_pdf(self) -> None:
        entry = _make_dir_entry("PZOPFS0204E.pdf")
        assert is_scenario_pdf(entry) is True

    def test_map_pdf_excluded(self) -> None:
        entry = _make_dir_entry("PZOPFS0204E MAPS.pdf")
        assert is_scenario_pdf(entry) is False

    def test_non_pdf_excluded(self) -> None:
        entry = _make_dir_entry("PZOPFS0207 C2 The Foals of Szuriel.jpg")
        assert is_scenario_pdf(entry) is False

    def test_directory_excluded(self) -> None:
        entry = _make_dir_entry("Season 1", is_file=False)
        assert is_scenario_pdf(entry) is False

    def test_map_pdf_case_insensitive(self) -> None:
        entry = _make_dir_entry("PZOPFS0206E maps.pdf")
        assert is_scenario_pdf(entry) is False
