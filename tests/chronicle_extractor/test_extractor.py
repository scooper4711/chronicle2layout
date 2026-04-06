"""Unit tests for chronicle_extractor.extractor.

Tests extract_last_page using programmatically created multi-page PDFs
via PyMuPDF. Verifies single-page output, content matching, parent
directory creation, and error handling for corrupt/missing files.

Tests process_directory using a temp directory populated with a mix of
valid scenario PDFs, map PDFs, non-PDF files, and subdirectories.
Verifies correct processing, skip messages, and output file placement.
"""

from pathlib import Path

import fitz
import pytest

from chronicle_extractor.extractor import extract_last_page, process_directory


@pytest.fixture()
def multi_page_pdf(tmp_path: Path) -> Path:
    """Create a three-page PDF with distinct text on each page."""
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} content")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestExtractLastPage:
    """Tests for extract_last_page function."""

    def test_output_has_one_page(
        self, multi_page_pdf: Path, tmp_path: Path
    ) -> None:
        output = tmp_path / "output.pdf"
        extract_last_page(multi_page_pdf, output)

        doc = fitz.open(output)
        assert len(doc) == 1
        doc.close()

    def test_output_contains_last_page_content(
        self, multi_page_pdf: Path, tmp_path: Path
    ) -> None:
        output = tmp_path / "output.pdf"
        extract_last_page(multi_page_pdf, output)

        doc = fitz.open(output)
        text = doc[0].get_text()
        assert "Page 3 content" in text
        doc.close()

    def test_output_does_not_contain_earlier_pages(
        self, multi_page_pdf: Path, tmp_path: Path
    ) -> None:
        output = tmp_path / "output.pdf"
        extract_last_page(multi_page_pdf, output)

        doc = fitz.open(output)
        text = doc[0].get_text()
        assert "Page 1 content" not in text
        assert "Page 2 content" not in text
        doc.close()

    def test_creates_parent_directories(
        self, multi_page_pdf: Path, tmp_path: Path
    ) -> None:
        output = tmp_path / "nested" / "dirs" / "output.pdf"
        extract_last_page(multi_page_pdf, output)

        assert output.exists()
        doc = fitz.open(output)
        assert len(doc) == 1
        doc.close()

    def test_single_page_pdf(self, tmp_path: Path) -> None:
        pdf_path = tmp_path / "single.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Only page")
        doc.save(str(pdf_path))
        doc.close()

        output = tmp_path / "output.pdf"
        extract_last_page(pdf_path, output)

        result = fitz.open(output)
        assert len(result) == 1
        assert "Only page" in result[0].get_text()
        result.close()

    def test_missing_pdf_raises_runtime_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.pdf"
        output = tmp_path / "output.pdf"

        with pytest.raises(RuntimeError, match="Failed to open PDF"):
            extract_last_page(missing, output)

    def test_corrupt_pdf_raises_runtime_error(self, tmp_path: Path) -> None:
        corrupt = tmp_path / "corrupt.pdf"
        corrupt.write_text("this is not a valid PDF")
        output = tmp_path / "output.pdf"

        with pytest.raises(RuntimeError, match="Failed to open PDF"):
            extract_last_page(corrupt, output)


def _create_scenario_pdf(
    path: Path, scenario_tag: str, name: str, pages: int = 6,
) -> None:
    """Create a multi-page PDF with scenario number on page 1 and running headers.

    Pages 3-5 include a "Pathfinder Society Scenario" + name running header
    to match the real PFS PDF format used by the parser.
    """
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        if i == 0:
            page.insert_text((72, 72), scenario_tag)
        elif i >= 2:
            page.insert_text((72, 36), f"{i + 1}")
            page.insert_text((72, 52), "Pathfinder Society Scenario")
            page.insert_text((72, 68), name)
            page.insert_text((72, 84), f"Body text for page {i + 1}")
        else:
            page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(str(path))
    doc.close()


@pytest.fixture()
def mixed_input_dir(tmp_path: Path) -> Path:
    """Create a temp directory with a mix of file types.

    Contents:
    - PZOPFS0107E.pdf: valid scenario PDF with #1-07 text (2 pages)
    - PZOPFS0212E.pdf: valid scenario PDF with #2-12 text (3 pages)
    - PZOPFS0204E MAPS.pdf: map PDF (should be skipped)
    - notes.txt: non-PDF file (should be skipped)
    - subdir/: subdirectory (should be skipped)
    - PZOPFS0300E.pdf: PDF with no scenario number (should warn)
    """
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    _create_scenario_pdf(
        input_dir / "PZOPFS0107E.pdf",
        "#1-07 Flooded King's Court",
        "Flooded King's Court",
    )
    _create_scenario_pdf(
        input_dir / "PZOPFS0212E.pdf",
        "#2-12 Below the Silver Tarn",
        "Below the Silver Tarn",
    )
    _create_scenario_pdf(
        input_dir / "PZOPFS0204E MAPS.pdf",
        "#2-04 Path of Kings",
        "Path of Kings",
    )
    _create_scenario_pdf(
        input_dir / "PZOPFS0300E.pdf",
        "No scenario number here",
        "No Name",
    )

    (input_dir / "notes.txt").write_text("just a text file")
    (input_dir / "subdir").mkdir()

    return input_dir


class TestProcessDirectory:
    """Tests for process_directory function."""

    def test_processes_valid_scenario_pdfs(
        self, mixed_input_dir: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "output"
        process_directory(mixed_input_dir, output_dir)

        season1 = output_dir / "season1"
        season2 = output_dir / "season2"
        assert season1.is_dir()
        assert season2.is_dir()

        s1_files = list(season1.glob("*.pdf"))
        s2_files = list(season2.glob("*.pdf"))
        assert len(s1_files) == 1
        assert "1-07" in s1_files[0].name
        assert s1_files[0].name.endswith("Chronicle.pdf")

        assert len(s2_files) == 1
        assert "2-12" in s2_files[0].name

    def test_skipped_files_produce_stderr(
        self, mixed_input_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        output_dir = tmp_path / "output"
        process_directory(mixed_input_dir, output_dir)

        captured = capsys.readouterr()
        stderr = captured.err

        # Map PDF, non-PDF file, and subdirectory should all be skipped
        assert "MAPS" in stderr
        assert "notes.txt" in stderr
        assert "subdir" in stderr

    def test_no_scenario_number_warns_stderr(
        self, mixed_input_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        output_dir = tmp_path / "output"
        process_directory(mixed_input_dir, output_dir)

        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "PZOPFS0300E.pdf" in captured.err

    def test_success_messages_on_stdout(
        self, mixed_input_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        output_dir = tmp_path / "output"
        process_directory(mixed_input_dir, output_dir)

        captured = capsys.readouterr()
        stdout = captured.out
        # Two valid scenario PDFs should produce stdout output
        assert "season1" in stdout
        assert "season2" in stdout
        assert "Chronicle.pdf" in stdout

    def test_output_pdfs_have_one_page(
        self, mixed_input_dir: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "output"
        process_directory(mixed_input_dir, output_dir)

        for pdf_path in output_dir.rglob("*.pdf"):
            doc = fitz.open(pdf_path)
            assert len(doc) == 1
            doc.close()

    def test_continues_on_per_file_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Corrupt PDF that will cause a RuntimeError
        corrupt = input_dir / "corrupt.pdf"
        corrupt.write_bytes(b"%PDF-1.4 corrupt data")

        # Valid scenario PDF
        _create_scenario_pdf(
            input_dir / "PZOPFS0101E.pdf",
            "#1-01 The Absalom Initiation",
            "The Absalom Initiation",
        )

        output_dir = tmp_path / "output"
        process_directory(input_dir, output_dir)

        captured = capsys.readouterr()
        # The corrupt file should produce an error on stderr
        assert "corrupt.pdf" in captured.err
        # The valid file should still be processed
        assert "Chronicle.pdf" in captured.out

    def test_does_not_recurse_into_subdirectories(
        self, tmp_path: Path
    ) -> None:
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        sub = input_dir / "subdir"
        sub.mkdir()

        _create_scenario_pdf(
            sub / "PZOPFS0101E.pdf",
            "#1-01 The Absalom Initiation",
            "The Absalom Initiation",
        )

        output_dir = tmp_path / "output"
        process_directory(input_dir, output_dir)

        # No output should be created since the PDF is in a subdirectory
        assert not output_dir.exists() or not list(output_dir.rglob("*.pdf"))
