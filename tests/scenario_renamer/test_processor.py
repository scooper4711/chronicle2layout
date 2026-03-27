"""Unit tests for scenario_renamer.processor module.

Tests scan_and_classify, copy_as_is, process_scenario_image,
and process_directory using tmp_path fixtures with synthetic files.

Requirements: scenario-renamer 3.1, 3.2, 3.3, 4.1, 7.1, 7.2, 7.3,
    12.1, 12.2, 12.3, 12.4, 15.1, 15.2, 15.3, 16.1, 16.5
"""

from pathlib import Path

import fitz

from scenario_renamer.processor import (
    copy_as_is,
    process_directory,
    process_scenario_image,
    scan_and_classify,
)


def _create_file(path: Path, content: str = "dummy") -> Path:
    """Create a file with the given content, ensuring parent dirs exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _create_scenario_pdf(path: Path, season: int, scenario: str, name: str) -> Path:
    """Create a multi-page PDF with a chronicle-style last page.

    The last page contains a '#X-YY Name' line followed by
    'Adventure Summary', which extract_from_chronicle can parse.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    # First page (content page)
    doc.new_page()
    # Last page (chronicle sheet)
    chronicle = doc.new_page()
    chronicle.insert_text((72, 72), f"#{season}-{scenario}: {name}")
    chronicle.insert_text((72, 100), "Adventure Summary")
    doc.save(str(path))
    doc.close()
    return path


class TestScanAndClassify:
    """Tests for scan_and_classify with mixed file types."""

    def test_classifies_mixed_files(self, tmp_path: Path) -> None:
        """Verify PDFs, patterned images, plain images, and txt are classified."""
        _create_file(tmp_path / "PZOPFS0101E.pdf", "pdf-data")
        _create_file(tmp_path / "PZOPFS0107E Maps.jpg", "image-data")
        _create_file(tmp_path / "notes.txt", "some notes")
        _create_file(tmp_path / "random-photo.png", "png-data")

        pdfs, images, as_is = scan_and_classify(tmp_path)

        assert len(pdfs) == 1
        assert pdfs[0].name == "PZOPFS0101E.pdf"

        assert len(images) == 1
        assert images[0].name == "PZOPFS0107E Maps.jpg"

        # .png without pattern → as_is; .txt → skip (not in any list)
        assert len(as_is) == 1
        assert as_is[0].name == "random-photo.png"


class TestCopyAsIs:
    """Tests for copy_as_is preserving relative path."""

    def test_preserves_nested_relative_path(self, tmp_path: Path) -> None:
        """File in a nested subdirectory is copied to the same relative path."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        source = _create_file(
            input_dir / "sub" / "deep" / "file.png", "content-abc"
        )

        result = copy_as_is(source, input_dir, output_dir)

        expected = output_dir / "sub" / "deep" / "file.png"
        assert result == expected
        assert result.exists()
        assert result.read_text() == "content-abc"


class TestProcessScenarioImage:
    """Tests for process_scenario_image with various lookup states."""

    def test_populated_lookup_renames_correctly(self, tmp_path: Path) -> None:
        """Image with a matching lookup entry is renamed and placed in season dir."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        _create_file(input_dir / "PZOPFS0107E Maps.jpg", "img-data")

        lookup = {(1, "07"): "FloodedKingsCourt"}
        process_scenario_image(
            input_dir / "PZOPFS0107E Maps.jpg",
            input_dir,
            output_dir,
            lookup,
        )

        expected = output_dir / "Season 1" / "1-07-FloodedKingsCourtMaps.jpg"
        assert expected.exists()
        assert expected.read_text() == "img-data"

    def test_unresolved_lookup_copies_as_is(self, tmp_path: Path) -> None:
        """Image with no matching lookup entry is copied as-is."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        _create_file(input_dir / "PZOPFS9999 Maps.jpg", "img-data")

        process_scenario_image(
            input_dir / "PZOPFS9999 Maps.jpg",
            input_dir,
            output_dir,
            lookup={},
        )

        as_is_path = output_dir / "PZOPFS9999 Maps.jpg"
        assert as_is_path.exists()
        assert as_is_path.read_text() == "img-data"

    def test_no_pattern_copies_as_is(self, tmp_path: Path) -> None:
        """Image without a PZOPFS or season-number pattern is copied as-is."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        _create_file(input_dir / "random-photo.jpg", "photo-data")

        process_scenario_image(
            input_dir / "random-photo.jpg",
            input_dir,
            output_dir,
            lookup={},
        )

        as_is_path = output_dir / "random-photo.jpg"
        assert as_is_path.exists()
        assert as_is_path.read_text() == "photo-data"


class TestProcessDirectory:
    """End-to-end test for process_directory with mixed file types."""

    def test_end_to_end_mixed_directory(self, tmp_path: Path) -> None:
        """Verify output structure with a PDF, patterned image, plain image, and txt."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        # Scenario PDF with extractable chronicle info
        _create_scenario_pdf(
            input_dir / "scenario.pdf",
            season=1, scenario="01", name="The Absalom Initiation",
        )

        # Scenario image (PZOPFS pattern)
        _create_file(input_dir / "PZOPFS0101E Maps.jpg", "map-data")

        # Plain PNG without pattern → as-is
        _create_file(input_dir / "photo.png", "png-data")

        # .txt → skipped entirely
        _create_file(input_dir / "notes.txt", "text")

        process_directory(input_dir, output_dir)

        # PDF should be renamed into Season 1
        season1 = output_dir / "Season 1"
        assert season1.exists()
        pdf_files = list(season1.glob("1-01-*.pdf"))
        assert len(pdf_files) == 1
        assert "TheAbsalomInitiation" in pdf_files[0].name

        # Image should be renamed using lookup from the PDF
        image_files = list(season1.glob("1-01-*Maps.jpg"))
        assert len(image_files) == 1

        # Plain PNG copied as-is
        assert (output_dir / "photo.png").exists()

        # .txt should NOT appear in output
        assert not (output_dir / "notes.txt").exists()
