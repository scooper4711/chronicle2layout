"""Unit tests for scenario_download_workflow.pipeline.

Mocks all five downstream ``main()`` functions to verify argument
construction, staging directory lifecycle, error propagation, and
graceful blueprint skip behaviour.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chronicle_extractor.parser import ScenarioInfo
from scenario_download_workflow.detection import GameSystem
from scenario_download_workflow.pipeline import (
    PipelineResult,
    _build_season_blueprint_pattern,
    process_single_pdf,
)
from scenario_download_workflow.routing import RoutingPaths, compute_routing_paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROOT = Path("/fake/project")


def _make_routes(
    tmp_path: Path,
    system: GameSystem = GameSystem.PFS,
    info: ScenarioInfo | None = None,
) -> RoutingPaths:
    """Build real RoutingPaths rooted under tmp_path."""
    if info is None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
    return compute_routing_paths(tmp_path, system, info)


def _default_info() -> ScenarioInfo:
    return ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")


def _create_pdf(tmp_path: Path, name: str = "test.pdf") -> Path:
    """Create a dummy PDF file in tmp_path."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    pdf = tmp_path / name
    pdf.write_bytes(b"%PDF-1.4 dummy")
    return pdf


# ---------------------------------------------------------------------------
# PipelineResult dataclass
# ---------------------------------------------------------------------------


class TestPipelineResult:
    """Verify PipelineResult dataclass fields and defaults."""

    def test_success_result(self) -> None:
        result = PipelineResult(success=True, steps_completed=5)
        assert result.success is True
        assert result.steps_completed == 5
        assert result.error_message is None

    def test_failure_result(self) -> None:
        result = PipelineResult(
            success=False, steps_completed=2, error_message="step 3 failed"
        )
        assert result.success is False
        assert result.steps_completed == 2
        assert result.error_message == "step 3 failed"


# ---------------------------------------------------------------------------
# Blueprint pattern construction
# ---------------------------------------------------------------------------


class TestBuildSeasonBlueprintPattern:
    """Verify season-level base blueprint ID pattern."""

    def test_pfs_season_7(self) -> None:
        assert (
            _build_season_blueprint_pattern("pfs2", 7)
            == "pfs2.season7-layout-s7-00*"
        )

    def test_sfs_season_1(self) -> None:
        assert (
            _build_season_blueprint_pattern("sfs2", 1)
            == "sfs2.season1-layout-s1-00*"
        )


# ---------------------------------------------------------------------------
# Full pipeline — happy path
# ---------------------------------------------------------------------------

_RENAMER = "scenario_download_workflow.pipeline.scenario_renamer_cli"
_CHRONICLE = "scenario_download_workflow.pipeline.chronicle_extractor_cli"
_BLUEPRINT = "scenario_download_workflow.pipeline.blueprint2layout_cli"
_LAYOUT_GEN = "scenario_download_workflow.pipeline.layout_generator_cli"
_VISUALIZER = "scenario_download_workflow.pipeline.layout_visualizer_cli"


def _mock_renamer_success(routes: RoutingPaths, info: ScenarioInfo):
    """Return a side_effect that creates a renamed PDF, prints its path,
    and returns 0 — mimicking the real scenario_renamer.
    """
    def side_effect(argv):
        routes.scenarios_dir.mkdir(parents=True, exist_ok=True)
        out_file = routes.scenarios_dir / f"{info.season}-{info.scenario}-Test.pdf"
        out_file.write_bytes(b"%PDF renamed")
        print(out_file)
        return 0
    return side_effect


def _mock_chronicle_success(routes: RoutingPaths, info: ScenarioInfo):
    """Return a side_effect that creates a chronicle PDF, prints its path,
    and returns 0 — mimicking the real chronicle_extractor.
    """
    def side_effect(argv):
        routes.chronicles_dir.mkdir(parents=True, exist_ok=True)
        out_file = routes.chronicles_dir / f"{info.season}-{info.scenario}-TestChronicle.pdf"
        out_file.write_bytes(b"%PDF chronicle")
        print(out_file)
        return 0
    return side_effect


class TestHappyPath:
    """All five tools succeed and produce expected output."""

    def test_all_steps_complete(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", return_value=0),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is True
        assert result.steps_completed == 5
        assert result.error_message is None

    def test_finds_new_file_when_preexisting_files_present(self, tmp_path: Path) -> None:
        """Verify the pipeline picks up the newly created file, not a
        pre-existing one already in the output directory."""
        info = ScenarioInfo(season=7, scenario="16", name="A Stars Journey")
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        # Pre-populate the output dirs with an older scenario
        routes.scenarios_dir.mkdir(parents=True, exist_ok=True)
        (routes.scenarios_dir / "7-01-EnoughisEnough.pdf").write_bytes(b"%PDF old")
        routes.chronicles_dir.mkdir(parents=True, exist_ok=True)
        (routes.chronicles_dir / "7-01-EnoughisEnoughChronicle.pdf").write_bytes(b"%PDF old")

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", return_value=0),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is True
        assert result.steps_completed == 5

    def test_renamer_receives_correct_args(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")
        renamer_mock = MagicMock(side_effect=_mock_renamer_success(routes, info))

        with (
            patch(f"{_RENAMER}.main", renamer_mock),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", return_value=0),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        args = renamer_mock.call_args[0][0]
        assert args[0] == "--input-dir"
        # staging dir is a temp dir — just verify it was a string
        assert isinstance(args[1], str)
        assert args[2] == "--output-dir"
        assert args[3] == str(routes.scenarios_dir.parent)

    def test_chronicle_receives_correct_args(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")
        chronicle_mock = MagicMock(
            side_effect=_mock_chronicle_success(routes, info)
        )

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", chronicle_mock),
            patch(f"{_BLUEPRINT}.main", return_value=0),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        args = chronicle_mock.call_args[0][0]
        assert args[0] == "--input-dir"
        assert args[2] == "--output-dir"
        assert args[3] == str(routes.chronicles_dir.parent)

    def test_blueprint_receives_correct_args(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")
        blueprint_mock = MagicMock(return_value=0)

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", blueprint_mock),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        args = blueprint_mock.call_args[0][0]
        assert args == [
            "--blueprints-dir", str(routes.blueprints_dir),
            "--blueprint-id", "pfs2.season7-layout-s7-00*",
            "--output-dir", str(routes.layouts_dir),
        ]

    def test_layout_generator_receives_correct_args(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")
        layout_mock = MagicMock(return_value=0)

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", return_value=0),
            patch(f"{_LAYOUT_GEN}.main", layout_mock),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        args = layout_mock.call_args[0][0]
        # First arg is the chronicle PDF path
        assert args[0].endswith(".pdf")
        assert args[1] == "--metadata-file"
        assert args[2] == str(tmp_path / "chronicle_properties.toml")
        assert args[3] == "--layouts-dir"
        assert args[4] == str(routes.layouts_dir)
        assert args[5] == "--base-dir"

    def test_visualizer_receives_correct_args(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")
        viz_mock = MagicMock(return_value=0)

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", return_value=0),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", viz_mock),
        ):
            process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        args = viz_mock.call_args[0][0]
        assert args == [
            "--layout-root", str(routes.layouts_dir),
            "--layout-id", routes.layout_id,
            "--output-dir", str(tmp_path / "debug_clips" / "layout_visualizer"),
            "--mode", "data",
        ]


# ---------------------------------------------------------------------------
# Staging directory cleanup
# ---------------------------------------------------------------------------


class TestStagingCleanup:
    """Verify staging directories are cleaned up even on failure."""

    def test_cleanup_on_renamer_failure(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        staging_dirs: list[str] = []
        original_mkdtemp = __import__("tempfile").mkdtemp

        def tracking_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            staging_dirs.append(d)
            return d

        with (
            patch("scenario_download_workflow.pipeline.tempfile.mkdtemp", side_effect=tracking_mkdtemp),
            patch(f"{_RENAMER}.main", return_value=1),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        # All staging dirs should be cleaned up
        for d in staging_dirs:
            assert not Path(d).exists()

    def test_cleanup_on_chronicle_failure(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        staging_dirs: list[str] = []
        original_mkdtemp = __import__("tempfile").mkdtemp

        def tracking_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            staging_dirs.append(d)
            return d

        with (
            patch("scenario_download_workflow.pipeline.tempfile.mkdtemp", side_effect=tracking_mkdtemp),
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", return_value=1),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        assert result.steps_completed == 1
        for d in staging_dirs:
            assert not Path(d).exists()

    def test_cleanup_on_renamer_exception(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        staging_dirs: list[str] = []
        original_mkdtemp = __import__("tempfile").mkdtemp

        def tracking_mkdtemp(**kwargs):
            d = original_mkdtemp(**kwargs)
            staging_dirs.append(d)
            return d

        with (
            patch("scenario_download_workflow.pipeline.tempfile.mkdtemp", side_effect=tracking_mkdtemp),
            patch(f"{_RENAMER}.main", side_effect=RuntimeError("boom")),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        for d in staging_dirs:
            assert not Path(d).exists()


# ---------------------------------------------------------------------------
# Error propagation — non-zero exit codes
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    """Verify pipeline stops and reports errors on tool failures."""

    def test_renamer_nonzero_stops_pipeline(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        with patch(f"{_RENAMER}.main", return_value=1):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        assert result.steps_completed == 0
        assert "Step 1" in result.error_message

    def test_chronicle_nonzero_stops_pipeline(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", return_value=1),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        assert result.steps_completed == 1
        assert "Step 2" in result.error_message

    def test_layout_generator_nonzero_stops_pipeline(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", return_value=0),
            patch(f"{_LAYOUT_GEN}.main", return_value=1),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        assert result.steps_completed == 3
        assert "Step 4" in result.error_message

    def test_visualizer_nonzero_stops_pipeline(self, tmp_path: Path) -> None:
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", return_value=0),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=1),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        assert result.steps_completed == 4
        assert "Step 5" in result.error_message

    def test_renamer_no_output_file(self, tmp_path: Path) -> None:
        """Renamer returns 0 but produces no output file."""
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        with patch(f"{_RENAMER}.main", return_value=0):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        assert result.steps_completed == 0


# ---------------------------------------------------------------------------
# Blueprint step — graceful skip
# ---------------------------------------------------------------------------


class TestBlueprintGracefulSkip:
    """Verify blueprint step skips gracefully when no blueprint found."""

    def test_blueprint_nonzero_continues_pipeline(self, tmp_path: Path) -> None:
        """blueprint2layout returns non-zero → warning, pipeline continues."""
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", return_value=1),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is True
        assert result.steps_completed == 5

    def test_quest_skips_blueprint_step(self, tmp_path: Path) -> None:
        """Quests (season=0) skip the blueprint step entirely."""
        info = ScenarioInfo(season=0, scenario="14", name="Silverhex Chronicles")
        routes = _make_routes(tmp_path, system=GameSystem.PFS, info=info)
        pdf = _create_pdf(tmp_path / "downloads")
        blueprint_mock = MagicMock(return_value=0)

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", blueprint_mock),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is True
        assert result.steps_completed == 5
        blueprint_mock.assert_not_called()

    def test_bounty_skips_blueprint_step(self, tmp_path: Path) -> None:
        """Bounties (season=-1) skip the blueprint step entirely."""
        info = ScenarioInfo(season=-1, scenario="13", name="Blood of the Beautiful")
        routes = _make_routes(tmp_path, system=GameSystem.PFS, info=info)
        pdf = _create_pdf(tmp_path / "downloads")
        blueprint_mock = MagicMock(return_value=0)

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", blueprint_mock),
            patch(f"{_LAYOUT_GEN}.main", return_value=0),
            patch(f"{_VISUALIZER}.main", return_value=0),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is True
        blueprint_mock.assert_not_called()

    def test_blueprint_exception_fails_pipeline(self, tmp_path: Path) -> None:
        """An unexpected exception in blueprint2layout fails the pipeline."""
        info = _default_info()
        routes = _make_routes(tmp_path, info=info)
        pdf = _create_pdf(tmp_path / "downloads")

        with (
            patch(f"{_RENAMER}.main", side_effect=_mock_renamer_success(routes, info)),
            patch(f"{_CHRONICLE}.main", side_effect=_mock_chronicle_success(routes, info)),
            patch(f"{_BLUEPRINT}.main", side_effect=RuntimeError("crash")),
        ):
            result = process_single_pdf(pdf, tmp_path, GameSystem.PFS, info, routes)

        assert result.success is False
        assert result.steps_completed == 2
        assert "Step 3" in result.error_message
