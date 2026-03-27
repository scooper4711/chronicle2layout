"""Unit tests for scenario_renamer.classifier.

Tests concrete examples and edge cases for has_scenario_pattern
and classify_file, covering PDF, JPG, PNG, and unsupported extensions.

Requirements: scenario-renamer 2.1, 2.2, 2.3, 2.4, 2.5, 13.1, 13.2
"""

from pathlib import Path

import pytest

from scenario_renamer.classifier import classify_file, has_scenario_pattern


def _create_file(tmp_path: Path, name: str) -> tuple[Path, Path]:
    """Create a real file in tmp_path and return (file_path, input_dir).

    Args:
        tmp_path: The pytest tmp_path fixture directory.
        name: The filename to create.

    Returns:
        A tuple of (absolute file path, input directory).
    """
    file_path = tmp_path / name
    file_path.write_bytes(b"")
    return file_path, tmp_path


class TestHasScenarioPattern:
    """Tests for has_scenario_pattern with various stems."""

    def test_pzopfs_standard(self) -> None:
        assert has_scenario_pattern("PZOPFS0107E") is True

    def test_pzopfs_with_suffix(self) -> None:
        assert has_scenario_pattern("PZOPFS0107E Maps") is True

    def test_pzopfs_lowercase(self) -> None:
        assert has_scenario_pattern("pzopfs0409") is True

    def test_season_number_pattern(self) -> None:
        assert has_scenario_pattern("2-03-Map-1") is True

    def test_pfs_season_number_pattern(self) -> None:
        assert has_scenario_pattern("PFS 2-21 Map 1") is True

    def test_no_pattern_plain_word(self) -> None:
        assert has_scenario_pattern("random-photo") is False

    def test_no_pattern_single_digit_after_dash(self) -> None:
        # "1-3" has only one digit after the dash — not a season-number pattern
        assert has_scenario_pattern("photo-1-3") is False

    def test_empty_stem(self) -> None:
        assert has_scenario_pattern("") is False

    def test_pzopfs_ambush_suffix(self) -> None:
        assert has_scenario_pattern("PZOPFS0409 A-Nighttime Ambush") is True


class TestClassifyFilePdf:
    """Tests for classify_file with PDF files."""

    def test_scenario_pdf(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "PZOPFS0107E.pdf")
        classification, rel = classify_file(file_path, input_dir)
        assert classification == "scenario_pdf"
        assert rel == Path("PZOPFS0107E.pdf")

    def test_map_pdf_classified_as_scenario_image(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "PZOPFS0107E Maps.pdf")
        classification, rel = classify_file(file_path, input_dir)
        assert classification == "scenario_image"
        assert rel == Path("PZOPFS0107E Maps.pdf")

    def test_map_pdf_singular(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "PZOPFS0208E Map.pdf")
        classification, _ = classify_file(file_path, input_dir)
        assert classification == "scenario_image"

    def test_uppercase_pdf_extension(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "PZOPFS0101E.PDF")
        classification, _ = classify_file(file_path, input_dir)
        assert classification == "scenario_pdf"


class TestClassifyFileImage:
    """Tests for classify_file with JPG and PNG image files."""

    def test_jpg_with_season_number_pattern(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "2-03-Map-1.jpg")
        classification, rel = classify_file(file_path, input_dir)
        assert classification == "scenario_image"
        assert rel == Path("2-03-Map-1.jpg")

    def test_jpg_with_pzopfs_pattern(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(
            tmp_path, "PZOPFS0409 A-Nighttime Ambush.jpg"
        )
        classification, _ = classify_file(file_path, input_dir)
        assert classification == "scenario_image"

    def test_jpg_with_pfs_season_number(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "PFS 2-21 Map 1.jpg")
        classification, _ = classify_file(file_path, input_dir)
        assert classification == "scenario_image"

    def test_jpg_without_scenario_pattern(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "random-photo.jpg")
        classification, rel = classify_file(file_path, input_dir)
        assert classification == "as_is"
        assert rel == Path("random-photo.jpg")

    def test_png_with_scenario_pattern(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "PZOPFS0107E Maps.png")
        classification, _ = classify_file(file_path, input_dir)
        assert classification == "scenario_image"

    def test_png_without_scenario_pattern(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "random.png")
        classification, _ = classify_file(file_path, input_dir)
        assert classification == "as_is"


class TestClassifyFileSkip:
    """Tests for classify_file with unsupported extensions and non-files."""

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        file_path, input_dir = _create_file(tmp_path, "notes.txt")
        classification, rel = classify_file(file_path, input_dir)
        assert classification == "skip"
        assert rel == Path("notes.txt")

    def test_directory_returns_skip(self, tmp_path: Path) -> None:
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()
        classification, rel = classify_file(dir_path, tmp_path)
        assert classification == "skip"
        assert rel == Path("subdir")


class TestClassifyFileRelativePath:
    """Tests that classify_file computes relative_path correctly."""

    def test_nested_file_relative_path(self, tmp_path: Path) -> None:
        nested_dir = tmp_path / "Season 1"
        nested_dir.mkdir()
        file_path = nested_dir / "PZOPFS0101E.pdf"
        file_path.write_bytes(b"")
        _, rel = classify_file(file_path, tmp_path)
        assert rel == Path("Season 1") / "PZOPFS0101E.pdf"
