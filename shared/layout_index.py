"""Layout/Blueprint JSON index and inheritance chain utilities.

Provides common functions for scanning directories of JSON files,
building id-to-path indexes, and walking parent inheritance chains.
Used by both blueprint2layout and layout_visualizer.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_json_file(path: Path) -> dict:
    """Read and parse a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file contains invalid JSON.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def build_json_index(directory: Path) -> dict[str, Path]:
    """Scan a directory tree for JSON files and build an id-to-path map.

    Reads each ``.json`` file recursively, parses the ``id`` field,
    and maps it to the file path. Files without an ``id`` field
    or with invalid JSON are silently skipped.

    Args:
        directory: Root directory to scan.

    Returns:
        Dictionary mapping id strings to file paths.
    """
    index: dict[str, Path] = {}
    for json_path in directory.rglob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.debug("Skipping %s: cannot parse JSON", json_path)
            continue
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            index[data["id"]] = json_path
    return index


def collect_inheritance_chain(
    file_path: Path,
    index: dict[str, Path],
) -> list[tuple[Path, dict]]:
    """Walk the parent chain and collect JSON data from root to leaf.

    Follows the ``parent`` field in each JSON file, looking up paths
    in the provided index. Returns the chain in root-first order.

    Args:
        file_path: Path to the target (leaf) JSON file.
        index: Map of ids to file paths.

    Returns:
        List of (path, data) tuples ordered root-first, leaf-last.

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If JSON is invalid or a parent id is not in the index.
    """
    chain: list[tuple[Path, dict]] = []
    current_path: Path | None = file_path

    while current_path is not None:
        data = read_json_file(current_path)
        chain.append((current_path, data))
        parent_id = data.get("parent")
        if parent_id is None:
            break
        if parent_id not in index:
            raise ValueError(
                f"Parent id '{parent_id}' not found in index"
            )
        current_path = index[parent_id]

    chain.reverse()
    return chain
