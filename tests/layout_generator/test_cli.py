"""CLI integration tests for layout_generator.__main__ module.

Tests the main() entry point with real argument lists, verifying
error handling, output file creation, summary output, and exit codes.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9,
    9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6,
    13.1, 13.2, 13.3, 13.4
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from layout_generator.__main__ import main

REAL_PDF = Path("Scenarios/pfs2/season1/1-00-OriginoftheOpenRoad.pdf")
LAYOUTS_DIR = Path(
    "modules/pfs-chronicle-generator/assets/layouts/pfs2",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_toml(path: Path, content: str) -> Path:
    """Write TOML content to a file and return its path."""
    path.write_text(content, encoding="utf-8")
    return path


def create_parent_layout(layouts_dir: Path, layout_id: str) -> None:
    """Create a minimal parent layout JSON with canvas definitions."""
    layout = {
        "id": layout_id,
        "canvas": {
            "page": {
                "x": 0.0,
                "y": 0.0,
                "x2": 100.0,
                "y2": 100.0,
            },
            "items": {
                "x": 0.0,
                "y": 50.0,
                "x2": 40.0,
                "y2": 83.0,
                "parent": "page",
            },
            "summary": {
                "x": 0.0,
                "y": 9.0,
                "x2": 100.0,
                "y2": 31.0,
                "parent": "page",
            },
        },
    }
    layout_file = layouts_dir / f"{layout_id}.json"
    layout_file.write_text(json.dumps(layout, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Missing arguments — argparse exits non-zero
# ---------------------------------------------------------------------------


class TestMissingArguments:
    """Tests for missing required CLI arguments."""

    def test_no_arguments_exits_nonzero(self, capsys: pytest.CaptureFixture) -> None:
        """Calling main with no arguments exits non-zero with usage info."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert "usage" in captured.err.lower() or "required" in captured.err.lower()


# ---------------------------------------------------------------------------
# Missing metadata file
# ---------------------------------------------------------------------------


class TestMissingMetadataFile:
    """Tests for missing metadata file error handling."""

    def test_missing_metadata_exits_nonzero(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """A non-existent metadata file exits with code 1 and error to stderr."""
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()

        exit_code = main([
            str(pdf_dir),
            "--metadata-file", str(tmp_path / "nonexistent.toml"),
            "--layouts-dir", str(tmp_path),
        ])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()


# ---------------------------------------------------------------------------
# Missing layouts directory
# ---------------------------------------------------------------------------


class TestMissingLayoutsDirectory:
    """Tests for missing layouts directory error handling."""

    def test_missing_layouts_dir_exits_nonzero(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """A non-existent layouts directory exits with code 1."""
        toml_path = write_toml(
            tmp_path / "meta.toml",
            '[[rules]]\npattern = ".*"\nid = "x"\nparent = "y"\n',
        )
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()

        exit_code = main([
            str(pdf_dir),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(tmp_path / "no_such_dir"),
        ])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "layouts directory" in captured.err.lower()


# ---------------------------------------------------------------------------
# --layouts-dir not provided and not in TOML
# ---------------------------------------------------------------------------


class TestLayoutsDirNotProvided:
    """Tests for layouts-dir fallback behavior."""

    def test_no_layouts_dir_anywhere_exits_nonzero(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """No --layouts-dir and no layouts_dir in TOML exits with code 1."""
        toml_path = write_toml(
            tmp_path / "meta.toml",
            '[[rules]]\npattern = ".*"\nid = "x"\nparent = "y"\n',
        )
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()

        exit_code = main([
            str(pdf_dir),
            "--metadata-file", str(toml_path),
        ])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "layouts" in captured.err.lower()


# ---------------------------------------------------------------------------
# No matching rules — warning and exit code 1
# ---------------------------------------------------------------------------


class TestNoMatchingRules:
    """Tests for PDFs that don't match any metadata rules."""

    def test_no_matching_rules_exits_with_code_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """PDFs with no matching rules produce a warning and exit code 1."""
        layouts_dir = tmp_path / "layouts"
        layouts_dir.mkdir()

        toml_path = write_toml(
            tmp_path / "meta.toml",
            '[[rules]]\npattern = "^NOMATCH$"\nid = "x"\nparent = "y"\n',
        )

        # Create a dummy PDF file (doesn't need to be valid — rule won't match)
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "test.pdf").write_bytes(b"%PDF-1.4 dummy")

        exit_code = main([
            str(pdf_dir),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(layouts_dir),
        ])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "no matching rule" in captured.err.lower()
        assert "0 generated" in captured.err.lower()


# ---------------------------------------------------------------------------
# Output directory creation
# ---------------------------------------------------------------------------


class TestOutputDirectoryCreation:
    """Tests for automatic output directory creation."""

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_output_dir_created_when_missing(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """The output directory is created if it does not exist."""
        layouts_dir = tmp_path / "layouts"
        layouts_dir.mkdir()
        create_parent_layout(layouts_dir, "test-parent")

        output_dir = tmp_path / "output" / "nested"
        assert not output_dir.exists()

        toml_content = (
            "[[rules]]\n"
            "pattern = '.*\\.pdf'\n"
            "id = 'test-leaf'\n"
            "parent = 'test-parent'\n"
        )
        toml_path = write_toml(tmp_path / "meta.toml", toml_content)

        exit_code = main([
            str(REAL_PDF),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(layouts_dir),
            "--output-dir", str(output_dir),
        ])

        assert exit_code == 0
        assert output_dir.exists()
        assert (output_dir / "test-leaf.json").exists()


# ---------------------------------------------------------------------------
# Summary output (generated/skipped counts)
# ---------------------------------------------------------------------------


class TestSummaryOutput:
    """Tests for the summary line printed to stderr."""

    def test_summary_shows_zero_generated_on_no_match(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Summary reports 0 generated when no rules match."""
        layouts_dir = tmp_path / "layouts"
        layouts_dir.mkdir()

        toml_path = write_toml(
            tmp_path / "meta.toml",
            '[[rules]]\npattern = "^NOMATCH$"\nid = "x"\nparent = "y"\n',
        )

        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "a.pdf").write_bytes(b"%PDF-1.4 dummy")

        main([
            str(pdf_dir),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(layouts_dir),
        ])

        captured = capsys.readouterr()
        assert "0 generated" in captured.err.lower()
        assert "1 skipped" in captured.err.lower()

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_summary_shows_generated_count(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Summary reports correct generated count on success."""
        layouts_dir = tmp_path / "layouts"
        layouts_dir.mkdir()
        create_parent_layout(layouts_dir, "test-parent")

        toml_content = (
            "[[rules]]\n"
            "pattern = '.*\\.pdf'\n"
            "id = 'test-leaf'\n"
            "parent = 'test-parent'\n"
        )
        toml_path = write_toml(tmp_path / "meta.toml", toml_content)

        main([
            str(REAL_PDF),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(layouts_dir),
            "--output-dir", str(tmp_path / "out"),
        ])

        captured = capsys.readouterr()
        assert "1 generated" in captured.err.lower()


# ---------------------------------------------------------------------------
# Single-file mode with real chronicle PDF
# ---------------------------------------------------------------------------


class TestSingleFileMode:
    """Tests for single-file mode with a real chronicle PDF."""

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_single_file_generates_layout(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Single-file mode generates a valid layout JSON."""
        layouts_dir = tmp_path / "layouts"
        layouts_dir.mkdir()
        create_parent_layout(layouts_dir, "test-parent")

        output_dir = tmp_path / "output"

        toml_content = (
            "[[rules]]\n"
            "pattern = '.*\\.pdf'\n"
            "id = 'pfs2-s1-00'\n"
            "parent = 'test-parent'\n"
            "description = 'Origin of the Open Road'\n"
        )
        toml_path = write_toml(tmp_path / "meta.toml", toml_content)

        exit_code = main([
            str(REAL_PDF),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(layouts_dir),
            "--output-dir", str(output_dir),
        ])

        assert exit_code == 0

        output_file = output_dir / "pfs2-s1-00.json"
        assert output_file.exists()

        layout = json.loads(output_file.read_text(encoding="utf-8"))
        assert layout["id"] == "pfs2-s1-00"
        assert layout["parent"] == "test-parent"
        assert layout["description"] == "Origin of the Open Road"

        # Output path printed to stdout
        captured = capsys.readouterr()
        assert "pfs2-s1-00.json" in captured.out


# ---------------------------------------------------------------------------
# Directory mode with temp directory containing PDFs
# ---------------------------------------------------------------------------


class TestDirectoryMode:
    """Tests for directory mode with multiple PDFs."""

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_directory_mode_processes_pdfs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Directory mode finds and processes PDF files recursively."""
        layouts_dir = tmp_path / "layouts"
        layouts_dir.mkdir()
        create_parent_layout(layouts_dir, "test-parent")

        output_dir = tmp_path / "output"

        # Create a directory structure with a symlink/copy of the real PDF
        pdf_dir = tmp_path / "chronicles"
        sub_dir = pdf_dir / "season1"
        sub_dir.mkdir(parents=True)

        import shutil
        shutil.copy2(str(REAL_PDF), str(sub_dir / "s1-00.pdf"))

        toml_content = (
            "[[rules]]\n"
            "pattern = 'season1/s1-(\\d+)\\.pdf'\n"
            "id = 'pfs2-s1-$1'\n"
            "parent = 'test-parent'\n"
            "description = 'Season 1 scenario $1'\n"
        )
        toml_path = write_toml(tmp_path / "meta.toml", toml_content)

        exit_code = main([
            str(pdf_dir),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(layouts_dir),
            "--output-dir", str(output_dir),
        ])

        assert exit_code == 0

        output_file = output_dir / "season1" / "pfs2-s1-00.json"
        assert output_file.exists()

        layout = json.loads(output_file.read_text(encoding="utf-8"))
        assert layout["id"] == "pfs2-s1-00"
        assert layout["description"] == "Season 1 scenario 00"

        captured = capsys.readouterr()
        assert "1 generated" in captured.err.lower()

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_directory_mode_mixed_match_and_skip(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Directory mode counts both matched and unmatched PDFs."""
        layouts_dir = tmp_path / "layouts"
        layouts_dir.mkdir()
        create_parent_layout(layouts_dir, "test-parent")

        output_dir = tmp_path / "output"

        pdf_dir = tmp_path / "chronicles"
        pdf_dir.mkdir()

        import shutil
        shutil.copy2(str(REAL_PDF), str(pdf_dir / "matched.pdf"))
        # Create a dummy PDF that won't match the rule
        (pdf_dir / "unmatched.pdf").write_bytes(b"%PDF-1.4 dummy")

        toml_content = (
            "[[rules]]\n"
            "pattern = '^matched\\.pdf$'\n"
            "id = 'test-matched'\n"
            "parent = 'test-parent'\n"
        )
        toml_path = write_toml(tmp_path / "meta.toml", toml_content)

        exit_code = main([
            str(pdf_dir),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(layouts_dir),
            "--output-dir", str(output_dir),
        ])

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "1 generated" in captured.err.lower()
        assert "1 skipped" in captured.err.lower()


# ---------------------------------------------------------------------------
# Non-existent pdf_path
# ---------------------------------------------------------------------------


class TestNonExistentPdfPath:
    """Tests for non-existent pdf_path argument."""

    def test_nonexistent_pdf_path_exits_nonzero(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """A non-existent pdf_path exits with code 1 and error to stderr."""
        toml_path = write_toml(
            tmp_path / "meta.toml",
            '[[rules]]\npattern = ".*"\nid = "x"\nparent = "y"\n',
        )

        exit_code = main([
            str(tmp_path / "no_such_path"),
            "--metadata-file", str(toml_path),
            "--layouts-dir", str(tmp_path),
        ])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()
