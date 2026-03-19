"""Unit tests for generate_layouts functions.

Tests title_to_description, _resolve_parent_id, process_season, and main().

Requirements: refactor-chronicle2layout 6.1, 6.2, 6.3, 6.4, 6.5
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from generate_layouts import (
    SEASON_CONFIGS,
    _SEASON4_PARENT_MAP,
    _resolve_parent_id,
    derive_paths,
    main,
    process_season,
    title_to_description,
)


# ---------------------------------------------------------------------------
# title_to_description tests
# ---------------------------------------------------------------------------

class TestTitleToDescription:
    """Unit tests for title_to_description."""

    def test_camel_case_split(self) -> None:
        """CamelCase title is split into separate words."""
        result = title_to_description(5, "07", "RottenApples")
        assert result == "5-07 Rotten Apples"

    def test_single_word(self) -> None:
        """Single word title is preserved."""
        result = title_to_description(6, "01", "Intro")
        assert result == "6-01 Intro"

    def test_underscore_fallback(self) -> None:
        """Non-camelCase title with underscores is split on underscores."""
        result = title_to_description(3, "02", "some_title")
        assert result == "3-02 some title"

    def test_space_fallback(self) -> None:
        """Non-camelCase title with spaces is split on spaces."""
        result = title_to_description(4, "05", "some title")
        assert result == "4-05 some title"

    def test_multi_word_camel_case(self) -> None:
        """Multiple camelCase words are all separated."""
        result = title_to_description(7, "12", "TheGreatBeyond")
        assert result == "7-12 The Great Beyond"


# ---------------------------------------------------------------------------
# _resolve_parent_id tests
# ---------------------------------------------------------------------------

class TestResolveParentId:
    """Unit tests for _resolve_parent_id."""

    def test_non_season4_returns_default(self) -> None:
        """Non-season-4 always returns the default parent."""
        result = _resolve_parent_id("pfs2.season5", 5, 1)
        assert result == "pfs2.season5"

    def test_season4_scenario_1_returns_4a(self) -> None:
        """Season 4 scenario 1 maps to season4a."""
        result = _resolve_parent_id("pfs2.season4", 4, 1)
        assert result == "pfs2.season4a"

    def test_season4_scenario_4_returns_4b(self) -> None:
        """Season 4 scenario 4 maps to season4b."""
        result = _resolve_parent_id("pfs2.season4", 4, 4)
        assert result == "pfs2.season4b"

    def test_season4_scenario_6_returns_4c(self) -> None:
        """Season 4 scenario 6 maps to season4c."""
        result = _resolve_parent_id("pfs2.season4", 4, 6)
        assert result == "pfs2.season4c"

    def test_season4_scenario_7_returns_4d(self) -> None:
        """Season 4 scenario 7 maps to season4d."""
        result = _resolve_parent_id("pfs2.season4", 4, 7)
        assert result == "pfs2.season4d"

    def test_season4_scenario_9_returns_4e(self) -> None:
        """Season 4 scenario 9+ maps to season4e."""
        result = _resolve_parent_id("pfs2.season4", 4, 9)
        assert result == "pfs2.season4e"

    def test_season4_unknown_scenario_returns_default(self) -> None:
        """Season 4 scenario not in map returns the default parent."""
        result = _resolve_parent_id("pfs2.season4", 4, 99)
        assert result == "pfs2.season4"


# ---------------------------------------------------------------------------
# process_season tests
# ---------------------------------------------------------------------------

class TestProcessSeason:
    """Unit tests for process_season."""

    def test_skips_missing_chronicles_dir(self, tmp_path: Path, capsys) -> None:
        """Skips processing when chronicles directory does not exist."""
        modules_dir = tmp_path / "modules"
        layouts_dir = tmp_path / "layouts" / "pfs2"
        debug_dir = tmp_path / "debug"

        process_season(
            season_num=6,
            base_dir=tmp_path,
            modules_dir=modules_dir,
            layouts_dir=layouts_dir,
            debug_dir=debug_dir,
            python_exe=sys.executable,
        )

        captured = capsys.readouterr()
        assert "Skipping" in captured.out

    def test_creates_layout_and_debug_dirs(self, tmp_path: Path) -> None:
        """Creates layout and debug directories even if no PDFs found."""
        modules_dir = tmp_path / "modules"
        layouts_dir = tmp_path / "layouts" / "pfs2"
        debug_dir = tmp_path / "debug"

        # Create the chronicles dir but leave it empty
        config = SEASON_CONFIGS[3]
        for subdir in config["chronicles_subdirs"]:
            (modules_dir / config["module_name"] / subdir).mkdir(parents=True)

        process_season(
            season_num=3,
            base_dir=tmp_path,
            modules_dir=modules_dir,
            layouts_dir=layouts_dir,
            debug_dir=debug_dir,
            python_exe=sys.executable,
        )

        assert (layouts_dir / config["layouts_dir"]).exists()
        assert (debug_dir / "season3").exists()

    def test_scenario_filter_limits_processing(self, tmp_path: Path) -> None:
        """Only scenarios in the filter set are processed."""
        modules_dir = tmp_path / "modules"
        layouts_dir = tmp_path / "layouts" / "pfs2"
        debug_dir = tmp_path / "debug"

        config = SEASON_CONFIGS[3]
        chronicles_dir = modules_dir / config["module_name"] / config["chronicles_subdirs"][0]
        chronicles_dir.mkdir(parents=True)

        # Create two fake PDFs matching season 3 pattern
        (chronicles_dir / "3-01-TestScenario.pdf").touch()
        (chronicles_dir / "3-02-OtherScenario.pdf").touch()

        with patch("subprocess.run") as mock_run:
            process_season(
                season_num=3,
                base_dir=tmp_path,
                modules_dir=modules_dir,
                layouts_dir=layouts_dir,
                debug_dir=debug_dir,
                python_exe=sys.executable,
                scenario_filter={"01"},
            )

            # Only scenario 01 should be processed
            assert mock_run.call_count == 1
            cmd_args = mock_run.call_args[0][0]
            assert any("3-01" in str(arg) for arg in cmd_args)

    def test_handles_subprocess_error(self, tmp_path: Path, capsys) -> None:
        """Prints error message when subprocess fails."""
        import subprocess

        modules_dir = tmp_path / "modules"
        layouts_dir = tmp_path / "layouts" / "pfs2"
        debug_dir = tmp_path / "debug"

        config = SEASON_CONFIGS[3]
        chronicles_dir = modules_dir / config["module_name"] / config["chronicles_subdirs"][0]
        chronicles_dir.mkdir(parents=True)
        (chronicles_dir / "3-01-TestScenario.pdf").touch()

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
            process_season(
                season_num=3,
                base_dir=tmp_path,
                modules_dir=modules_dir,
                layouts_dir=layouts_dir,
                debug_dir=debug_dir,
                python_exe=sys.executable,
            )

        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_warns_on_unparseable_filename(self, tmp_path: Path, capsys) -> None:
        """Prints warning for PDF filenames that don't match the pattern."""
        modules_dir = tmp_path / "modules"
        layouts_dir = tmp_path / "layouts" / "pfs2"
        debug_dir = tmp_path / "debug"

        config = SEASON_CONFIGS[3]
        chronicles_dir = modules_dir / config["module_name"] / config["chronicles_subdirs"][0]
        chronicles_dir.mkdir(parents=True)
        (chronicles_dir / "random-file.pdf").touch()

        process_season(
            season_num=3,
            base_dir=tmp_path,
            modules_dir=modules_dir,
            layouts_dir=layouts_dir,
            debug_dir=debug_dir,
            python_exe=sys.executable,
        )

        captured = capsys.readouterr()
        assert "Warning" in captured.out


# ---------------------------------------------------------------------------
# main() CLI tests
# ---------------------------------------------------------------------------

class TestMain:
    """Unit tests for the main() CLI entry point."""

    def test_main_skips_unknown_season(self, capsys) -> None:
        """main() skips seasons not in SEASON_CONFIGS."""
        test_args = ["generate_layouts.py", "--season", "99"]
        with patch("sys.argv", test_args):
            main()

        captured = capsys.readouterr()
        assert "Skipping unknown season 99" in captured.out

    def test_main_processes_all_seasons_by_default(self, tmp_path: Path) -> None:
        """main() processes all configured seasons when --season is omitted."""
        with patch("generate_layouts.process_season") as mock_process:
            test_args = [
                "generate_layouts.py",
                "--base-dir", str(tmp_path),
            ]
            with patch("sys.argv", test_args):
                main()

            # process_season is called with positional args
            called_seasons = {c[0][0] for c in mock_process.call_args_list}
            assert called_seasons == set(SEASON_CONFIGS.keys())

    def test_main_passes_scenario_filter(self, tmp_path: Path) -> None:
        """main() passes --scenarios filter to process_season."""
        with patch("generate_layouts.process_season") as mock_process:
            test_args = [
                "generate_layouts.py",
                "--season", "6",
                "--scenarios", "01", "02",
                "--base-dir", str(tmp_path),
            ]
            with patch("sys.argv", test_args):
                main()

            assert mock_process.call_count == 1
            kwargs = mock_process.call_args[1]
            assert kwargs["scenario_filter"] == {"01", "02"}
            assert mock_process.call_args[0][0] == 6
