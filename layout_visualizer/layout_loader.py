"""Layout loading and inheritance resolution.

Loads layout JSON files and resolves the full parent inheritance chain
to produce a merged set of canvas regions. Delegates directory scanning
and chain walking to the shared.layout_index module.
"""

import logging
from pathlib import Path

from layout_visualizer.models import (
    CanvasRegion,
    CheckboxEntry,
    DataContentEntry,
    RectangleEntry,
    StrikeoutEntry,
)
from shared.layout_index import build_json_index, collect_inheritance_chain

logger = logging.getLogger(__name__)

_TEXT_TYPES = {"text", "multiline"}
_SKIP_TYPES = {"line"}

_NAMED_COLORS: dict[str, tuple[float, float, float]] = {
    "white": (1.0, 1.0, 1.0),
    "black": (0.0, 0.0, 0.0),
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 0.5, 0.0),
    "blue": (0.0, 0.0, 1.0),
}


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
    presets: dict[str, dict] | None = None,
    label: str | None = None,
) -> None:
    """Recursively extract positioned fields from a content array.

    Walks through content entries, including nested trigger and choice
    content. Entries with canvas + x + y + x2 + y2 are collected as
    CanvasRegion instances where parent is the canvas name.

    Args:
        content: The content array (or nested content).
        fields: Accumulator list to append extracted fields to.
        counter: Single-element list used as a mutable counter for naming.
        presets: Merged preset definitions for resolving preset-based entries.
        label: Optional label propagated from a parent choice key.
    """
    if presets is None:
        presets = {}

    for entry in content:
        entry_type = entry.get("type")

        if entry_type == "choice":
            choices = entry.get("content", {})
            if isinstance(choices, dict):
                for key, key_content in choices.items():
                    if isinstance(key_content, list):
                        _extract_fields_from_content(
                            key_content, fields, counter, presets, label=key,
                        )
            continue

        if entry_type == "trigger":
            nested = entry.get("content", [])
            _extract_fields_from_content(nested, fields, counter, presets, label)
            continue

        if entry_type in ("strikeout", "checkbox"):
            field = _extract_preset_based_field(entry, presets, label, counter)
            if field is not None:
                fields.append(field)
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


def _extract_preset_based_field(
    entry: dict,
    presets: dict[str, dict],
    label: str | None,
    counter: list[int],
) -> CanvasRegion | None:
    """Resolve presets on a strikeout or checkbox entry and return a field.

    Merges preset properties into the entry, checks for required
    positioning coordinates, and returns a CanvasRegion. Returns None
    if the resolved entry lacks any required coordinate.

    Args:
        entry: Raw content entry dict (strikeout or checkbox).
        presets: Merged preset definitions.
        label: Optional label from a parent choice key.
        counter: Single-element mutable counter for fallback naming.

    Returns:
        A CanvasRegion with resolved coordinates, or None.

    Requirements: 1.1, 1.2, 1.3, 1.4, 5.1, 5.2
    """
    resolved = resolve_entry_presets(entry, presets)

    canvas = resolved.get("canvas")
    if not canvas:
        return None
    if not all(k in resolved for k in ("x", "y", "x2", "y2")):
        return None

    name = label if label else f"field_{counter[0]}"
    counter[0] += 1

    return CanvasRegion(
        name=name,
        x=float(resolved["x"]),
        y=float(resolved["y"]),
        x2=float(resolved["x2"]),
        y2=float(resolved["y2"]),
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

    presets = merge_presets(chain)

    fields: list[CanvasRegion] = []
    _extract_fields_from_content(merged_content, fields, [0], presets)

    return fields, merged_canvases, file_paths


def merge_parameters(
    chain: list[tuple[Path, dict]],
) -> dict[str, dict]:
    """Merge parameters from the inheritance chain into a flat lookup.

    Walks root-to-leaf. For each layout, iterates parameter groups
    and collects parameters by name. Child definitions override
    parent definitions for the same parameter name.

    Args:
        chain: Inheritance chain from ``collect_inheritance_chain``
               (root-first order).

    Returns:
        Flat dict mapping parameter name to its definition dict
        (containing type, description, example, etc.).

    Requirements: layout-data-mode 2.1
    """
    merged: dict[str, dict] = {}
    for _path, data in chain:
        parameters = data.get("parameters", {})
        for group in parameters.values():
            if isinstance(group, dict):
                merged.update(group)
    return merged


def merge_presets(
    chain: list[tuple[Path, dict]],
) -> dict[str, dict]:
    """Merge presets from the inheritance chain.

    Walks root-to-leaf. Child preset definitions override parent
    definitions for the same preset name.

    Args:
        chain: Inheritance chain (root-first order).

    Returns:
        Dict mapping preset name to its property dict.

    Requirements: layout-data-mode 3.3
    """
    merged: dict[str, dict] = {}
    for _path, data in chain:
        presets = data.get("presets", {})
        if isinstance(presets, dict):
            merged.update(presets)
    return merged


def _resolve_preset_chain(
    preset_name: str,
    presets: dict[str, dict],
    visited: set[str] | None = None,
) -> dict:
    """Recursively resolve a single preset and its nested references.

    Walks depth-first left-to-right through nested preset references,
    collecting properties. Later presets override earlier ones.

    Args:
        preset_name: Name of the preset to resolve.
        presets: Merged preset definitions.
        visited: Set of already-visited preset names (cycle guard).

    Returns:
        Merged property dict from the preset chain.
    """
    if visited is None:
        visited = set()
    if preset_name in visited or preset_name not in presets:
        return {}
    visited.add(preset_name)

    preset_def = presets[preset_name]
    resolved: dict = {}

    for nested_name in preset_def.get("presets", []):
        resolved.update(_resolve_preset_chain(nested_name, presets, visited))

    for key, value in preset_def.items():
        if key != "presets":
            resolved[key] = value

    return resolved


def resolve_entry_presets(
    entry: dict,
    presets: dict[str, dict],
) -> dict:
    """Apply preset properties to a content entry as defaults.

    Walks the entry's presets array (if any), resolving nested
    preset references recursively. Collects properties from
    presets in order, then overlays the entry's inline properties.
    Inline values always win over preset values.

    Args:
        entry: Raw content entry dict from the layout JSON.
        presets: Merged preset definitions.

    Returns:
        A new dict with all properties resolved (presets merged
        as defaults, inline values as overrides).

    Requirements: layout-data-mode 3.1, 3.2
    """
    resolved: dict = {}

    for preset_name in entry.get("presets", []):
        resolved.update(_resolve_preset_chain(preset_name, presets, set()))

    for key, value in entry.items():
        if key != "presets":
            resolved[key] = value

    return resolved


def _collect_choice_nested_content(raw_entry: dict) -> list[dict]:
    """Gather all nested content arrays from a choice entry."""
    choices = raw_entry.get("content", {})
    combined: list[dict] = []
    if isinstance(choices, dict):
        for choice_content in choices.values():
            if isinstance(choice_content, list):
                combined.extend(choice_content)
    return combined


def _extract_checkbox_entries(
    raw_entry: dict,
    presets: dict[str, dict],
    parameters: dict[str, dict],
    canvases: dict[str, CanvasRegion],
    checkboxes: list[CheckboxEntry],
    strikeouts: list[StrikeoutEntry],
) -> None:
    """Extract all checkbox and strikeout entries from a choice block.

    Checks every choice branch and collects all checkbox and strikeout
    content entries regardless of the example value.
    """
    choices_content = raw_entry.get("content", {})
    if not isinstance(choices_content, dict):
        return

    for choice_entries in choices_content.values():
        if not isinstance(choice_entries, list):
            continue
        for entry in choice_entries:
            entry_type = entry.get("type")
            resolved = resolve_entry_presets(entry, presets)
            canvas_name = resolved.get("canvas")
            if not canvas_name or canvas_name not in canvases:
                continue

            if entry_type == "checkbox":
                color_name = resolved.get("color", "black")
                color = _NAMED_COLORS.get(color_name, (0.0, 0.0, 0.0))
                checkboxes.append(CheckboxEntry(
                    canvas=canvas_name,
                    x=float(resolved.get("x", 0)),
                    y=float(resolved.get("y", 0)),
                    x2=float(resolved.get("x2", 0)),
                    y2=float(resolved.get("y2", 0)),
                    color=color,
                ))
            elif entry_type == "strikeout":
                color_name = resolved.get("color", "black")
                color = _NAMED_COLORS.get(color_name, (0.0, 0.0, 0.0))
                strikeouts.append(StrikeoutEntry(
                    canvas=canvas_name,
                    x=float(resolved.get("x", 0)),
                    y=float(resolved.get("y", 0)),
                    x2=float(resolved.get("x2", 0)),
                    y2=float(resolved.get("y2", 0)),
                    color=color,
                ))


def _lookup_example_value(
    param_name: str,
    parameters: dict[str, dict],
) -> str | None:
    """Look up and stringify a parameter's example value.

    Returns ``None`` (with a warning) when the parameter is missing
    or has no ``example`` field.
    """
    param_def = parameters.get(param_name)
    if param_def is None:
        logger.warning("Missing parameter '%s' — skipping entry", param_name)
        return None
    if "example" not in param_def:
        logger.warning(
            "Parameter '%s' has no example field — skipping entry",
            param_name,
        )
        return None
    return str(param_def["example"])


def _build_data_content_entry(
    resolved: dict,
    entry_type: str,
    param_name: str,
    example_value: str,
) -> DataContentEntry:
    """Construct a ``DataContentEntry`` from a resolved property dict."""
    return DataContentEntry(
        param_name=param_name,
        example_value=example_value,
        entry_type=entry_type,
        canvas=resolved["canvas"],
        x=float(resolved.get("x", 0)),
        y=float(resolved.get("y", 0)),
        x2=float(resolved.get("x2", 100)),
        y2=float(resolved.get("y2", 100)),
        font=resolved.get("font", "Helvetica"),
        fontsize=float(resolved.get("fontsize", 12)),
        fontweight=resolved.get("fontweight"),
        align=resolved.get("align", "LB"),
        lines=int(resolved.get("lines", 1)),
    )


def _extract_data_entries(
    content: list[dict],
    presets: dict[str, dict],
    parameters: dict[str, dict],
    canvases: dict[str, CanvasRegion],
    entries: list[DataContentEntry],
    rectangles: list[RectangleEntry],
    checkboxes: list[CheckboxEntry] | None = None,
    strikeouts: list[StrikeoutEntry] | None = None,
) -> None:
    """Recursively extract text/multiline and rectangle entries.

    Skips non-text types except rectangle. Recurses into trigger and
    choice nested content. Resolves presets, looks up example values,
    and appends fully resolved instances.

    Args:
        content: The content array to walk.
        presets: Merged preset definitions.
        parameters: Merged parameter definitions (flat).
        canvases: Merged canvas regions.
        entries: Accumulator list for extracted text entries.
        rectangles: Accumulator list for extracted rectangle entries.
    """
    for raw_entry in content:
        entry_type = raw_entry.get("type")

        if entry_type == "trigger":
            nested = raw_entry.get("content", [])
            _extract_data_entries(
                nested, presets, parameters, canvases,
                entries, rectangles, checkboxes, strikeouts,
            )
            continue

        if entry_type == "choice":
            nested = _collect_choice_nested_content(raw_entry)
            _extract_data_entries(
                nested, presets, parameters, canvases, entries, rectangles,
            )
            _extract_checkbox_entries(
                raw_entry, presets, parameters, canvases,
                checkboxes, strikeouts,
            )
            continue

        if entry_type == "rectangle":
            resolved = resolve_entry_presets(raw_entry, presets)
            canvas_name = resolved.get("canvas")
            if not canvas_name or canvas_name not in canvases:
                continue
            color_name = resolved.get("color", "white")
            color = _NAMED_COLORS.get(color_name, (1.0, 1.0, 1.0))
            x = float(resolved.get("x", 0))
            y = float(resolved.get("y", 0))
            x2 = float(resolved.get("x2", 100))
            y2 = float(resolved.get("y2", 100))
            rectangles.append(RectangleEntry(
                canvas=canvas_name, x=x, y=y, x2=x2, y2=y2, color=color,
            ))
            continue

        if entry_type not in _TEXT_TYPES:
            continue

        resolved = resolve_entry_presets(raw_entry, presets)
        canvas_name = resolved.get("canvas")
        if not canvas_name or canvas_name not in canvases:
            continue

        value = resolved.get("value", "")
        if not isinstance(value, str) or not value.startswith("param:"):
            continue

        param_name = value[6:]
        example_value = _lookup_example_value(param_name, parameters)
        if example_value is None:
            continue

        entries.append(
            _build_data_content_entry(resolved, entry_type, param_name, example_value),
        )


def load_data_content(
    layout_path: Path,
    layout_index: dict[str, Path],
) -> tuple[list[DataContentEntry], list[RectangleEntry], list[CheckboxEntry], list[StrikeoutEntry], dict[str, CanvasRegion], list[Path]]:
    """Load content entries for data mode rendering.

    Walks the inheritance chain, merges canvases, parameters,
    presets, and content. Extracts text/multiline and rectangle
    entries, resolves presets, looks up example values, and returns
    fully resolved instances.

    Skips non-text types (checkbox, strikeout, line) except rectangle.
    Recurses into trigger and choice nested content.
    Warns and skips entries with missing parameters or examples.

    Args:
        layout_path: Path to the target layout JSON file.
        layout_index: Map of layout ids to file paths.

    Returns:
        Tuple of (text_entries, rectangle_entries, merged_canvases,
        layout_file_paths).

    Requirements: layout-data-mode 2.1-2.5, 3.1-3.3, 7.1-7.6
    """
    chain = collect_inheritance_chain(layout_path, layout_index)

    merged_canvases: dict[str, CanvasRegion] = {}
    merged_content: list[dict] = []
    file_paths: list[Path] = []

    for path, data in chain:
        file_paths.append(path)
        canvas_data = data.get("canvas", {})
        merged_canvases.update(_parse_canvas_object(canvas_data))
        merged_content.extend(data.get("content", []))

    parameters = merge_parameters(chain)
    presets = merge_presets(chain)

    entries: list[DataContentEntry] = []
    rectangles: list[RectangleEntry] = []
    checkboxes: list[CheckboxEntry] = []
    strikeouts: list[StrikeoutEntry] = []
    _extract_data_entries(
        merged_content, presets, parameters, merged_canvases,
        entries, rectangles, checkboxes, strikeouts,
    )

    return entries, rectangles, checkboxes, strikeouts, merged_canvases, file_paths
