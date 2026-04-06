"""CLI entry point for the layout_visualizer package.

Invoked via ``python -m layout_visualizer``. Parses command-line arguments,
runs the visualization pipeline, and optionally watches for file changes.

The chronicle PDF is resolved automatically from the layout's
``defaultChronicleLocation`` field (walking the inheritance chain).
``--layout-id`` supports shell-style wildcards (e.g. ``pfs.b*``) to
generate PNGs for multiple layouts in one invocation.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
import time
from pathlib import Path

_RED = "\033[91m"
_RESET = "\033[0m"


def _print_error(message: str) -> None:
    """Print a red-highlighted error message to stderr."""
    print(f"{_RED}{message}{_RESET}", file=sys.stderr)


from layout_visualizer.coordinate_resolver import (
    assign_colors,
    resolve_canvas_pixels,
    resolve_field_pixels,
)
from layout_visualizer.data_renderer import draw_data_text
from layout_visualizer.layout_loader import (
    build_layout_index,
    load_content_fields,
    load_data_content,
    load_layout_with_inheritance,
    resolve_default_chronicle_location,
)
from layout_visualizer.overlay_renderer import draw_overlays
from layout_visualizer.pdf_renderer import render_pdf_page


def _build_output_filename(layout_id: str, chronicle_path: Path) -> str:
    """Derive the output PNG filename from a layout id and chronicle PDF.

    Format: ``{layout_id}_{chronicle_stem}.png``.  The layout id is
    included because multiple layouts can reference the same chronicle.

    Args:
        layout_id: The layout's unique identifier.
        chronicle_path: Path to the chronicle PDF.

    Returns:
        The output filename string (no directory component).
    """
    return f"{layout_id}_{chronicle_path.stem}.png"


def match_layout_ids(
    pattern: str,
    layout_index: dict[str, Path],
) -> list[str]:
    """Return layout ids matching a shell-style wildcard pattern.

    If the pattern contains no wildcard characters it is treated as a
    literal id and must exist in the index.

    Args:
        pattern: A layout id or glob pattern (e.g. ``pfs.b*``).
        layout_index: Map of layout ids to file paths.

    Returns:
        Sorted list of matching layout ids.

    Raises:
        ValueError: If no ids match the pattern.
    """
    has_wildcard = any(ch in pattern for ch in ("*", "?", "["))
    if has_wildcard:
        matched = sorted(
            lid for lid in layout_index if fnmatch.fnmatch(lid, pattern)
        )
    else:
        if pattern not in layout_index:
            raise ValueError(f"Layout id '{pattern}' not found")
        matched = [pattern]

    if not matched:
        raise ValueError(
            f"No layout ids match pattern '{pattern}'"
        )
    return matched


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for layout_visualizer.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with layout_root, layout_id, output_dir,
        watch, and mode.

    Requirements: layout-visualizer 1.1, 1.3, 1.4, 1.6
    """
    parser = argparse.ArgumentParser(
        prog="layout_visualizer",
        description=(
            "Visualize canvas regions from a layout JSON on its "
            "chronicle PDF.  The PDF is resolved from the layout's "
            "defaultChronicleLocation field."
        ),
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
        help=(
            "Layout id to visualize.  Supports shell-style wildcards "
            "(e.g. 'pfs.b*') to generate PNGs for multiple layouts."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory for output PNG files (default: current directory).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        default=False,
        help="Watch layout files for changes and auto-regenerate.",
    )
    parser.add_argument(
        "--mode",
        choices=["canvases", "fields", "data"],
        default="canvases",
        help=(
            "What to visualize: 'canvases' draws canvas regions, "
            "'fields' draws content field positions, "
            "'data' renders example parameter values as text "
            "(default: canvases)."
        ),
    )

    return parser.parse_args(argv)


def resolve_chronicle_pdf(
    layout_id: str,
    layout_index: dict[str, Path],
) -> Path:
    """Resolve the chronicle PDF path for a layout id.

    Walks the inheritance chain to find ``defaultChronicleLocation``.

    Args:
        layout_id: The layout's unique identifier.
        layout_index: Map of layout ids to file paths.

    Returns:
        Path to the chronicle PDF.

    Raises:
        ValueError: If no ``defaultChronicleLocation`` is found.
        FileNotFoundError: If the resolved PDF does not exist.
    """
    layout_path = layout_index[layout_id]
    location = resolve_default_chronicle_location(layout_path, layout_index)
    if location is None:
        raise ValueError(
            f"Layout '{layout_id}' has no defaultChronicleLocation "
            f"in its inheritance chain"
        )
    pdf_path = Path(location)
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Chronicle PDF not found: {pdf_path} "
            f"(from layout '{layout_id}')"
        )
    return pdf_path


def run_visualizer(
    layout_root: Path,
    layout_id: str,
    output_path: Path,
    mode: str = "canvases",
) -> None:
    """Run the full visualization pipeline once.

    Builds a layout index from layout_root, looks up the layout by id,
    resolves the chronicle PDF from ``defaultChronicleLocation``,
    renders the PDF, draws overlays, and writes PNG.

    Args:
        layout_root: Root directory containing layout JSON files.
        layout_id: Layout id to visualize.
        output_path: Path for the output PNG file.
        mode: What to visualize — "canvases", "fields", or "data".

    Raises:
        FileNotFoundError: If PDF not found or layout id not in index.
        ValueError: If layout JSON is invalid or parent not found.
        OSError: If output path is not writable.

    Requirements: layout-visualizer 1.1–1.4, 8.1, 8.2
    """
    layout_index = build_layout_index(layout_root)

    if layout_id not in layout_index:
        raise ValueError(
            f"Layout id '{layout_id}' not found in {layout_root}"
        )

    layout_path = layout_index[layout_id]
    pdf_path = resolve_chronicle_pdf(layout_id, layout_index)
    pixmap = render_pdf_page(pdf_path)

    if mode == "fields":
        fields, canvases, _chain = load_content_fields(layout_path, layout_index)
        canvas_pixels = resolve_canvas_pixels(canvases, pixmap.width, pixmap.height)
        pixel_rects = resolve_field_pixels(fields, canvas_pixels)
    elif mode == "data":
        entries, canvases, _chain = load_data_content(layout_path, layout_index)
        canvas_pixels = resolve_canvas_pixels(canvases, pixmap.width, pixmap.height)
        composited = draw_data_text(pixmap, entries, canvas_pixels)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        composited.save(str(output_path))
        print(f"Wrote {output_path}")
        return
    else:
        canvases, _chain = load_layout_with_inheritance(layout_path, layout_index)
        pixel_rects = resolve_canvas_pixels(canvases, pixmap.width, pixmap.height)

    colors = assign_colors(list(pixel_rects.keys()))
    composited = draw_overlays(pixmap, pixel_rects, colors)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    composited.save(str(output_path))
    print(f"Wrote {output_path}")


def _collect_watched_paths(
    layout_root: Path,
    layout_ids: list[str],
) -> list[Path]:
    """Build the deduplicated list of layout file paths to monitor.

    Unions the inheritance chains of all provided layout ids so that
    a change to any file in any chain triggers regeneration.

    Args:
        layout_root: Root directory containing layout JSON files.
        layout_ids: Layout ids to watch.

    Returns:
        Deduplicated list of all layout file paths across all chains.
    """
    layout_index = build_layout_index(layout_root)
    seen: set[Path] = set()
    result: list[Path] = []
    for layout_id in layout_ids:
        layout_path = layout_index[layout_id]
        _canvases, chain_paths = load_layout_with_inheritance(
            layout_path, layout_index,
        )
        for path in chain_paths:
            if path not in seen:
                seen.add(path)
                result.append(path)
    return result


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
    targets: list[tuple[str, Path]],
    mode: str = "canvases",
) -> None:
    """Watch layout files for changes and regenerate PNGs.

    Monitors the inheritance chains of all target layouts. When any
    watched file changes, every target is regenerated.

    Args:
        layout_root: Root directory containing layout JSON files.
        targets: List of (layout_id, output_path) pairs to generate.
        mode: What to visualize — "canvases", "fields", or "data".

    Requirements: layout-visualizer 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
    """
    layout_ids = [lid for lid, _ in targets]

    for layout_id, output_path in targets:
        run_visualizer(layout_root, layout_id, output_path, mode)

    watched_paths = _collect_watched_paths(layout_root, layout_ids)
    mtimes = _record_mtimes(watched_paths)

    try:
        while True:
            time.sleep(1)
            if not _any_file_changed(watched_paths, mtimes):
                continue

            print("Regenerating...")
            try:
                for layout_id, output_path in targets:
                    run_visualizer(
                        layout_root, layout_id, output_path, mode,
                    )
                watched_paths = _collect_watched_paths(
                    layout_root, layout_ids,
                )
            except Exception as exc:  # noqa: BLE001 — continue watching on any error
                _print_error(f"Error: Regeneration failed: {exc}")

            mtimes = _record_mtimes(watched_paths)
    except KeyboardInterrupt:
        print("Stopped.")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the layout_visualizer CLI.

    Parses arguments, validates inputs, resolves matching layout ids,
    and runs the visualization pipeline for each match. Prints errors
    to stderr and returns an appropriate exit code.

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

    try:
        layout_index = build_layout_index(args.layout_root)
        matched_ids = match_layout_ids(args.layout_id, layout_index)
    except ValueError as exc:
        _print_error(f"Error: {exc}")
        return 1

    try:
        targets: list[tuple[str, Path]] = []
        for layout_id in matched_ids:
            pdf_path = resolve_chronicle_pdf(layout_id, layout_index)
            output_name = _build_output_filename(layout_id, pdf_path)
            layout_file = layout_index[layout_id]
            sub_dir = layout_file.parent.relative_to(args.layout_root)
            output_path = args.output_dir / sub_dir / output_name
            targets.append((layout_id, output_path))

        if args.watch:
            watch_and_regenerate(
                args.layout_root, targets, args.mode,
            )
            return 0

        for layout_id, output_path in targets:
            run_visualizer(
                args.layout_root, layout_id,
                output_path, args.mode,
            )
    except FileNotFoundError as exc:
        _print_error(f"Error: {exc}")
        return 1
    except ValueError as exc:
        _print_error(f"Error: {exc}")
        return 1
    except OSError as exc:
        _print_error(f"Error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
