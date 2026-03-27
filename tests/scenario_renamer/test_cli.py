"""CLI integration tests for scenario_renamer.__main__ module.

Tests argument parsing, input directory validation, output directory
creation, and successful invocation with an empty input directory.

Requirements: scenario-renamer 1.1, 1.2, 1.3, 1.4
"""

from pathlib import Path

import pytest

from scenario_renamer.__main__ import main, parse_args


class TestParseArgs:
    """Tests for parse_args argument handling."""

    def test_missing_input_dir_exits_nonzero(self) -> None:
        """Omitting --input-dir causes SystemExit with non-zero code."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--output-dir", "/tmp/out"])
        assert exc_info.value.code != 0

    def test_missing_output_dir_exits_nonzero(self) -> None:
        """Omitting --output-dir causes SystemExit with non-zero code."""
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--input-dir", "/tmp/in"])
        assert exc_info.value.code != 0

    def test_valid_args_returns_paths(self, tmp_path: Path) -> None:
        """Both arguments provided returns namespace with Path objects."""
        args = parse_args([
            "--input-dir", str(tmp_path / "in"),
            "--output-dir", str(tmp_path / "out"),
        ])
        assert isinstance(args.input_dir, Path)
        assert isinstance(args.output_dir, Path)


class TestMain:
    """Tests for main CLI entry point."""

    def test_nonexistent_input_dir_returns_one(self, tmp_path: Path) -> None:
        """Non-existent --input-dir causes exit code 1 and stderr message."""
        nonexistent = tmp_path / "does_not_exist"
        code = main([
            "--input-dir", str(nonexistent),
            "--output-dir", str(tmp_path / "out"),
        ])
        assert code == 1

    def test_nonexistent_input_dir_prints_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Non-existent --input-dir prints descriptive error to stderr."""
        nonexistent = tmp_path / "does_not_exist"
        main([
            "--input-dir", str(nonexistent),
            "--output-dir", str(tmp_path / "out"),
        ])
        captured = capsys.readouterr()
        assert "does not exist" in captured.err

    def test_output_dir_created_when_missing(self, tmp_path: Path) -> None:
        """--output-dir is created (including parents) when it doesn't exist."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "nested" / "deep" / "output"

        code = main([
            "--input-dir", str(input_dir),
            "--output-dir", str(output_dir),
        ])

        assert code == 0
        assert output_dir.is_dir()

    def test_successful_invocation_empty_input(self, tmp_path: Path) -> None:
        """Empty input directory processes successfully with exit code 0."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        code = main([
            "--input-dir", str(input_dir),
            "--output-dir", str(output_dir),
        ])

        assert code == 0
        assert output_dir.is_dir()
