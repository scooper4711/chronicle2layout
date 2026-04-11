"""CLI entry point for the scenario download workflow.

Discovers recently downloaded PDFs, prompts for confirmation,
detects game system, extracts scenario info, and runs the
five-step processing pipeline for each confirmed PDF.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF

from chronicle_extractor.parser import extract_scenario_info
from scenario_download_workflow.detection import detect_game_system
from scenario_download_workflow.discovery import discover_recent_pdfs
from scenario_download_workflow.duration import parse_duration
from scenario_download_workflow.pipeline import process_single_pdf
from scenario_download_workflow.routing import compute_routing_paths


def classify_response(response: str) -> str:
    """Classify a user's interactive confirmation response.

    Args:
        response: Raw user input string.

    Returns:
        One of "accept", "skip", "quit", or "invalid".
    """
    normalized = response.strip().lower()
    if normalized in ("y", "yes"):
        return "accept"
    if normalized in ("n", "no"):
        return "skip"
    if normalized in ("q", "quit"):
        return "quit"
    return "invalid"


def compute_exit_code(success_count: int, fail_count: int) -> int:  # noqa: ARG001
    """Determine the process exit code from processing outcomes.

    Args:
        success_count: Number of PDFs processed successfully.
        fail_count: Number of PDFs that failed processing (kept for API symmetry).

    Returns:
        0 if at least one PDF succeeded, 1 otherwise.
    """
    return 0 if success_count > 0 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the scenario download workflow.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with downloads_dir, project_dir, recent, non_interactive.
    """
    parser = argparse.ArgumentParser(
        prog="scenario_download_workflow",
        description="Process recently downloaded scenario PDFs.",
    )
    parser.add_argument(
        "--downloads-dir",
        type=Path,
        default=Path.home() / "Downloads",
        help="Directory to scan for PDFs (default: ~/Downloads)",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="PFS Tools project root (default: current directory)",
    )
    parser.add_argument(
        "--recent",
        type=parse_duration,
        default=parse_duration("1h"),
        help="Recency window for PDF discovery (default: 1h)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=False,
        help="Process all discovered PDFs without prompting",
    )
    return parser.parse_args(argv)


def _read_page_text(doc: fitz.Document, page_index: int) -> str | None:
    """Read text from a specific page, returning None if out of range."""
    if page_index < 0 or page_index >= len(doc):
        return None
    return doc[page_index].get_text()


def _process_pdf(
    pdf_path: Path,
    project_dir: Path,
) -> str:
    """Process a single PDF through detection, extraction, routing, and pipeline.

    Returns:
        "success", "fail", or "skip" indicating the outcome.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        print(f"Error: cannot open {pdf_path.name}: {exc}", file=sys.stderr)
        return "fail"

    try:
        first_page_text = _read_page_text(doc, 0) or ""

        # Try page 1 first; newer PDFs have a cover page without the
        # society name, so fall back to page 2 if needed.
        system = detect_game_system(first_page_text)
        if system is None:
            second_page_text = _read_page_text(doc, 1) or ""
            system = detect_game_system(second_page_text)
        if system is None:
            print(
                f"Warning: cannot detect game system for {pdf_path.name}, skipping",
                file=sys.stderr,
            )
            return "skip"

        print(f"Processing {pdf_path.name} ({system.value.upper()})...")

        page3_text = _read_page_text(doc, 2)
        page4_text = _read_page_text(doc, 3)
        page5_text = _read_page_text(doc, 4)
        last_page_text = _read_page_text(doc, len(doc) - 1)

        info = extract_scenario_info(
            first_page_text,
            page3_text=page3_text,
            page4_text=page4_text,
            page5_text=page5_text,
            last_page_text=last_page_text,
        )
        if info is None:
            print(
                f"Warning: cannot extract scenario info from {pdf_path.name}, skipping",
                file=sys.stderr,
            )
            return "skip"

        routes = compute_routing_paths(project_dir, system, info)
        result = process_single_pdf(pdf_path, project_dir, system, info, routes)

        return "success" if result.success else "fail"
    finally:
        doc.close()


def _confirm_pdf(pdf_path: Path) -> str:
    """Prompt the user for interactive confirmation on a single PDF.

    Returns:
        "accept", "skip", or "quit".
    """
    response = input(f"Process {pdf_path.name}? [y/n/q] ")
    action = classify_response(response)
    if action == "invalid":
        print(f"Invalid response: {response!r}, skipping {pdf_path.name}")
        return "skip"
    return action


def _tally_outcome(
    outcome: str,
    counts: list[int],
) -> None:
    """Update [success, skip, fail] counts based on outcome string."""
    if outcome == "success":
        counts[0] += 1
    elif outcome == "fail":
        counts[2] += 1
    else:
        counts[1] += 1


def _process_all_pdfs(
    pdfs: list[Path],
    project_dir: Path,
    non_interactive: bool,
) -> tuple[int, int, int]:
    """Iterate over PDFs, optionally confirming each, and process them.

    Returns:
        (success_count, skip_count, fail_count) tuple.
    """
    counts = [0, 0, 0]  # success, skip, fail

    for pdf_path in pdfs:
        if not non_interactive:
            action = _confirm_pdf(pdf_path)
            if action == "skip":
                counts[1] += 1
                continue
            if action == "quit":
                remaining = len(pdfs) - sum(counts)
                counts[1] += remaining
                break

        outcome = _process_pdf(pdf_path, project_dir)
        _tally_outcome(outcome, counts)

    return counts[0], counts[1], counts[2]


def main(argv: list[str] | None = None) -> int:
    """Entry point: discover PDFs, confirm, detect, extract info, run pipeline.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 if at least one PDF processed, 1 if none processed,
        0 if no PDFs found.
    """
    args = parse_args(argv)

    pdfs = discover_recent_pdfs(args.downloads_dir, args.recent)

    if not pdfs:
        print(
            f"No recent PDFs found in {args.downloads_dir} "
            f"(window: {args.recent})"
        )
        return 0

    success_count, skip_count, fail_count = _process_all_pdfs(
        pdfs, args.project_dir, args.non_interactive,
    )

    print(
        f"Summary: {success_count} processed, "
        f"{skip_count} skipped, {fail_count} failed"
    )

    return compute_exit_code(success_count, fail_count)


if __name__ == "__main__":
    sys.exit(main())
