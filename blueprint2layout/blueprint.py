"""Blueprint parsing and inheritance resolution.

Parses Blueprint JSON files into structured data, builds an id-to-path
index for parent resolution, and loads Blueprints with full inheritance
chain support including circular reference detection and duplicate
canvas name validation.
"""

import json
from pathlib import Path

from blueprint2layout.models import Blueprint, CanvasEntry, FieldEntry

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


def _validate_parameters(parameters: object) -> dict:
    """Validate that parameters is a dict of dicts.

    Args:
        parameters: The raw parameters value from JSON.

    Returns:
        The validated parameters dict.

    Raises:
        ValueError: If structure is not dict-of-dicts.

    Requirements: blueprint-fields 1.4
    """
    if not isinstance(parameters, dict):
        raise ValueError(
            f"Blueprint 'parameters' must be a dict of dicts, "
            f"got {type(parameters).__name__}"
        )
    for group_name, group_value in parameters.items():
        if not isinstance(group_value, dict):
            raise ValueError(
                f"Blueprint 'parameters' must be a dict of dicts, "
                f"but group '{group_name}' is {type(group_value).__name__}"
            )
    return parameters


# Valid types for FieldEntry properties, used by _parse_field_entry
_FIELD_EDGE_TYPES = (int, float, str)
_FIELD_NUMERIC_TYPES = (int, float)
_FIELD_PROPERTY_VALIDATORS: dict[str, tuple[type, ...]] = {
    "canvas": (str,),
    "type": (str,),
    "param": (str,),
    "value": (str,),
    "left": _FIELD_EDGE_TYPES,
    "right": _FIELD_EDGE_TYPES,
    "top": _FIELD_EDGE_TYPES,
    "bottom": _FIELD_EDGE_TYPES,
    "font": (str,),
    "fontsize": _FIELD_NUMERIC_TYPES,
    "fontweight": (str,),
    "align": (str,),
    "color": (str,),
    "linewidth": _FIELD_NUMERIC_TYPES,
    "size": _FIELD_NUMERIC_TYPES,
    "lines": (int,),
    "trigger": (str,),
}


def _parse_field_entry(entry: dict) -> FieldEntry:
    """Convert a raw field entry dict into a FieldEntry dataclass.

    Validates required field 'name' and valid property types.
    Does not validate that canvas/type are present (they may come
    from styles).

    Args:
        entry: A dictionary from the Blueprint's fields array.

    Returns:
        A FieldEntry instance.

    Raises:
        ValueError: If required fields are missing or types invalid.

    Requirements: blueprint-fields 7.2, 7.5, 7.6, 7.7, 7.8, 13.4, 13.5
    """
    if not isinstance(entry, dict):
        raise ValueError(
            f"Field entry must be a dict, got {type(entry).__name__}"
        )

    if "name" not in entry:
        raise ValueError("Field entry missing required field 'name'")

    name = entry["name"]
    if not isinstance(name, str):
        raise ValueError(
            f"Field entry 'name' must be a string, got {type(name).__name__}"
        )

    kwargs: dict = {"name": name}

    for prop, valid_types in _FIELD_PROPERTY_VALIDATORS.items():
        if prop == "name":
            continue
        if prop not in entry:
            continue
        val = entry[prop]
        if isinstance(val, bool) or not isinstance(val, valid_types):
            raise ValueError(
                f"Field '{name}' property '{prop}' must be "
                f"{' or '.join(t.__name__ for t in valid_types)}, "
                f"got {type(val).__name__}"
            )
        kwargs[prop] = val

    # Handle styles array
    if "styles" in entry:
        styles = entry["styles"]
        if not isinstance(styles, list) or not all(
            isinstance(s, str) for s in styles
        ):
            raise ValueError(
                f"Field '{name}' property 'styles' must be a list of strings"
            )
        kwargs["styles"] = styles

    return FieldEntry(**kwargs)


def _merge_parameters(
    parent_params: dict | None,
    child_params: dict | None,
) -> dict | None:
    """Merge parent and child parameter dictionaries.

    Groups present only in parent are included. Groups present only
    in child are added. Groups in both have their individual parameters
    merged, with child overriding parent.

    Args:
        parent_params: Parent Blueprint's parameters (or None).
        child_params: Child Blueprint's parameters (or None).

    Returns:
        Merged parameters dict, or None if both are None.

    Requirements: blueprint-fields 2.1, 2.2, 2.3, 2.4
    """
    if parent_params is None and child_params is None:
        return None
    if parent_params is None:
        return child_params
    if child_params is None:
        return parent_params

    merged: dict = {}
    all_groups = set(parent_params) | set(child_params)
    for group in all_groups:
        parent_group = parent_params.get(group, {})
        child_group = child_params.get(group, {})
        merged[group] = {**parent_group, **child_group}
    return merged


def _merge_field_styles(
    parent_styles: dict | None,
    child_styles: dict | None,
) -> dict | None:
    """Merge parent and child field_styles dictionaries.

    Child definitions override parent definitions for the same name.

    Args:
        parent_styles: Parent Blueprint's field_styles (or None).
        child_styles: Child Blueprint's field_styles (or None).

    Returns:
        Merged field_styles dict, or None if both are None.

    Requirements: blueprint-fields 6.8
    """
    if parent_styles is None and child_styles is None:
        return None
    if parent_styles is None:
        return child_styles
    if child_styles is None:
        return parent_styles

    return {**parent_styles, **child_styles}


def parse_blueprint(data: dict) -> Blueprint:
    """Parse a raw JSON dictionary into a Blueprint.

    Validates required fields (id, canvases) and converts each
    canvas entry dict into a CanvasEntry dataclass. Also parses
    optional parameters, defaultChronicleLocation, field_styles,
    and fields properties.

    Args:
        data: Parsed JSON dictionary from a Blueprint file.

    Returns:
        A Blueprint instance.

    Raises:
        ValueError: If required fields are missing or malformed.

    Requirements: chronicle-blueprints 7.1, 7.2, 7.3;
        blueprint-fields 1.1, 1.4, 3.1, 3.4, 6.1, 7.1, 13.1-13.5
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

    # Parse optional parameters (validated as dict-of-dicts)
    parameters = None
    if "parameters" in data:
        parameters = _validate_parameters(data["parameters"])

    # Parse optional defaultChronicleLocation (validated as string)
    default_chronicle_location = data.get("defaultChronicleLocation")
    if default_chronicle_location is not None and not isinstance(
        default_chronicle_location, str
    ):
        raise ValueError(
            f"Blueprint 'defaultChronicleLocation' must be a string, "
            f"got {type(default_chronicle_location).__name__}"
        )

    # Parse optional field_styles (validated as dict)
    field_styles = None
    if "field_styles" in data:
        raw_styles = data["field_styles"]
        if not isinstance(raw_styles, dict):
            raise ValueError(
                f"Blueprint 'field_styles' must be a dict, "
                f"got {type(raw_styles).__name__}"
            )
        field_styles = raw_styles

    # Parse optional fields (validated as list, each entry parsed)
    fields = None
    if "fields" in data:
        raw_fields = data["fields"]
        if not isinstance(raw_fields, list):
            raise ValueError(
                f"Blueprint 'fields' must be a list, "
                f"got {type(raw_fields).__name__}"
            )
        fields = [_parse_field_entry(entry) for entry in raw_fields]

    return Blueprint(
        id=blueprint_id,
        canvases=canvas_entries,
        parent=parent,
        description=description,
        flags=flags,
        aspectratio=aspectratio,
        parameters=parameters,
        default_chronicle_location=default_chronicle_location,
        field_styles=field_styles,
        fields=fields,
    )


def build_blueprint_index(blueprints_dir: Path) -> dict[str, Path]:
    """Scan a directory for Blueprint JSON files and build an id-to-path map.

    Delegates to shared.layout_index.build_json_index.

    Args:
        blueprints_dir: Directory containing Blueprint JSON files.

    Returns:
        Dictionary mapping Blueprint id strings to file paths.

    Requirements: chronicle-blueprints 8.3
    """
    from shared.layout_index import build_json_index

    return build_json_index(blueprints_dir)


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


def _validate_unique_field_names(
    target_fields: list[FieldEntry] | None,
    ancestor_chain: list[Blueprint],
) -> None:
    """Raise ValueError if child field names duplicate any parent field names.

    Args:
        target_fields: The target Blueprint's fields (or None).
        ancestor_chain: Ancestor Blueprints in root-first order.

    Raises:
        ValueError: If a child field name duplicates a parent field name.

    Requirements: blueprint-fields 10.4
    """
    if not target_fields:
        return

    parent_field_names: set[str] = set()
    for ancestor in ancestor_chain:
        if ancestor.fields:
            for field_entry in ancestor.fields:
                parent_field_names.add(field_entry.name)

    for field_entry in target_fields:
        if field_entry.name in parent_field_names:
            raise ValueError(
                f"Duplicate field name '{field_entry.name}' — "
                f"already defined in a parent Blueprint"
            )


def load_blueprint_with_inheritance(
    blueprint_path: Path,
    blueprint_index: dict[str, Path],
) -> tuple[Blueprint, list[CanvasEntry], dict | None, dict[str, dict] | None, str | None]:
    """Load a Blueprint and resolve its full inheritance chain.

    Recursively loads parent Blueprints, validates no circular
    references, validates no duplicate canvas names across the
    chain, merges parameters and field_styles through the chain,
    validates field name uniqueness, and returns the target Blueprint
    plus inherited canvases, merged parameters, and merged field_styles.

    Args:
        blueprint_path: Path to the target Blueprint JSON file.
        blueprint_index: Map of Blueprint ids to file paths.

    Returns:
        A tuple of (target_blueprint, inherited_canvases,
        merged_parameters, merged_field_styles, effective_aspectratio)
        where inherited_canvases is the ordered list of canvas entries
        from all ancestor Blueprints (root-first order),
        merged_parameters is the result of merging parameters
        through the full chain, merged_field_styles is the result
        of merging field_styles through the full chain, and
        effective_aspectratio is the child's aspectratio or the
        nearest ancestor's if the child doesn't declare one.

    Raises:
        FileNotFoundError: If the Blueprint file does not exist.
        ValueError: If JSON is invalid, parent id is unknown,
            circular reference detected, duplicate canvas names,
            or duplicate field names across the chain.

    Requirements: chronicle-blueprints 7.4, 7.5, 7.6, 8.1, 8.2,
        8.4, 8.5, 8.6, 8.7, 8.8, 8.9;
        blueprint-fields 2.1, 2.2, 2.3, 2.4, 6.8, 10.1, 10.4
    """
    with open(blueprint_path, encoding="utf-8") as f:
        data = json.load(f)
    target = parse_blueprint(data)

    if target.parent is None:
        _validate_unique_canvas_names(target.canvases)
        return (
            target, [], target.parameters, target.field_styles,
            target.aspectratio,
        )

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

    # Merge parameters through the chain: root → ... → parent → child
    merged_parameters: dict | None = None
    for ancestor in chain:
        merged_parameters = _merge_parameters(merged_parameters, ancestor.parameters)
    merged_parameters = _merge_parameters(merged_parameters, target.parameters)

    # Merge field_styles through the chain: root → ... → parent → child
    merged_field_styles: dict[str, dict] | None = None
    for ancestor in chain:
        merged_field_styles = _merge_field_styles(merged_field_styles, ancestor.field_styles)
    merged_field_styles = _merge_field_styles(merged_field_styles, target.field_styles)

    # Validate field name uniqueness across the chain
    _validate_unique_field_names(target.fields, chain)

    # Resolve effective aspectratio: child wins, else walk up the chain
    effective_aspectratio = target.aspectratio
    if effective_aspectratio is None:
        for ancestor in reversed(chain):
            if ancestor.aspectratio is not None:
                effective_aspectratio = ancestor.aspectratio
                break

    return (
        target, inherited_canvases, merged_parameters,
        merged_field_styles, effective_aspectratio,
    )
