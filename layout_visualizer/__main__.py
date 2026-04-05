"""CLI entry point for the layout_visualizer package.

Invoked via ``python -m layout_visualizer``. Parses command-line arguments,
runs the visualization pipeline, and optionally watches for file changes.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from layout_visualizer.coordinate_resolver import (
    assign_colors,
    resolve_canvas_pixels,
    resolve_field_pixels,
)
from layout_visualizer.layout_loader import (
    build_layout_index,
    load_content_fields,
    load_layout_with_inheritance,
)
from layout_visualizer.overlay_renderer import draw_overlays
from layout_visualizer.pdf_renderer import render_pdf_page


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for layout_visualizer.

    Positional: layout_file, pdf_file.
    Optional positional: output (PNG path).
    Optional flag: --watch.

    When no output path is given, the default is the layout file's
    directory with the same base name and a ``.png`` extension.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with layout_file and pdf_file as Paths,
        output as Path or None, and watch as bool.

    Requirements: layout-visualizer 1.1, 1.2, 1.3, 1.4, 1.6
    """
    parser = argparse.ArgumentParser(
        prog="layout_visualizer",
        description="Visualize canvas regions from a layout JSON on a chronicle PDF.",
    )
    parser.add_argument(
        "--layout-root",
        type=Path,
        required=True,
        help="Root directory containing layout JSON files.",
    )
    parser.add_argument(
        "--layout-id",
        required=True,
        help="Layout id to visualize (e.g. 'pfs2.season7').",
    )
    parser.add_argument(
        "pdf_file",
        type=Path,
        help="Path to the chronicle PDF file.",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=None,
        help="Output PNG file path (default: <layout_id>.png in current directory).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        default=False,
        help="Watch layout files for changes and auto-regenerate.",
    )
    parser.add_argument(
        "--mode",
        choices=["canvases", "fields"],
        default="canvases",
        help="What to visualize: 'canvases' draws canvas regions, "
             "'fields' draws content field positions (default: canvases).",
    )

    args = parser.parse_args(argv)

    if args.output is None:
        args.output = Path(f"{args.layout_id}.png")

    return args


def run_visualizer(
    layout_root: Path,
    layout_id: str,
    pdf_path: Path,
    output_path: Path,
    mode: str = "canvases",
) -> None:
    """Run the full visualization pipeline once.

    Builds a layout index from layout_root, looks up the layout by id,
    resolves inheritance, renders the PDF, draws overlays, and writes PNG.

    Args:
        layout_root: Root directory containing layout JSON files.
        layout_id: Layout id to visualize.
        pdf_path: Path to the chronicle PDF.
        output_path: Path for the output PNG file.
        mode: What to visualize — "canvases" or "fields".

    Raises:
        FileNotFoundError: If PDF not found or layout id not in index.
        ValueError: If layout JSON is invalid or parent not found.
        OSError: If output path is not writable.

    Requirements: layout-visualizer 1.1, 1.2, 1.3, 1.4, 8.1, 8.2
    """
    layout_index = build_layout_index(layout_root)

    if layout_id not in layout_index:
        raise ValueError(
            f"Layout id '{layout_id}' not found in {layout_root}"
        )

    layout_path = layout_index[layout_id]
    pixmap = render_pdf_page(pdf_path)

    if mode == "fields":
        fields, canvases, _chain = load_content_fields(layout_path, layout_index)
        canvas_pixels = resolve_canvas_pixels(canvases, pixmap.width, pixmap.height)
        pixel_rects = resolve_field_pixels(fields, canvas_pixels)
    else:
        canvases, _chain = load_layout_with_inheritance(layout_path, layout_index)
        pixel_rects = resolve_canvas_pixels(canvases, pixmap.width, pixmap.height)

    colors = assign_colors(list(pixel_rects.keys()))
    composited = draw_overlays(pixmap, pixel_rects, colors)
    composited.save(str(output_path))


def _collect_watched_paths(layout_root: Path, layout_id: str) -> list[Path]:
    """Build the list of layout file paths to monitor for changes.

    Args:
        layout_root: Root directory containing layout JSON files.
        layout_id: Layout id to visualize.

    Returns:
        List of all layout file paths in the inheritance chain.
    """
    layout_index = build_layout_index(layout_root)
    layout_path = layout_index[layout_id]
    _canvases, chain_paths = load_layout_with_inheritance(layout_path, layout_index)
    return chain_paths


def _record_mtimes(paths: list[Path]) -> dict[Path, float]:
    """Record the modification time of each file path.

    Args:
        paths: List of file paths to check.

    Returns:
        Dictionary mapping each path to its mtime.
    """
    return {path: os.path.getmtime(path) for path in paths}


def _any_file_changed(
    paths: list[Path],
    previous_mtimes: dict[Path, float],
) -> bool:
    """Check whether any monitored file has been modified.

    Args:
        paths: List of file paths to check.
        previous_mtimes: Previously recorded modification times.

    Returns:
        True if any file's mtime differs from the recorded value.
    """
    for path in paths:
        try:
            if os.path.getmtime(path) != previous_mtimes.get(path):
                return True
        except OSError:
            continue
    return False


def watch_and_regenerate(
    layout_root: Path,
    layout_id: str,
    pdf_path: Path,
    output_path: Path,
    mode: str = "canvases",
) -> None:
    """Watch layout files for changes and regenerate PNG.

    Args:
        layout_root: Root directory containing layout JSON files.
        layout_id: Layout id to visualize.
        pdf_path: Path to the chronicle PDF.
        output_path: Path for the output PNG file.
        mode: What to visualize — "canvases" or "fields".

    Requirements: layout-visualizer 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
    """
    run_visualizer(layout_root, layout_id, pdf_path, output_path, mode)

    watched_paths = _collect_watched_paths(layout_root, layout_id)
    mtimes = _record_mtimes(watched_paths)

    try:
        while True:
            time.sleep(1)
            if not _any_file_changed(watched_paths, mtimes):
                continue

            print("Regenerating...")
            try:
                run_visualizer(layout_root, layout_id, pdf_path, output_path, mode)
                watched_paths = _collect_watched_paths(layout_root, layout_id)
            except Exception as exc:  # noqa: BLE001 — continue watching on any error
                print(f"Error: Regeneration failed: {exc}", file=sys.stderr)

            mtimes = _record_mtimes(watched_paths)
    except KeyboardInterrupt:
        print("Stopped.")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the layout_visualizer CLI.

    Parses arguments, validates file existence, and runs the
    visualization pipeline. Prints errors to stderr and returns
    an appropriate exit code.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for errors.

    Requirements: layout-visualizer 1.5, 8.2, 8.3, 9.1, 9.2, 9.3, 9.4
    """
    args = parse_args(argv)

    if not args.layout_root.is_dir():
        print(
            f"Error: Layout root is not a directory: {args.layout_root}",
            file=sys.stderr,
        )
        return 1

    if not args.pdf_file.exists():
        print(
            f"Error: PDF file not found: {args.pdf_file}",
            file=sys.stderr,
        )
        return 1

    try:
        if args.watch:
            watch_and_regenerate(
                args.layout_root, args.layout_id,
                args.pdf_file, args.output, args.mode,
            )
            return 0
        run_visualizer(
            args.layout_root, args.layout_id,
            args.pdf_file, args.output, args.mode,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
