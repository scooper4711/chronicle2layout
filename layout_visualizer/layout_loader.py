"""Layout loading and inheritance resolution.

Loads layout JSON files and resolves the full parent inheritance chain
to produce a merged set of canvas regions. Delegates directory scanning
and chain walking to the shared.layout_index module.
"""

from pathlib import Path

from layout_visualizer.models import CanvasRegion
from shared.layout_index import build_json_index, collect_inheritance_chain


def build_layout_index(layouts_dir: Path) -> dict[str, Path]:
    """Scan a directory tree for layout JSON files and build an id-to-path map.

    Args:
        layouts_dir: Root directory containing layout JSON files.

    Returns:
        Dictionary mapping layout id strings to file paths.

    Requirements: layout-visualizer 2.2
    """
    return build_json_index(layouts_dir)


def _parse_canvas_object(
    canvas_data: dict[str, dict],
) -> dict[str, CanvasRegion]:
    """Convert a raw canvas JSON object into CanvasRegion instances.

    Args:
        canvas_data: The ``canvas`` object from a layout JSON file.

    Returns:
        Dictionary mapping canvas name to CanvasRegion.
    """
    canvases: dict[str, CanvasRegion] = {}
    for name, props in canvas_data.items():
        canvases[name] = CanvasRegion(
            name=name,
            x=float(props["x"]),
            y=float(props["y"]),
            x2=float(props["x2"]),
            y2=float(props["y2"]),
            parent=props.get("parent"),
        )
    return canvases


def load_layout_with_inheritance(
    layout_path: Path,
    layout_index: dict[str, Path],
) -> tuple[dict[str, CanvasRegion], list[Path]]:
    """Load a layout and resolve its full inheritance chain.

    Walks the parent chain via the layout_index, merging canvas
    dicts from root to leaf (child overrides parent for same-named
    canvases).

    Args:
        layout_path: Path to the target layout JSON file.
        layout_index: Map of layout ids to file paths.

    Returns:
        A tuple of (merged_canvases, layout_file_paths) where
        merged_canvases maps canvas name to CanvasRegion, and
        layout_file_paths is the ordered list of files in the
        inheritance chain (root first).

    Raises:
        FileNotFoundError: If layout_path does not exist.
        ValueError: If JSON is invalid or parent id not found.

    Requirements: layout-visualizer 2.1, 2.2, 2.3, 2.4, 2.5
    """
    chain = collect_inheritance_chain(layout_path, layout_index)
    merged: dict[str, CanvasRegion] = {}
    file_paths: list[Path] = []

    for path, data in chain:
        file_paths.append(path)
        canvas_data = data.get("canvas", {})
        merged.update(_parse_canvas_object(canvas_data))

    return merged, file_paths


def _extract_fields_from_content(
    content: list[dict],
    fields: list[CanvasRegion],
    counter: list[int],
) -> None:
    """Recursively extract positioned fields from a content array.

    Walks through content entries, including nested trigger and choice
    content. Entries with canvas + x + y + x2 + y2 are collected as
    CanvasRegion instances where parent is the canvas name.

    Args:
        content: The content array (or nested content).
        fields: Accumulator list to append extracted fields to.
        counter: Single-element list used as a mutable counter for naming.
    """
    for entry in content:
        nested = _get_nested_content(entry)
        if nested:
            _extract_fields_from_content(nested, fields, counter)
            continue

        field = _try_parse_field(entry, counter)
        if field is not None:
            fields.append(field)


def _get_nested_content(entry: dict) -> list[dict] | None:
    """Return nested content from trigger or choice entries, or None."""
    entry_type = entry.get("type")

    if entry_type == "trigger":
        return entry.get("content", [])

    if entry_type == "choice":
        choices = entry.get("content", {})
        if isinstance(choices, dict):
            combined: list[dict] = []
            for choice_content in choices.values():
                if isinstance(choice_content, list):
                    combined.extend(choice_content)
            return combined

    return None


def _try_parse_field(entry: dict, counter: list[int]) -> CanvasRegion | None:
    """Parse a content entry as a positioned field, or return None."""
    canvas = entry.get("canvas")
    if not canvas:
        return None
    if not all(k in entry for k in ("x", "y", "x2", "y2")):
        return None

    label = entry.get("value", f"field_{counter[0]}")
    if label.startswith("param:"):
        label = label[6:]
    counter[0] += 1

    return CanvasRegion(
        name=label,
        x=float(entry["x"]),
        y=float(entry["y"]),
        x2=float(entry["x2"]),
        y2=float(entry["y2"]),
        parent=canvas,
    )


def resolve_default_chronicle_location(
    layout_path: Path,
    layout_index: dict[str, Path],
) -> str | None:
    """Walk the inheritance chain and return the defaultChronicleLocation.

    The leaf layout's value takes precedence. If the leaf doesn't define
    it, walks up the chain (child-first) until one is found.

    Args:
        layout_path: Path to the target layout JSON file.
        layout_index: Map of layout ids to file paths.

    Returns:
        The defaultChronicleLocation string, or None if not defined
        anywhere in the chain.
    """
    chain = collect_inheritance_chain(layout_path, layout_index)
    # chain is root-first; walk in reverse (leaf-first) so child wins
    for _path, data in reversed(chain):
        location = data.get("defaultChronicleLocation")
        if location is not None:
            return location
    return None


def load_content_fields(
    layout_path: Path,
    layout_index: dict[str, Path],
) -> tuple[list[CanvasRegion], dict[str, CanvasRegion], list[Path]]:
    """Load a layout's content fields and canvases with inheritance.

    Extracts positioned content entries from the merged layout chain
    as CanvasRegion instances. Each field's parent is its canvas name.

    Args:
        layout_path: Path to the target layout JSON file.
        layout_index: Map of layout ids to file paths.

    Returns:
        A tuple of (fields, merged_canvases, layout_file_paths).
    """
    chain = collect_inheritance_chain(layout_path, layout_index)
    merged_canvases: dict[str, CanvasRegion] = {}
    merged_content: list[dict] = []
    file_paths: list[Path] = []

    for path, data in chain:
        file_paths.append(path)
        canvas_data = data.get("canvas", {})
        merged_canvases.update(_parse_canvas_object(canvas_data))
        content = data.get("content", [])
        merged_content.extend(content)

    fields: list[CanvasRegion] = []
    _extract_fields_from_content(merged_content, fields, [0])

    return fields, merged_canvases, file_paths
