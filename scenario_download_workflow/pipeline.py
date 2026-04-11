"""Five-step processing pipeline for a single scenario PDF.

Orchestrates the downstream tools (scenario_renamer, chronicle_extractor,
blueprint2layout, layout_generator, layout_visualizer) via their
``main(argv)`` functions. Creates temporary staging directories for
tools that expect directory-based input, and cleans them up with
``try/finally`` regardless of success or failure.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from chronicle_extractor.filename import sanitize_name
from chronicle_extractor.parser import ScenarioInfo, _BOUNTY_SEASON
from scenario_download_workflow.detection import GameSystem
from scenario_download_workflow.routing import RoutingPaths

import blueprint2layout.__main__ as blueprint2layout_cli
import chronicle_extractor.__main__ as chronicle_extractor_cli
import layout_generator.__main__ as layout_generator_cli
import layout_visualizer.__main__ as layout_visualizer_cli
import scenario_renamer.__main__ as scenario_renamer_cli


@dataclass
class PipelineResult:
    """Outcome of processing a single PDF through the pipeline."""

    success: bool
    steps_completed: int
    error_message: str | None = None


def _build_season_blueprint_pattern(
    prefix: str,
    season: int,
) -> str:
    """Construct the season-level base blueprint ID glob pattern.

    Args:
        prefix: System prefix (e.g. ``pfs2``).
        season: Season number.

    Returns:
        A glob pattern like ``pfs2.season7-layout-s7-00*``.
    """
    return f"{prefix}.season{season}-layout-s{season}-00*"


def _capture_stdout(func, *args):
    """Call a function while capturing its stdout output.

    Returns:
        Tuple of (return_value, captured_lines).
    """
    import io
    import contextlib

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = func(*args)
    lines = [line.strip() for line in buffer.getvalue().splitlines() if line.strip()]
    return result, lines


def _run_step_1_rename(
    pdf_path: Path,
    routes: RoutingPaths,
) -> Path | None:
    """Step 1: Rename and file the scenario PDF via scenario_renamer.

    Copies the PDF into a staging directory, invokes scenario_renamer,
    and parses the output path from the tool's stdout.

    Returns:
        Path to the renamed scenario PDF, or ``None`` on failure.
    """
    print("Step 1/5: Renaming scenario...")
    staging = tempfile.mkdtemp(prefix="sdw_rename_")
    try:
        shutil.copy2(pdf_path, Path(staging) / pdf_path.name)

        # scenario_renamer creates its own season subdirectory, so pass
        # the parent (e.g. Scenarios/PFS/) not the season dir itself.
        renamer_output_dir = routes.scenarios_dir.parent
        exit_code, stdout_lines = _capture_stdout(
            scenario_renamer_cli.main,
            ["--input-dir", staging, "--output-dir", str(renamer_output_dir)],
        )
        if exit_code != 0:
            print(
                f"  Error: scenario_renamer exited with code {exit_code}",
                file=sys.stderr,
            )
            return None

        # The tool prints the output path to stdout
        output = _find_pdf_in_stdout(stdout_lines)
        if output is None:
            print(
                "  Error: scenario_renamer produced no output file",
                file=sys.stderr,
            )
            return None

        print(f"  Renamed: {output}")
        return output
    except Exception as exc:
        print(f"  Error in scenario_renamer: {exc}", file=sys.stderr)
        return None
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _find_pdf_in_stdout(lines: list[str]) -> Path | None:
    """Find the first .pdf path printed to stdout by a tool.

    Args:
        lines: Captured stdout lines from a tool invocation.

    Returns:
        Path to the PDF file, or ``None`` if none found.
    """
    for line in lines:
        if line.lower().endswith(".pdf") and Path(line).is_file():
            return Path(line)
    return None


def _run_step_2_chronicle(
    renamed_pdf: Path,
    routes: RoutingPaths,
) -> Path | None:
    """Step 2: Extract the chronicle sheet via chronicle_extractor.

    Copies the renamed PDF into a staging directory, invokes
    chronicle_extractor, and parses the output path from stdout.

    Returns:
        Path to the extracted chronicle PDF, or ``None`` on failure.
    """
    print("Step 2/5: Extracting chronicle...")
    staging = tempfile.mkdtemp(prefix="sdw_chronicle_")
    try:
        shutil.copy2(renamed_pdf, Path(staging) / renamed_pdf.name)

        # chronicle_extractor creates its own season subdirectory, so pass
        # the parent (e.g. chronicles/pfs2/) not the season dir itself.
        extractor_output_dir = routes.chronicles_dir.parent
        exit_code, stdout_lines = _capture_stdout(
            chronicle_extractor_cli.main,
            ["--input-dir", staging, "--output-dir", str(extractor_output_dir)],
        )
        if exit_code != 0:
            print(
                f"  Error: chronicle_extractor exited with code {exit_code}",
                file=sys.stderr,
            )
            return None

        output = _find_pdf_in_stdout(stdout_lines)
        if output is None:
            print(
                "  Error: chronicle_extractor produced no output file",
                file=sys.stderr,
            )
            return None

        print(f"  Chronicle: {output}")
        return output
    except Exception as exc:
        print(f"  Error in chronicle_extractor: {exc}", file=sys.stderr)
        return None
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _run_step_3_blueprint(
    info: ScenarioInfo,
    routes: RoutingPaths,
) -> bool:
    """Step 3: Convert season-level base blueprint to layout via blueprint2layout.

    Uses the season-level base blueprint ID pattern. If no matching
    blueprint is found (non-zero exit), prints a warning and returns
    ``True`` so the pipeline continues.

    Returns:
        ``True`` if the step completed (success or graceful skip),
        ``False`` only on unexpected exceptions.
    """
    print("Step 3/5: Converting blueprint to layout...")

    if info.season <= 0:
        print("  Skipped: no blueprint for quests/bounties")
        return True

    pattern = _build_season_blueprint_pattern(routes.system_prefix, info.season)
    print(f"  Blueprint pattern: {pattern}")

    try:
        exit_code = blueprint2layout_cli.main([
            "--blueprints-dir", str(routes.blueprints_dir),
            "--blueprint-id", pattern,
            "--output-dir", str(routes.layouts_dir),
        ])
        if exit_code != 0:
            print(
                f"  Warning: no matching blueprint found for "
                f"{routes.system_prefix} season {info.season} "
                f"(blueprint2layout exited with code {exit_code}). "
                f"Skipping blueprint step.",
                file=sys.stderr,
            )
            return True

        print(
            f"  Scenario resolves to blueprint pattern {pattern}"
        )
        return True
    except Exception as exc:
        print(f"  Error in blueprint2layout: {exc}", file=sys.stderr)
        return False


def _run_step_4_layout(
    chronicle_pdf: Path,
    project_root: Path,
    routes: RoutingPaths,
) -> bool:
    """Step 4: Generate leaf layout JSON via layout_generator.

    Passes the chronicle PDF path with ``--base-dir`` so the TOML
    pattern matching sees the correct relative path (e.g.
    ``pfs2/season7/7-16-...pdf``).

    Returns:
        ``True`` on success, ``False`` on failure.
    """
    print("Step 4/5: Generating layout...")
    metadata_file = project_root / "chronicle_properties.toml"

    # chronicles_dir is e.g. .../chronicles/pfs2/season7 — go up two
    # levels to get the chronicles root that the TOML patterns expect.
    chronicles_root = routes.chronicles_dir.parent.parent

    try:
        exit_code = layout_generator_cli.main([
            str(chronicle_pdf),
            "--metadata-file", str(metadata_file),
            "--layouts-dir", str(routes.layouts_dir),
            "--base-dir", str(chronicles_root),
        ])
        if exit_code != 0:
            print(
                f"  Error: layout_generator exited with code {exit_code}",
                file=sys.stderr,
            )
            return False

        print("  Layout generated successfully")
        return True
    except Exception as exc:
        print(f"  Error in layout_generator: {exc}", file=sys.stderr)
        return False


def _run_step_5_visualize(
    routes: RoutingPaths,
    project_root: Path,
) -> bool:
    """Step 5: Render a data-mode preview via layout_visualizer.

    Uses the layout root directory and layout ID to generate a
    visualization PNG.

    Returns:
        ``True`` on success, ``False`` on failure.
    """
    print("Step 5/5: Generating visualization...")
    viz_dir = project_root / "debug_clips" / "layout_visualizer"

    try:
        exit_code = layout_visualizer_cli.main([
            "--layout-root", str(routes.layouts_dir),
            "--layout-id", routes.layout_id,
            "--output-dir", str(viz_dir),
            "--mode", "data",
        ])
        if exit_code != 0:
            print(
                f"  Error: layout_visualizer exited with code {exit_code}",
                file=sys.stderr,
            )
            return False

        print("  Visualization generated successfully")
        return True
    except Exception as exc:
        print(f"  Error in layout_visualizer: {exc}", file=sys.stderr)
        return False


def process_single_pdf(
    pdf_path: Path,
    project_root: Path,
    system: GameSystem,
    info: ScenarioInfo,
    routes: RoutingPaths,
) -> PipelineResult:
    """Run the 5-step pipeline for a single scenario PDF.

    Creates and cleans up staging directories. Each step prints
    progress to stdout and errors to stderr. Returns a result
    indicating success/failure and how far the pipeline got.

    Args:
        pdf_path: Path to the downloaded scenario PDF.
        project_root: The PFS Tools project root directory.
        system: The detected game system (PFS or SFS).
        info: Parsed scenario metadata.
        routes: Pre-computed routing paths for this scenario.

    Returns:
        A PipelineResult with success status, steps completed, and
        any error message.
    """
    steps_completed = 0

    # Step 1: Rename scenario
    renamed_pdf = _run_step_1_rename(pdf_path, routes)
    if renamed_pdf is None:
        return PipelineResult(
            success=False,
            steps_completed=steps_completed,
            error_message="Step 1 failed: scenario_renamer",
        )
    steps_completed = 1

    # Step 2: Extract chronicle
    chronicle_pdf = _run_step_2_chronicle(renamed_pdf, routes)
    if chronicle_pdf is None:
        return PipelineResult(
            success=False,
            steps_completed=steps_completed,
            error_message="Step 2 failed: chronicle_extractor",
        )
    steps_completed = 2

    # Step 3: Blueprint to layout (graceful skip on no blueprint)
    blueprint_ok = _run_step_3_blueprint(info, routes)
    if not blueprint_ok:
        return PipelineResult(
            success=False,
            steps_completed=steps_completed,
            error_message="Step 3 failed: blueprint2layout",
        )
    steps_completed = 3

    # Step 4: Generate layout
    layout_ok = _run_step_4_layout(chronicle_pdf, project_root, routes)
    if not layout_ok:
        return PipelineResult(
            success=False,
            steps_completed=steps_completed,
            error_message="Step 4 failed: layout_generator",
        )
    steps_completed = 4

    # Step 5: Visualize layout
    viz_ok = _run_step_5_visualize(routes, project_root)
    if not viz_ok:
        return PipelineResult(
            success=False,
            steps_completed=steps_completed,
            error_message="Step 5 failed: layout_visualizer",
        )
    steps_completed = 5

    print("Pipeline completed successfully!")
    return PipelineResult(success=True, steps_completed=steps_completed)
