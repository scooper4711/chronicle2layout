"""Unit tests for scenario_download_workflow.__main__.

Tests argument parsing defaults/overrides, interactive confirmation
classification, exit code logic, and end-to-end flow with mocked
tools and discovery.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scenario_download_workflow.__main__ import (
    classify_response,
    compute_exit_code,
    main,
    parse_args,
)


# ---------------------------------------------------------------------------
# classify_response
# ---------------------------------------------------------------------------


class TestClassifyResponse:
    """Verify user response classification."""

    def test_accept_y(self) -> None:
        assert classify_response("y") == "accept"

    def test_accept_yes(self) -> None:
        assert classify_response("yes") == "accept"

    def test_accept_uppercase_y(self) -> None:
        assert classify_response("Y") == "accept"

    def test_accept_mixed_case_yes(self) -> None:
        assert classify_response("YeS") == "accept"

    def test_skip_n(self) -> None:
        assert classify_response("n") == "skip"

    def test_skip_no(self) -> None:
        assert classify_response("no") == "skip"

    def test_skip_uppercase_no(self) -> None:
        assert classify_response("NO") == "skip"

    def test_quit_q(self) -> None:
        assert classify_response("q") == "quit"

    def test_quit_quit(self) -> None:
        assert classify_response("quit") == "quit"

    def test_quit_uppercase_quit(self) -> None:
        assert classify_response("QUIT") == "quit"

    def test_invalid_empty(self) -> None:
        assert classify_response("") == "invalid"

    def test_invalid_random(self) -> None:
        assert classify_response("maybe") == "invalid"

    def test_whitespace_stripped(self) -> None:
        assert classify_response("  y  ") == "accept"


# ---------------------------------------------------------------------------
# compute_exit_code
# ---------------------------------------------------------------------------


class TestComputeExitCode:
    """Verify exit code logic."""

    def test_success_returns_zero(self) -> None:
        assert compute_exit_code(1, 0) == 0

    def test_mixed_success_returns_zero(self) -> None:
        assert compute_exit_code(2, 3) == 0

    def test_no_success_returns_one(self) -> None:
        assert compute_exit_code(0, 1) == 1

    def test_all_failed_returns_one(self) -> None:
        assert compute_exit_code(0, 5) == 1

    def test_zero_zero_returns_one(self) -> None:
        assert compute_exit_code(0, 0) == 1


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Verify argument parsing defaults and overrides."""

    def test_defaults(self) -> None:
        args = parse_args([])
        assert args.downloads_dir == Path.home() / "Downloads"
        assert args.project_dir == Path.cwd()
        assert args.recent == timedelta(hours=1)
        assert args.non_interactive is False

    def test_custom_downloads_dir(self) -> None:
        args = parse_args(["--downloads-dir", "/tmp/dl"])
        assert args.downloads_dir == Path("/tmp/dl")

    def test_custom_project_dir(self) -> None:
        args = parse_args(["--project-dir", "/my/project"])
        assert args.project_dir == Path("/my/project")

    def test_custom_recent(self) -> None:
        args = parse_args(["--recent", "30m"])
        assert args.recent == timedelta(minutes=30)

    def test_non_interactive_flag(self) -> None:
        args = parse_args(["--non-interactive"])
        assert args.non_interactive is True

    def test_invalid_recent_exits(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--recent", "abc"])


# ---------------------------------------------------------------------------
# main — end-to-end with mocked tools
# ---------------------------------------------------------------------------

_DISCOVER = "scenario_download_workflow.__main__.discover_recent_pdfs"
_DETECT = "scenario_download_workflow.__main__.detect_game_system"
_EXTRACT = "scenario_download_workflow.__main__.extract_scenario_info"
_COMPUTE_ROUTES = "scenario_download_workflow.__main__.compute_routing_paths"
_PROCESS = "scenario_download_workflow.__main__.process_single_pdf"
_FITZ = "scenario_download_workflow.__main__.fitz"


def _make_mock_doc(page_count: int = 10) -> MagicMock:
    """Create a mock fitz.Document with page_count pages of dummy text."""
    doc = MagicMock()
    doc.__len__ = lambda self: page_count
    page = MagicMock()
    page.get_text.return_value = "Pathfinder Society Scenario #7-06"
    doc.__getitem__ = lambda self, idx: page
    doc.close = MagicMock()
    return doc


class TestMainNoPdfs:
    """Verify behaviour when no PDFs are found."""

    def test_no_pdfs_returns_zero(self, tmp_path: Path) -> None:
        with patch(_DISCOVER, return_value=[]):
            exit_code = main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
                "--non-interactive",
            ])
        assert exit_code == 0

    def test_no_pdfs_prints_message(self, tmp_path: Path, capsys) -> None:
        with patch(_DISCOVER, return_value=[]):
            main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
                "--non-interactive",
            ])
        captured = capsys.readouterr()
        assert "No recent PDFs found" in captured.out


class TestMainInteractive:
    """Verify interactive confirmation flow with mocked input."""

    def test_accept_processes_pdf(self, tmp_path: Path) -> None:
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")
        mock_doc = _make_mock_doc()
        mock_result = MagicMock(success=True)

        from chronicle_extractor.parser import ScenarioInfo
        from scenario_download_workflow.detection import GameSystem

        with (
            patch(_DISCOVER, return_value=[pdf]),
            patch(_FITZ + ".open", return_value=mock_doc),
            patch(_DETECT, return_value=GameSystem.PFS),
            patch(_EXTRACT, return_value=ScenarioInfo(7, "06", "Test")),
            patch(_COMPUTE_ROUTES, return_value=MagicMock()),
            patch(_PROCESS, return_value=mock_result),
            patch("builtins.input", return_value="y"),
        ):
            exit_code = main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
            ])
        assert exit_code == 0

    def test_skip_skips_pdf(self, tmp_path: Path, capsys) -> None:
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")

        with (
            patch(_DISCOVER, return_value=[pdf]),
            patch("builtins.input", return_value="n"),
        ):
            exit_code = main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
            ])
        captured = capsys.readouterr()
        assert "1 skipped" in captured.out
        assert exit_code == 1

    def test_quit_skips_remaining(self, tmp_path: Path, capsys) -> None:
        pdf1 = tmp_path / "a.pdf"
        pdf2 = tmp_path / "b.pdf"
        pdf1.write_bytes(b"%PDF")
        pdf2.write_bytes(b"%PDF")

        with (
            patch(_DISCOVER, return_value=[pdf1, pdf2]),
            patch("builtins.input", return_value="q"),
        ):
            exit_code = main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
            ])
        captured = capsys.readouterr()
        assert "2 skipped" in captured.out
        assert exit_code == 1


class TestMainNonInteractive:
    """Verify non-interactive mode processes all PDFs."""

    def test_processes_all_pdfs(self, tmp_path: Path) -> None:
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")
        mock_doc = _make_mock_doc()
        mock_result = MagicMock(success=True)

        from chronicle_extractor.parser import ScenarioInfo
        from scenario_download_workflow.detection import GameSystem

        with (
            patch(_DISCOVER, return_value=[pdf]),
            patch(_FITZ + ".open", return_value=mock_doc),
            patch(_DETECT, return_value=GameSystem.PFS),
            patch(_EXTRACT, return_value=ScenarioInfo(7, "06", "Test")),
            patch(_COMPUTE_ROUTES, return_value=MagicMock()),
            patch(_PROCESS, return_value=mock_result),
        ):
            exit_code = main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
                "--non-interactive",
            ])
        assert exit_code == 0

    def test_detection_failure_skips_pdf(self, tmp_path: Path) -> None:
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")
        mock_doc = _make_mock_doc()

        with (
            patch(_DISCOVER, return_value=[pdf]),
            patch(_FITZ + ".open", return_value=mock_doc),
            patch(_DETECT, return_value=None),
        ):
            exit_code = main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
                "--non-interactive",
            ])
        assert exit_code == 1

    def test_detection_falls_back_to_page_two(self, tmp_path: Path) -> None:
        """When page 1 has no society string, page 2 is checked."""
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")

        # Page 0 returns cover text (no society), page 1 returns society text
        page0 = MagicMock()
        page0.get_text.return_value = "SCENARIO: #1-20\nMAGIC UNLEASHED\n"
        page1 = MagicMock()
        page1.get_text.return_value = "Starfinder Society Scenario"
        other_page = MagicMock()
        other_page.get_text.return_value = "Some other text"

        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 10

        def getitem(self, idx):
            if idx == 0:
                return page0
            if idx == 1:
                return page1
            return other_page

        mock_doc.__getitem__ = getitem
        mock_doc.close = MagicMock()

        from chronicle_extractor.parser import ScenarioInfo
        from scenario_download_workflow.detection import GameSystem

        mock_result = MagicMock(success=True)

        with (
            patch(_DISCOVER, return_value=[pdf]),
            patch(_FITZ + ".open", return_value=mock_doc),
            patch(_EXTRACT, return_value=ScenarioInfo(1, "20", "Magic Unleashed")),
            patch(_COMPUTE_ROUTES, return_value=MagicMock()),
            patch(_PROCESS, return_value=mock_result),
        ):
            exit_code = main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
                "--non-interactive",
            ])
        assert exit_code == 0

    def test_extraction_failure_skips_pdf(self, tmp_path: Path) -> None:
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")
        mock_doc = _make_mock_doc()

        from scenario_download_workflow.detection import GameSystem

        with (
            patch(_DISCOVER, return_value=[pdf]),
            patch(_FITZ + ".open", return_value=mock_doc),
            patch(_DETECT, return_value=GameSystem.PFS),
            patch(_EXTRACT, return_value=None),
        ):
            exit_code = main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
                "--non-interactive",
            ])
        assert exit_code == 1


class TestMainSummary:
    """Verify summary output at end."""

    def test_summary_printed(self, tmp_path: Path, capsys) -> None:
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")
        mock_doc = _make_mock_doc()
        mock_result = MagicMock(success=True)

        from chronicle_extractor.parser import ScenarioInfo
        from scenario_download_workflow.detection import GameSystem

        with (
            patch(_DISCOVER, return_value=[pdf]),
            patch(_FITZ + ".open", return_value=mock_doc),
            patch(_DETECT, return_value=GameSystem.PFS),
            patch(_EXTRACT, return_value=ScenarioInfo(7, "06", "Test")),
            patch(_COMPUTE_ROUTES, return_value=MagicMock()),
            patch(_PROCESS, return_value=mock_result),
        ):
            main([
                "--downloads-dir", str(tmp_path),
                "--project-dir", str(tmp_path),
                "--non-interactive",
            ])
        captured = capsys.readouterr()
        assert "Summary:" in captured.out
        assert "1 processed" in captured.out
