"""CLI entry point for the layout_generator package.

Invoked via ``python -m layout_generator``. Parses command-line arguments,
loads TOML metadata, resolves canvas regions from parent layouts via
``shared.layout_index``, and orchestrates batch PDF processing.

Requirements: layout-generator 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7,
    1.8, 1.9, 3.1, 3.2, 3.3, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2,
    10.3, 10.4, 10.5, 10.6, 13.1, 13.2, 13.3, 13.4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from layout_generator.generator import generate_layout_json
from layout_generator.metadata import (
    MatchedMetadata,
    load_metadata,
    match_rule,
)
from shared.layout_index import build_json_index, collect_inheritance_chain


def resolve_canvas_region(
    canvas_name: str,
    parent_id: str,
    layout_index: dict[str, Path],
) -> list[float] | None:
    """Resolve a canvas to absolute page percentages via inheritance chain.

    Walks the parent layout chain, merges canvas definitions, then
    converts the target canvas's relative percentages to absolute
    page percentages by walking the canvas parent chain.

    Args:
        canvas_name: Name of the canvas to resolve (e.g. "items").
        parent_id: Parent layout id to start from.
        layout_index: Map of layout ids to file paths.

    Returns:
        [x0, y0, x1, y1] as absolute page percentages, or None
        if the canvas is not found.

    Requirements: layout-generator 3.1, 3.2, 3.3
    """
    if parent_id not in layout_index:
        return None

    layout_path = layout_index[parent_id]
    chain = collect_inheritance_chain(layout_path, layout_index)

    # Merge canvas definitions from root to leaf (child overrides parent)
    canvases: dict[str, dict] = {}
    for _path, data in chain:
        for name, props in data.get("canvas", {}).items():
            canvases[name] = props

    if canvas_name not in canvases:
        return None

    # Walk the canvas parent chain to compose absolute page percentages.
    # Start from the target canvas and walk up to the implicit page root.
    return _compose_absolute_coordinates(canvas_name, canvases)


def _compose_absolute_coordinates(
    canvas_name: str,
    canvases: dict[str, dict],
) -> list[float]:
    """Walk the canvas parent chain and compose absolute page percentages.

    Each canvas defines x, y, x2, y2 as percentages relative to its
    parent canvas. The implicit root is the full page (0, 0, 100, 100).

    Args:
        canvas_name: Target canvas to resolve.
        canvases: Merged canvas definitions from the inheritance chain.

    Returns:
        [x0, y0, x1, y1] as absolute page percentages.
    """
    # Build the chain from target canvas up to root
    chain: list[dict] = []
    current = canvas_name
    while current is not None and current in canvases:
        props = canvases[current]
        chain.append(props)
        current = props.get("parent")

    # Start with the full page as the absolute reference
    abs_x0, abs_y0, abs_x2, abs_y2 = 0.0, 0.0, 100.0, 100.0

    # Walk from root canvas down to target, composing coordinates
    for props in reversed(chain):
        parent_width = abs_x2 - abs_x0
        parent_height = abs_y2 - abs_y0
        rel_x = float(props["x"])
        rel_y = float(props["y"])
        rel_x2 = float(props["x2"])
        rel_y2 = float(props["y2"])
        new_x0 = abs_x0 + rel_x / 100.0 * parent_width
        new_y0 = abs_y0 + rel_y / 100.0 * parent_height
        new_x2 = abs_x0 + rel_x2 / 100.0 * parent_width
        new_y2 = abs_y0 + rel_y2 / 100.0 * parent_height
        abs_x0, abs_y0, abs_x2, abs_y2 = new_x0, new_y0, new_x2, new_y2

    return [abs_x0, abs_y0, abs_x2, abs_y2]



def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.

    Requirements: layout-generator 1.1–1.9
    """
    parser = argparse.ArgumentParser(
        prog="layout_generator",
        description=(
            "Generate leaf layout JSON files from chronicle PDFs "
            "and a TOML metadata file."
        ),
    )
    parser.add_argument(
        "pdf_path",
        help="Path to a single chronicle PDF or a directory of PDFs.",
    )
    parser.add_argument(
        "--metadata-file",
        default="chronicle_properties.toml",
        help=(
            "Path to the TOML metadata file "
            "(default: chronicle_properties.toml)."
        ),
    )
    parser.add_argument(
        "--layouts-dir",
        default=None,
        help=(
            "Root directory containing parent layout files. "
            "Falls back to layouts_dir in the TOML metadata file."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for generated layout JSON files "
            "(default: resolved --layouts-dir)."
        ),
    )
    parser.add_argument(
        "--item-canvas",
        default="items",
        help="Canvas name for item extraction (default: items).",
    )
    parser.add_argument(
        "--checkbox-canvas",
        default="summary",
        help="Canvas name for checkbox detection (default: summary).",
    )
    return parser.parse_args(argv)


def _resolve_layouts_dir(
    args: argparse.Namespace,
    toml_layouts_dir: str | None,
) -> Path | None:
    """Determine the layouts directory from CLI args or TOML config.

    Returns None if neither source provides a value.
    """
    if args.layouts_dir is not None:
        return Path(args.layouts_dir)
    if toml_layouts_dir is not None:
        return Path(toml_layouts_dir)
    return None


def _collect_pdf_files(pdf_path: Path) -> list[Path]:
    """Collect PDF files from a path (single file or directory)."""
    if pdf_path.is_file():
        return [pdf_path]
    return sorted(pdf_path.rglob("*.pdf"))


def _relative_path_for_matching(
    pdf_file: Path,
    pdf_path: Path,
) -> str:
    """Compute the relative path string used for rule matching.

    For directory mode, returns the path relative to the base directory.
    For single-file mode, returns just the filename.
    """
    if pdf_path.is_dir():
        return str(pdf_file.relative_to(pdf_path))
    return pdf_file.name


def _derive_output_file(
    pdf_file: Path,
    pdf_base: Path,
    metadata: MatchedMetadata,
    output_dir: Path,
) -> Path:
    """Derive the output file path, mirroring the PDF's subdirectory structure.

    For directory mode the PDF's relative subdirectory is preserved under
    output_dir.  For single-file mode the file lands directly in output_dir.
    """
    if pdf_base.is_dir():
        relative_parent = pdf_file.relative_to(pdf_base).parent
    else:
        relative_parent = Path(".")
    return output_dir / relative_parent / f"{metadata.id}.json"


def _process_single_pdf(
    pdf_file: Path,
    pdf_base: Path,
    metadata: MatchedMetadata,
    layout_index: dict[str, Path],
    item_canvas: str,
    checkbox_canvas: str,
    output_dir: Path,
) -> Path | None:
    """Process a single PDF: resolve canvases, generate layout, write JSON.

    Returns the output path on success, or None on failure.
    """
    item_region = resolve_canvas_region(
        item_canvas, metadata.parent, layout_index,
    )
    if item_region is None:
        print(
            f"Warning: Canvas '{item_canvas}' not found for "
            f"layout '{metadata.id}'; skipping item extraction.",
            file=sys.stderr,
        )

    checkbox_region = resolve_canvas_region(
        checkbox_canvas, metadata.parent, layout_index,
    )
    if checkbox_region is None:
        print(
            f"Warning: Canvas '{checkbox_canvas}' not found for "
            f"layout '{metadata.id}'; skipping checkbox detection.",
            file=sys.stderr,
        )

    layout = generate_layout_json(
        pdf_path=pdf_file,
        item_region_pct=item_region,
        checkbox_region_pct=checkbox_region,
        item_canvas_name=item_canvas,
        checkbox_canvas_name=checkbox_canvas,
        scenario_id=metadata.id,
        parent=metadata.parent,
        description=metadata.description,
        default_chronicle_location=metadata.default_chronicle_location,
    )

    output_file = _derive_output_file(pdf_file, pdf_base, metadata, output_dir)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(layout, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_file


def main(argv: list[str] | None = None) -> int:
    """Entry point for the layout generator CLI.

    Loads metadata, builds layout index, resolves canvases,
    processes PDFs, and writes output files.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 when at least one layout generated, 1 otherwise.

    Requirements: layout-generator 1.9, 9.1–9.5, 10.1–10.6, 13.1–13.4
    """
    args = parse_args(argv)
    pdf_path = Path(args.pdf_path)

    if not pdf_path.exists():
        print(
            f"Error: pdf_path does not exist: {pdf_path}",
            file=sys.stderr,
        )
        return 1

    # Load metadata
    metadata_path = Path(args.metadata_file)
    try:
        config = load_metadata(metadata_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Resolve layouts directory
    layouts_dir = _resolve_layouts_dir(args, config.layouts_dir)
    if layouts_dir is None:
        print(
            "Error: No layouts directory specified. Provide "
            "--layouts-dir or set layouts_dir in the metadata file.",
            file=sys.stderr,
        )
        return 1

    if not layouts_dir.is_dir():
        print(
            f"Error: Layouts directory does not exist: {layouts_dir}",
            file=sys.stderr,
        )
        return 1

    # Resolve output directory
    output_dir = Path(args.output_dir) if args.output_dir else layouts_dir

    # Build layout index
    layout_index = build_json_index(layouts_dir)

    # Collect PDF files
    pdf_files = _collect_pdf_files(pdf_path)

    generated_count = 0
    skipped_count = 0

    for pdf_file in pdf_files:
        relative = _relative_path_for_matching(pdf_file, pdf_path)
        metadata = match_rule(relative, config)

        if metadata is None:
            print(
                f"Warning: No matching rule for '{relative}'; skipping.",
                file=sys.stderr,
            )
            skipped_count += 1
            continue

        if metadata.parent not in layout_index:
            print(
                f"Error: Parent layout '{metadata.parent}' not found "
                f"in layout index for '{metadata.id}'; skipping.",
                file=sys.stderr,
            )
            skipped_count += 1
            continue

        try:
            output_file = _process_single_pdf(
                pdf_file,
                pdf_path,
                metadata,
                layout_index,
                args.item_canvas,
                args.checkbox_canvas,
                output_dir,
            )
            if output_file is not None:
                print(output_file)
                generated_count += 1
        except Exception as exc:
            print(
                f"Error processing '{pdf_file}' "
                f"(layout '{metadata.id}'): {exc}",
                file=sys.stderr,
            )
            skipped_count += 1

    print(
        f"Summary: {generated_count} generated, "
        f"{skipped_count} skipped.",
        file=sys.stderr,
    )

    return 0 if generated_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
