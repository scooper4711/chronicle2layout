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
import difflib
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


def _suggest_layout_ids(unknown_id: str, layout_index: dict[str, Path]) -> str:
    """Build a suggestion string for an unrecognised layout id.

    Returns a human-readable hint containing close matches (if any)
    and the total number of known ids so the user knows where to look.
    """
    available = sorted(layout_index)
    close = difflib.get_close_matches(unknown_id, available, n=5, cutoff=0.4)
    parts: list[str] = []
    if close:
        parts.append("Did you mean one of these?")
        for match in close:
            parts.append(f"  - {match}")
    parts.append(
        f"Run with '--layout-id \"*\"' to list all "
        f"{len(available)} known layout ids."
    )
    return "\n".join(parts)


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
            hint = _suggest_layout_ids(pattern, layout_index)
            raise ValueError(
                f"--layout-id '{pattern}' not found\n{hint}"
            )
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
        hint = _suggest_layout_ids(layout_id, layout_index)
        raise ValueError(
            f"--layout-id '{layout_id}' not found in {layout_root}\n{hint}"
        )

    layout_path = layout_index[layout_id]
    pdf_path = resolve_chronicle_pdf(layout_id, layout_index)
    pixmap = render_pdf_page(pdf_path)

    if mode == "fields":
        fields, canvases, _chain = load_content_fields(layout_path, layout_index)
        canvas_pixels = resolve_canvas_pixels(canvases, pixmap.width, pixmap.height)
        pixel_rects = resolve_field_pixels(fields, canvas_pixels)
    elif mode == "data":
        entries, rectangles, checkboxes, strikeouts, canvases, _chain = load_data_content(layout_path, layout_index)
        canvas_pixels = resolve_canvas_pixels(canvases, pixmap.width, pixmap.height)
        composited = draw_data_text(pixmap, entries, canvas_pixels, rectangles, checkboxes, strikeouts)
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


def _build_dependency_map(
    layout_root: Path,
    layout_ids: list[str],
) -> dict[Path, set[str]]:
    """Map each watched file path to the layout ids that depend on it.

    Walks the inheritance chain of every layout id and records which
    ids include each file. A shared parent file maps to all children
    that inherit from it.

    Args:
        layout_root: Root directory containing layout JSON files.
        layout_ids: Layout ids to watch.

    Returns:
        Dictionary mapping file paths to sets of dependent layout ids.
    """
    layout_index = build_layout_index(layout_root)
    dep_map: dict[Path, set[str]] = {}
    for layout_id in layout_ids:
        layout_path = layout_index[layout_id]
        _canvases, chain_paths = load_layout_with_inheritance(
            layout_path, layout_index,
        )
        for path in chain_paths:
            dep_map.setdefault(path, set()).add(layout_id)
    return dep_map


def _record_mtimes(paths: list[Path]) -> dict[Path, float]:
    """Record the modification time of each file path.

    Args:
        paths: List of file paths to check.

    Returns:
        Dictionary mapping each path to its mtime.
    """
    return {path: os.path.getmtime(path) for path in paths}


def _find_changed_paths(
    paths: list[Path],
    previous_mtimes: dict[Path, float],
) -> list[Path]:
    """Return the watched paths whose mtime has changed.

    Args:
        paths: List of file paths to check.
        previous_mtimes: Previously recorded modification times.

    Returns:
        List of paths that have been modified since last check.
    """
    changed: list[Path] = []
    for path in paths:
        try:
            if os.path.getmtime(path) != previous_mtimes.get(path):
                changed.append(path)
        except OSError:
            continue
    return changed


def watch_and_regenerate(
    layout_root: Path,
    targets: list[tuple[str, Path]],
    mode: str = "canvases",
) -> None:
    """Watch layout files for changes and regenerate affected PNGs.

    Monitors the inheritance chains of all target layouts. When a
    watched file changes, only the targets that depend on that file
    are regenerated.

    Args:
        layout_root: Root directory containing layout JSON files.
        targets: List of (layout_id, output_path) pairs to generate.
        mode: What to visualize — "canvases", "fields", or "data".

    Requirements: layout-visualizer 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
    """
    target_map = {lid: out for lid, out in targets}

    for layout_id, output_path in targets:
        run_visualizer(layout_root, layout_id, output_path, mode)

    dep_map = _build_dependency_map(layout_root, list(target_map))
    watched_paths = list(dep_map)
    mtimes = _record_mtimes(watched_paths)

    try:
        while True:
            time.sleep(1)
            changed = _find_changed_paths(watched_paths, mtimes)
            if not changed:
                continue

            affected_ids: set[str] = set()
            for path in changed:
                affected_ids.update(dep_map.get(path, set()))

            affected_targets = [
                (lid, target_map[lid]) for lid in sorted(affected_ids)
            ]
            names = ", ".join(lid for lid, _ in affected_targets)
            print(f"Regenerating {names}...")

            mtimes = _record_mtimes(watched_paths)

            try:
                for layout_id, output_path in affected_targets:
                    run_visualizer(
                        layout_root, layout_id, output_path, mode,
                    )
                dep_map = _build_dependency_map(
                    layout_root, list(target_map),
                )
            except Exception as exc:  # noqa: BLE001 — continue watching on any error
                _print_error(f"Error: Regeneration failed: {exc}")

            watched_paths = list(dep_map)
            for new_path in watched_paths:
                if new_path not in mtimes:
                    try:
                        mtimes[new_path] = os.path.getmtime(new_path)
                    except OSError:
                        pass
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
