"""TOML metadata file parsing and regex rule matching.

Parses a TOML metadata file containing regex-based rules that map
chronicle PDF paths to layout metadata (id, parent, description,
defaultChronicleLocation). Rules are tested in order; the first
matching rule wins.

Requirements: layout-generator 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7,
    2.9, 15.1, 15.2, 15.3, 15.4
"""

from __future__ import annotations

import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetadataRule:
    """A single rule entry from the TOML metadata file.

    Attributes:
        pattern: Regex pattern to match against PDF relative paths.
        id: Template for the generated layout id (may contain $1, $2, etc.).
        parent: Template for the parent layout id.
        description: Optional template for the layout description.
        default_chronicle_location: Optional template for defaultChronicleLocation.
    """

    pattern: str
    id: str
    parent: str
    description: str | None = None
    default_chronicle_location: str | None = None


@dataclass(frozen=True)
class MetadataConfig:
    """Parsed contents of the TOML metadata file.

    Attributes:
        layouts_dir: Optional global layouts directory path from the TOML.
        rules: Ordered list of MetadataRule entries.
    """

    layouts_dir: str | None
    rules: list[MetadataRule]


@dataclass(frozen=True)
class MatchedMetadata:
    """Result of matching a PDF path against a MetadataRule.

    All template substitutions have been applied. Fields are None
    when the rule did not define them.

    Attributes:
        id: Resolved layout id.
        parent: Resolved parent layout id.
        description: Resolved description, or None.
        default_chronicle_location: Resolved defaultChronicleLocation, or None.
    """

    id: str
    parent: str
    description: str | None = None
    default_chronicle_location: str | None = None


def load_metadata(metadata_path: Path) -> MetadataConfig:
    """Parse a TOML metadata file into a MetadataConfig.

    Args:
        metadata_path: Path to the TOML file.

    Returns:
        Parsed MetadataConfig with layouts_dir and rules.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the TOML is malformed or missing required fields.

    Requirements: layout-generator 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    """
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {metadata_path}"
        )

    try:
        raw = metadata_path.read_bytes()
        data = tomllib.loads(raw.decode())
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(
            f"Malformed TOML in {metadata_path}: {exc}"
        ) from exc

    layouts_dir = data.get("layouts_dir")
    raw_rules = data.get("rules", [])
    rules: list[MetadataRule] = []

    for index, entry in enumerate(raw_rules):
        for field in ("pattern", "id", "parent"):
            if field not in entry:
                raise ValueError(
                    f"Rule {index} in {metadata_path} missing "
                    f"required field '{field}'"
                )
        rules.append(
            MetadataRule(
                pattern=entry["pattern"],
                id=entry["id"],
                parent=entry["parent"],
                description=entry.get("description"),
                default_chronicle_location=entry.get(
                    "default_chronicle_location"
                ),
            )
        )

    return MetadataConfig(layouts_dir=layouts_dir, rules=rules)


_CONNECTORS = ("of", "at", "the", "to", "and", "for")
"""Common lowercase connector words that get smushed in CamelCase filenames."""

# "on" is included with a negative lookbehind for "i" to avoid
# splitting words ending in "-ion" (e.g. Initiation, Revolution).
_CONNECTOR_ALTS = "|".join(_CONNECTORS) + r"|(?<!i)on"

_CONNECTOR_PATTERN = re.compile(
    r"\b([A-Z][a-z]+)(" + _CONNECTOR_ALTS + r")\b"
)


def _split_connectors(text: str) -> str:
    """Split words that end with a smushed connector word.

    Only matches words that start with an uppercase letter followed by
    lowercase letters, ending with a known connector. This avoids
    false splits inside words like "Initiation" or "Mountain".
    """
    return _CONNECTOR_PATTERN.sub(r"\1 \2", text)


def split_camel_case(text: str) -> str:
    """Insert spaces into a smushed CamelCase scenario name.

    1. Split at uppercase-after-lowercase and digit-letter boundaries.
    2. Iteratively peel off trailing connector words (of, at, the, in,
       is, on, to, and, or, for) from capitalized words until stable.

    For example, ``OriginoftheOpenRoad`` becomes
    ``Origin of the Open Road``.

    Args:
        text: CamelCase string to split.

    Returns:
        String with spaces inserted at word boundaries.
    """
    result = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    result = re.sub(r"(\d)([A-Za-z])", r"\1 \2", result)
    result = re.sub(r"([A-Za-z])(\d)", r"\1 \2", result)

    while True:
        updated = _split_connectors(result)
        if updated == result:
            break
        result = updated

    return result


def apply_substitutions(template: str, match: re.Match) -> str:
    """Replace $0, $1, $2, etc. in a template with regex match groups.

    Also supports ``${~N}`` syntax which applies CamelCase splitting
    to group N before substitution.

    Args:
        template: String containing substitution references.
        match: The regex match object providing group values.

    Returns:
        Template with all valid references replaced.

    Requirements: layout-generator 15.1, 15.2, 15.3
    """
    num_groups = len(match.groups())

    def replace_camel_reference(ref: re.Match) -> str:
        index = int(ref.group(1))
        if index == 0:
            return split_camel_case(match.group(0))
        if index <= num_groups:
            return split_camel_case(match.group(index))
        print(
            f"Warning: template references non-existent "
            f"capture group ${{~{index}}}",
            file=sys.stderr,
        )
        return ref.group(0)

    def replace_reference(ref: re.Match) -> str:
        index = int(ref.group(1))
        if index == 0:
            return match.group(0)
        if index <= num_groups:
            return match.group(index)
        print(
            f"Warning: template references non-existent "
            f"capture group ${index}",
            file=sys.stderr,
        )
        return ref.group(0)

    # Process ${~N} references first (CamelCase-split)
    result = re.sub(r"\$\{~(\d+)\}", replace_camel_reference, template)
    # Then process plain $N references
    return re.sub(r"\$(\d+)", replace_reference, result)


def match_rule(
    relative_path: str,
    config: MetadataConfig,
) -> MatchedMetadata | None:
    """Test rules in order and return metadata for the first match.

    Args:
        relative_path: PDF path relative to the pdf_path directory
            (or filename for single-file mode).
        config: Parsed TOML metadata configuration.

    Returns:
        MatchedMetadata with substitutions applied, or None if no
        rule matches.

    Requirements: layout-generator 2.7, 15.1, 15.2, 15.4
    """
    for rule in config.rules:
        compiled = re.compile(rule.pattern)
        m = compiled.search(relative_path)
        if m is None:
            continue

        resolved_id = apply_substitutions(rule.id, m)
        resolved_parent = apply_substitutions(rule.parent, m)
        resolved_description = (
            apply_substitutions(rule.description, m)
            if rule.description is not None
            else None
        )
        resolved_location = (
            apply_substitutions(rule.default_chronicle_location, m)
            if rule.default_chronicle_location is not None
            else None
        )

        return MatchedMetadata(
            id=resolved_id,
            parent=resolved_parent,
            description=resolved_description,
            default_chronicle_location=resolved_location,
        )

    return None
