"""Blueprint parsing and inheritance resolution.

Parses Blueprint JSON files into structured data, builds an id-to-path
index for parent resolution, and loads Blueprints with full inheritance
chain support including circular reference detection and duplicate
canvas name validation.
"""

import json
from pathlib import Path

from blueprint2layout.models import Blueprint, CanvasEntry

EDGE_NAMES = ("left", "right", "top", "bottom")


def _validate_edge_value(name: str, edge: str, value: object) -> int | float | str:
    """Validate that an edge value is numeric or string.

    Args:
        name: Canvas name (for error messages).
        edge: Edge name (for error messages).
        value: The raw edge value from JSON.

    Returns:
        The validated edge value.

    Raises:
        ValueError: If the value is not int, float, or str.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(
            f"Canvas '{name}' edge '{edge}' must be int, float, or str, "
            f"got {type(value).__name__}"
        )
    return value


def _parse_canvas_entry(entry: dict) -> CanvasEntry:
    """Convert a raw canvas entry dict into a CanvasEntry dataclass.

    Args:
        entry: A dictionary from the Blueprint's canvases array.

    Returns:
        A CanvasEntry instance.

    Raises:
        ValueError: If required fields are missing or edge types invalid.
    """
    if not isinstance(entry, dict):
        raise ValueError(f"Canvas entry must be a dict, got {type(entry).__name__}")

    if "name" not in entry:
        raise ValueError("Canvas entry missing required field 'name'")

    name = entry["name"]
    if not isinstance(name, str):
        raise ValueError(
            f"Canvas entry 'name' must be a string, got {type(name).__name__}"
        )

    for edge in EDGE_NAMES:
        if edge not in entry:
            raise ValueError(f"Canvas '{name}' missing required edge '{edge}'")

    edges = {edge: _validate_edge_value(name, edge, entry[edge]) for edge in EDGE_NAMES}

    parent = entry.get("parent")
    if parent is not None and not isinstance(parent, str):
        raise ValueError(
            f"Canvas '{name}' parent must be a string or null, "
            f"got {type(parent).__name__}"
        )

    return CanvasEntry(name=name, parent=parent, **edges)


def parse_blueprint(data: dict) -> Blueprint:
    """Parse a raw JSON dictionary into a Blueprint.

    Validates required fields (id, canvases) and converts each
    canvas entry dict into a CanvasEntry dataclass.

    Args:
        data: Parsed JSON dictionary from a Blueprint file.

    Returns:
        A Blueprint instance.

    Raises:
        ValueError: If required fields are missing or malformed.

    Requirements: chronicle-blueprints 7.1, 7.2, 7.3
    """
    if not isinstance(data, dict):
        raise ValueError(f"Blueprint data must be a dict, got {type(data).__name__}")

    if "id" not in data:
        raise ValueError("Blueprint missing required field 'id'")

    blueprint_id = data["id"]
    if not isinstance(blueprint_id, str):
        raise ValueError(
            f"Blueprint 'id' must be a string, got {type(blueprint_id).__name__}"
        )

    if "canvases" not in data:
        raise ValueError("Blueprint missing required field 'canvases'")

    canvases_raw = data["canvases"]
    if not isinstance(canvases_raw, list):
        raise ValueError(
            f"Blueprint 'canvases' must be a list, got {type(canvases_raw).__name__}"
        )

    canvas_entries = [_parse_canvas_entry(entry) for entry in canvases_raw]

    parent = data.get("parent")
    if parent is not None and not isinstance(parent, str):
        raise ValueError(
            f"Blueprint 'parent' must be a string or null, "
            f"got {type(parent).__name__}"
        )

    description = data.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError(
            f"Blueprint 'description' must be a string or null, "
            f"got {type(description).__name__}"
        )

    flags = data.get("flags", [])
    if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
        raise ValueError("Blueprint 'flags' must be a list of strings")

    aspectratio = data.get("aspectratio")
    if aspectratio is not None and not isinstance(aspectratio, str):
        raise ValueError(
            f"Blueprint 'aspectratio' must be a string or null, "
            f"got {type(aspectratio).__name__}"
        )

    return Blueprint(
        id=blueprint_id,
        canvases=canvas_entries,
        parent=parent,
        description=description,
        flags=flags,
        aspectratio=aspectratio,
    )


def build_blueprint_index(blueprints_dir: Path) -> dict[str, Path]:
    """Scan a directory for Blueprint JSON files and build an id-to-path map.

    Reads each .json file in the directory (recursively), parses the
    "id" field, and maps it to the file path. Files that are not valid
    JSON or lack an "id" field are silently skipped.

    Args:
        blueprints_dir: Directory containing Blueprint JSON files.

    Returns:
        Dictionary mapping Blueprint id strings to file paths.

    Requirements: chronicle-blueprints 8.3
    """
    index: dict[str, Path] = {}
    for json_path in blueprints_dir.rglob("*.json"):
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            index[data["id"]] = json_path
    return index


def _validate_unique_canvas_names(
    canvases: list[CanvasEntry],
    context: str = "",
) -> None:
    """Raise ValueError if any canvas names are duplicated.

    Args:
        canvases: Combined list of canvas entries to check.
        context: Optional context string for the error message.
    """
    seen: set[str] = set()
    for canvas in canvases:
        if canvas.name in seen:
            raise ValueError(
                f"Duplicate canvas name '{canvas.name}'{context}"
            )
        seen.add(canvas.name)


def load_blueprint_with_inheritance(
    blueprint_path: Path,
    blueprint_index: dict[str, Path],
) -> tuple[Blueprint, list[CanvasEntry]]:
    """Load a Blueprint and resolve its full inheritance chain.

    Recursively loads parent Blueprints, validates no circular
    references, validates no duplicate canvas names across the
    chain, and returns the target Blueprint plus the ordered list
    of inherited canvases from all ancestors.

    Args:
        blueprint_path: Path to the target Blueprint JSON file.
        blueprint_index: Map of Blueprint ids to file paths.

    Returns:
        A tuple of (target_blueprint, inherited_canvases) where
        inherited_canvases is the ordered list of canvas entries
        from all ancestor Blueprints (root-first order).

    Raises:
        FileNotFoundError: If the Blueprint file does not exist.
        ValueError: If JSON is invalid, parent id is unknown,
            circular reference detected, or duplicate canvas names.

    Requirements: chronicle-blueprints 7.4, 7.5, 7.6, 8.1, 8.2,
        8.4, 8.5, 8.6, 8.7, 8.8, 8.9
    """
    with open(blueprint_path, encoding="utf-8") as f:
        data = json.load(f)
    target = parse_blueprint(data)

    if target.parent is None:
        _validate_unique_canvas_names(target.canvases)
        return target, []

    # Walk the parent chain, collecting blueprints from child → root
    chain: list[Blueprint] = []
    visited: set[str] = {target.id}
    current_parent_id = target.parent

    while current_parent_id is not None:
        if current_parent_id in visited:
            raise ValueError(
                f"Circular parent reference detected: "
                f"'{current_parent_id}' already visited in chain"
            )
        if current_parent_id not in blueprint_index:
            raise ValueError(
                f"Unknown parent Blueprint id '{current_parent_id}'"
            )
        visited.add(current_parent_id)
        parent_path = blueprint_index[current_parent_id]
        with open(parent_path, encoding="utf-8") as f:
            parent_data = json.load(f)
        parent_blueprint = parse_blueprint(parent_data)
        chain.append(parent_blueprint)
        current_parent_id = parent_blueprint.parent

    # Reverse so root-first order (grandparent → parent)
    chain.reverse()

    # Collect inherited canvases in root-first order
    inherited_canvases: list[CanvasEntry] = []
    for ancestor in chain:
        inherited_canvases.extend(ancestor.canvases)

    # Validate no duplicate canvas names across entire chain
    all_canvases = inherited_canvases + list(target.canvases)
    _validate_unique_canvas_names(all_canvases)

    return target, inherited_canvases
