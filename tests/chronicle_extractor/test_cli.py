"""CLI integration tests for chronicle_extractor.__main__.

Tests argument parsing, input directory validation, output directory
creation, and end-to-end processing with fixture PDFs.
"""

from pathlib import Path

import fitz
import pytest

from chronicle_extractor.__main__ import main, parse_args


def _create_scenario_pdf(
    path: Path, scenario_tag: str, name: str, pages: int = 6,
) -> None:
    """Create a multi-page PDF with scenario number on page 1 and running headers."""
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


class TestParseArgs:
    """Tests for parse_args function."""

    def test_returns_path_objects(self) -> None:
        args = parse_args(["--input-dir", "/tmp/in", "--output-dir", "/tmp/out"])
        assert isinstance(args.input_dir, Path)
        assert isinstance(args.output_dir, Path)

    def test_parses_input_and_output_dirs(self) -> None:
        args = parse_args(["--input-dir", "src", "--output-dir", "dest"])
        assert args.input_dir == Path("src")
        assert args.output_dir == Path("dest")

    def test_missing_input_dir_raises(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--output-dir", "/tmp/out"])

    def test_missing_output_dir_raises(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--input-dir", "/tmp/in"])


class TestMainMissingInputDir:
    """Tests for main when input directory does not exist."""

    def test_exits_with_code_1(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        code = main(["--input-dir", str(missing), "--output-dir", str(tmp_path / "out")])
        assert code == 1

    def test_prints_error_to_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "nonexistent"
        main(["--input-dir", str(missing), "--output-dir", str(tmp_path / "out")])
        captured = capsys.readouterr()
        assert "does not exist" in captured.err


class TestMainOutputDirCreation:
    """Tests for main creating the output directory."""

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "nested" / "output"

        main(["--input-dir", str(input_dir), "--output-dir", str(output_dir)])
        assert output_dir.is_dir()

    def test_returns_zero_on_success(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        code = main(["--input-dir", str(input_dir), "--output-dir", str(output_dir)])
        assert code == 0


class TestMainEndToEnd:
    """End-to-end tests for main with fixture PDFs."""

    @pytest.fixture()
    def scenario_dir(self, tmp_path: Path) -> Path:
        """Create a temp directory with scenario PDFs for end-to-end testing."""
        input_dir = tmp_path / "scenarios"
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
        return input_dir

    def test_produces_chronicle_pdfs(
        self, scenario_dir: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "output"
        code = main(["--input-dir", str(scenario_dir), "--output-dir", str(output_dir)])

        assert code == 0
        chronicles = list(output_dir.rglob("*Chronicle.pdf"))
        assert len(chronicles) == 2

    def test_organizes_by_season(
        self, scenario_dir: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "output"
        main(["--input-dir", str(scenario_dir), "--output-dir", str(output_dir)])

        assert (output_dir / "season1").is_dir()
        assert (output_dir / "season2").is_dir()

    def test_chronicle_pdfs_have_one_page(
        self, scenario_dir: Path, tmp_path: Path
    ) -> None:
        output_dir = tmp_path / "output"
        main(["--input-dir", str(scenario_dir), "--output-dir", str(output_dir)])

        for pdf_path in output_dir.rglob("*.pdf"):
            doc = fitz.open(pdf_path)
            assert len(doc) == 1
            doc.close()
