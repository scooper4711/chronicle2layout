"""CLI entry point for the blueprint2layout tool.

Provides parse_args for command-line argument parsing and main as the
entry point that validates inputs, runs the full pipeline via
generate_layout, and writes the output layout JSON file.
"""

import argparse
import fnmatch
import os
import sys
import time
from pathlib import Path

from blueprint2layout import generate_layout
from blueprint2layout.blueprint import build_blueprint_index
from blueprint2layout.output import write_layout
from shared.layout_index import collect_inheritance_chain


_RED = "\033[91m"
_RESET = "\033[0m"


def _print_error(message: str) -> None:
    """Print a red-highlighted error message to stderr."""
    print(f"{_RED}{message}{_RESET}", file=sys.stderr)


def match_blueprint_ids(
    pattern: str,
    blueprint_index: dict[str, Path],
) -> list[str]:
    """Return blueprint ids matching a shell-style wildcard pattern.

    If the pattern contains no wildcard characters it is treated as a
    literal id and must exist in the index.

    Args:
        pattern: A blueprint id or glob pattern (e.g. ``pfs2.b*``).
        blueprint_index: Map of blueprint ids to file paths.

    Returns:
        Sorted list of matching blueprint ids.

    Raises:
        ValueError: If no ids match the pattern.

    Requirements: blueprint-batch-watch 2.1, 2.2, 2.3, 2.4
    """
    has_wildcard = any(ch in pattern for ch in ("*", "?", "["))
    if has_wildcard:
        matched = sorted(
            bid for bid in blueprint_index if fnmatch.fnmatch(bid, pattern)
        )
    else:
        if pattern not in blueprint_index:
            raise ValueError(f"Blueprint id '{pattern}' not found")
        matched = [pattern]

    if not matched:
        raise ValueError(
            f"No blueprint ids match pattern '{pattern}'"
        )
    return matched


def resolve_default_chronicle_location(
    blueprint_path: Path,
    blueprint_index: dict[str, Path],
) -> str | None:
    """Walk the inheritance chain and return the defaultChronicleLocation.

    The leaf blueprint's value takes precedence. If the leaf doesn't
    define it, walks up the chain (child-first) until one is found.

    Args:
        blueprint_path: Path to the target (leaf) blueprint JSON file.
        blueprint_index: Map of blueprint ids to file paths.

    Returns:
        The defaultChronicleLocation string, or None if not defined
        anywhere in the chain.

    Requirements: blueprint-batch-watch 3.1, 3.2, 3.3
    """
    chain = collect_inheritance_chain(blueprint_path, blueprint_index)
    # chain is root-first; walk in reverse (leaf-first) so child wins
    for _path, data in reversed(chain):
        location = data.get("defaultChronicleLocation")
        if location is not None:
            return location
    return None


def resolve_chronicle_pdf(
    blueprint_id: str,
    blueprint_index: dict[str, Path],
) -> Path:
    """Resolve the chronicle PDF path for a blueprint id.

    Walks the inheritance chain to find ``defaultChronicleLocation``.

    Args:
        blueprint_id: The blueprint's unique identifier.
        blueprint_index: Map of blueprint ids to file paths.

    Returns:
        Path to the chronicle PDF.

    Raises:
        ValueError: If no ``defaultChronicleLocation`` is found.
        FileNotFoundError: If the resolved PDF does not exist.

    Requirements: blueprint-batch-watch 3.1, 3.2, 3.3, 3.4
    """
    blueprint_path = blueprint_index[blueprint_id]
    location = resolve_default_chronicle_location(blueprint_path, blueprint_index)
    if location is None:
        raise ValueError(
            f"Blueprint '{blueprint_id}' has no defaultChronicleLocation "
            f"in its inheritance chain"
        )
    pdf_path = Path(location)
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Chronicle PDF not found: {pdf_path} "
            f"(from blueprint '{blueprint_id}')"
        )
    return pdf_path


def derive_output_path(
    blueprint_id: str,
    blueprint_path: Path,
    blueprints_dir: Path,
    output_dir: Path,
) -> Path:
    """Compute the output file path for a generated layout.

    Strips the blueprint id prefix up to and including the first dot,
    appends ``.json`` for the filename, and mirrors the blueprint's
    subdirectory structure under the output directory.

    Args:
        blueprint_id: The blueprint's unique identifier (e.g.
            ``pfs2.bounty-layout-b13``).
        blueprint_path: Path to the blueprint JSON file.
        blueprints_dir: Root directory containing blueprint files.
        output_dir: Root directory for generated output files.

    Returns:
        Full output path (e.g.
        ``output_dir/bounties/bounty-layout-b13.json``).

    Requirements: blueprint-batch-watch 4.1, 4.2, 4.3
    """
    dot_index = blueprint_id.index(".")
    filename = blueprint_id[dot_index + 1:] + ".json"
    relative_subdir = blueprint_path.parent.relative_to(blueprints_dir)
    return output_dir / relative_subdir / filename


def run_single_layout(
    blueprints_dir: Path,
    blueprint_id: str,
    output_path: Path,
) -> None:
    """Orchestrate a single layout generation.

    Builds the blueprint index, resolves the chronicle PDF, runs the
    pipeline, creates the output directory, and writes the result.

    Args:
        blueprints_dir: Root directory containing blueprint files.
        blueprint_id: The blueprint's unique identifier.
        output_path: Path to write the generated layout JSON.

    Requirements: blueprint-batch-watch 5.1, 5.2
    """
    blueprint_index = build_blueprint_index(blueprints_dir)
    blueprint_path = blueprint_index[blueprint_id]
    pdf_path = resolve_chronicle_pdf(blueprint_id, blueprint_index)
    layout = generate_layout(blueprint_path, pdf_path, blueprints_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_layout(layout, output_path)
    print(f"Wrote {output_path}")


def _build_dependency_map(
    blueprints_dir: Path,
    blueprint_ids: list[str],
) -> dict[Path, set[str]]:
    """Map each watched file path to the blueprint ids that depend on it.

    Walks the inheritance chain of every blueprint id and records which
    ids include each file. A shared parent file maps to all children
    that inherit from it.

    Args:
        blueprints_dir: Root directory containing blueprint files.
        blueprint_ids: Blueprint ids to watch.

    Returns:
        Dictionary mapping file paths to sets of dependent blueprint ids.

    Requirements: blueprint-batch-watch 6.3
    """
    blueprint_index = build_blueprint_index(blueprints_dir)
    dep_map: dict[Path, set[str]] = {}
    for blueprint_id in blueprint_ids:
        blueprint_path = blueprint_index[blueprint_id]
        chain = collect_inheritance_chain(blueprint_path, blueprint_index)
        for path, _data in chain:
            dep_map.setdefault(path, set()).add(blueprint_id)
    return dep_map


def _record_mtimes(paths: list[Path]) -> dict[Path, float]:
    """Record the modification time of each file path.

    Args:
        paths: List of file paths to check.

    Returns:
        Dictionary mapping each path to its mtime.

    Requirements: blueprint-batch-watch 6.1, 6.2
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

    Requirements: blueprint-batch-watch 6.1, 6.2
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
    blueprints_dir: Path,
    targets: list[tuple[str, Path]],
) -> None:
    """Watch blueprint files for changes and regenerate affected layouts.

    Monitors the inheritance chains of all target blueprints. When a
    watched file changes, only the targets that depend on that file
    are regenerated.

    Args:
        blueprints_dir: Root directory containing blueprint files.
        targets: List of (blueprint_id, output_path) pairs to generate.

    Requirements: blueprint-batch-watch 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
    """
    target_map = {bid: out for bid, out in targets}

    for blueprint_id, output_path in targets:
        try:
            run_single_layout(blueprints_dir, blueprint_id, output_path)
        except Exception as exc:  # noqa: BLE001 — report and continue
            _print_error(f"Error ({blueprint_id}): {exc}")

    try:
        dep_map = _build_dependency_map(
            blueprints_dir, list(target_map),
        )
    except Exception as exc:  # noqa: BLE001 — report and continue
        _print_error(f"Error collecting watch paths: {exc}")
        dep_map = {}
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
                (bid, target_map[bid]) for bid in sorted(affected_ids)
            ]
            names = ", ".join(bid for bid, _ in affected_targets)
            print(f"Regenerating {names}...")

            for blueprint_id, output_path in affected_targets:
                try:
                    run_single_layout(
                        blueprints_dir, blueprint_id, output_path,
                    )
                except Exception as exc:  # noqa: BLE001 — report and continue
                    _print_error(f"Error ({blueprint_id}): {exc}")

            try:
                dep_map = _build_dependency_map(
                    blueprints_dir, list(target_map),
                )
            except Exception as exc:  # noqa: BLE001 — keep previous map
                _print_error(f"Error collecting watch paths: {exc}")

            watched_paths = list(dep_map)
            mtimes = _record_mtimes(watched_paths)
    except KeyboardInterrupt:
        print("Stopped.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for blueprint2layout.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with blueprints_dir, blueprint_id, output_dir,
        and watch.

    Requirements: blueprint-batch-watch 1.1, 1.2, 1.3, 1.4, 1.5
    """
    parser = argparse.ArgumentParser(
        prog="blueprint2layout",
        description=(
            "Convert Blueprint JSON files into layout JSON files.  "
            "The chronicle PDF is resolved automatically from the "
            "blueprint's defaultChronicleLocation field."
        ),
    )
    parser.add_argument(
        "--blueprints-dir",
        type=Path,
        required=True,
        help="Root directory containing Blueprint JSON files.",
    )
    parser.add_argument(
        "--blueprint-id",
        required=True,
        help=(
            "Blueprint id to process.  Supports shell-style wildcards "
            "(e.g. 'pfs2.*') to generate layouts for multiple blueprints."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory for output layout JSON files (default: current directory).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        default=False,
        help="Watch blueprint files for changes and auto-regenerate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the blueprint2layout CLI.

    Validates inputs, resolves matching blueprint ids, derives output
    paths, and runs the layout pipeline for each match. Prints errors
    to stderr and returns an appropriate exit code.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for errors.

    Requirements: blueprint-batch-watch 1.1–1.5, 5.1, 5.2, 5.3, 7.1–7.4
    """
    args = parse_args(argv)

    if not args.blueprints_dir.is_dir():
        _print_error(
            f"Error: Blueprints directory is not a directory: {args.blueprints_dir}"
        )
        return 1

    try:
        blueprint_index = build_blueprint_index(args.blueprints_dir)
        matched_ids = match_blueprint_ids(args.blueprint_id, blueprint_index)
    except ValueError as exc:
        _print_error(f"Error: {exc}")
        return 1

    try:
        targets: list[tuple[str, Path]] = []
        for blueprint_id in matched_ids:
            blueprint_path = blueprint_index[blueprint_id]
            output_path = derive_output_path(
                blueprint_id, blueprint_path,
                args.blueprints_dir, args.output_dir,
            )
            targets.append((blueprint_id, output_path))

        if args.watch:
            watch_and_regenerate(args.blueprints_dir, targets)
            return 0

        for blueprint_id, output_path in targets:
            run_single_layout(
                args.blueprints_dir, blueprint_id, output_path,
            )
    except (ValueError, FileNotFoundError, OSError) as exc:
        _print_error(f"Error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
