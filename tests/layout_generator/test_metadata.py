"""Unit tests for layout_generator.metadata module.

Tests load_metadata, apply_substitutions, and match_rule with
concrete TOML fixtures, edge cases, and error conditions.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.9,
    15.1, 15.2, 15.3, 15.4
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from layout_generator.metadata import (
    MatchedMetadata,
    MetadataConfig,
    MetadataRule,
    apply_substitutions,
    load_metadata,
    match_rule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_TOML_ALL_FIELDS = """\
layouts_dir = "/some/layouts"

[[rules]]
pattern = "season(\\\\d+)/s\\\\d+-(?P<num>\\\\d+)"
id = "pfs2-s$1-$2"
parent = "pfs2-season$1"
description = "Season $1 scenario $2"
default_chronicle_location = "chronicles/s$1/$2.pdf"

[[rules]]
pattern = "bounties/b(\\\\d+)"
id = "pfs2-b$1"
parent = "pfs2-bounties"
"""

VALID_TOML_MINIMAL = """\
[[rules]]
pattern = ".*\\\\.pdf"
id = "catch-all"
parent = "base"
"""


def write_toml(tmp_path: Path, content: str, name: str = "meta.toml") -> Path:
    """Write TOML content to a temp file and return its path."""
    path = tmp_path / name
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# load_metadata — valid TOML with all fields
# ---------------------------------------------------------------------------


class TestLoadMetadataValid:
    """Tests for load_metadata with well-formed TOML files."""

    def test_parses_layouts_dir(self, tmp_path: Path) -> None:
        """Layouts_dir is read from the TOML global property."""
        path = write_toml(tmp_path, VALID_TOML_ALL_FIELDS)
        config = load_metadata(path)
        assert config.layouts_dir == "/some/layouts"

    def test_parses_all_rule_fields(self, tmp_path: Path) -> None:
        """All required and optional rule fields are populated."""
        path = write_toml(tmp_path, VALID_TOML_ALL_FIELDS)
        config = load_metadata(path)
        rule = config.rules[0]

        assert rule.pattern is not None
        assert rule.id == "pfs2-s$1-$2"
        assert rule.parent == "pfs2-season$1"
        assert rule.description == "Season $1 scenario $2"
        assert rule.default_chronicle_location == "chronicles/s$1/$2.pdf"

    def test_parses_multiple_rules_in_order(self, tmp_path: Path) -> None:
        """Rules list preserves TOML declaration order."""
        path = write_toml(tmp_path, VALID_TOML_ALL_FIELDS)
        config = load_metadata(path)
        assert len(config.rules) == 2
        assert config.rules[1].id == "pfs2-b$1"

    def test_optional_fields_omitted(self, tmp_path: Path) -> None:
        """Optional fields default to None when not in TOML."""
        path = write_toml(tmp_path, VALID_TOML_MINIMAL)
        config = load_metadata(path)
        rule = config.rules[0]

        assert rule.description is None
        assert rule.default_chronicle_location is None

    def test_layouts_dir_omitted(self, tmp_path: Path) -> None:
        """layouts_dir is None when not present in TOML."""
        path = write_toml(tmp_path, VALID_TOML_MINIMAL)
        config = load_metadata(path)
        assert config.layouts_dir is None

    def test_empty_rules_list(self, tmp_path: Path) -> None:
        """A TOML with no rules produces an empty rules list."""
        path = write_toml(tmp_path, 'layouts_dir = "/layouts"\n')
        config = load_metadata(path)
        assert config.rules == []


# ---------------------------------------------------------------------------
# load_metadata — error conditions
# ---------------------------------------------------------------------------


class TestLoadMetadataErrors:
    """Tests for load_metadata error handling."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """FileNotFoundError raised when the TOML file does not exist."""
        missing = tmp_path / "nonexistent.toml"
        with pytest.raises(FileNotFoundError, match="Metadata file not found"):
            load_metadata(missing)

    def test_malformed_toml_raises(self, tmp_path: Path) -> None:
        """ValueError raised for syntactically invalid TOML."""
        path = write_toml(tmp_path, "this is [not valid toml")
        with pytest.raises(ValueError, match="Malformed TOML"):
            load_metadata(path)

    def test_missing_pattern_field_raises(self, tmp_path: Path) -> None:
        """ValueError raised when a rule is missing 'pattern'."""
        content = '[[rules]]\nid = "x"\nparent = "y"\n'
        path = write_toml(tmp_path, content)
        with pytest.raises(ValueError, match="missing required field 'pattern'"):
            load_metadata(path)

    def test_missing_id_field_raises(self, tmp_path: Path) -> None:
        """ValueError raised when a rule is missing 'id'."""
        content = '[[rules]]\npattern = ".*"\nparent = "y"\n'
        path = write_toml(tmp_path, content)
        with pytest.raises(ValueError, match="missing required field 'id'"):
            load_metadata(path)

    def test_missing_parent_field_raises(self, tmp_path: Path) -> None:
        """ValueError raised when a rule is missing 'parent'."""
        content = '[[rules]]\npattern = ".*"\nid = "x"\n'
        path = write_toml(tmp_path, content)
        with pytest.raises(ValueError, match="missing required field 'parent'"):
            load_metadata(path)


# ---------------------------------------------------------------------------
# apply_substitutions
# ---------------------------------------------------------------------------


class TestApplySubstitutions:
    """Tests for apply_substitutions template replacement."""

    def test_single_group(self) -> None:
        """$1 is replaced with the first capture group."""
        m = re.search(r"s(\d+)", "s42")
        assert m is not None
        assert apply_substitutions("season-$1", m) == "season-42"

    def test_multiple_groups(self) -> None:
        """$1 and $2 are replaced with their respective groups."""
        m = re.search(r"s(\d+)-(\d+)", "s1-05")
        assert m is not None
        result = apply_substitutions("season$1-scenario$2", m)
        assert result == "season1-scenario05"

    def test_full_match_with_dollar_zero(self) -> None:
        """$0 is replaced with the entire matched string."""
        m = re.search(r"bounty-\d+", "bounty-13")
        assert m is not None
        assert apply_substitutions("id=$0", m) == "id=bounty-13"

    def test_nonexistent_group_left_as_literal(self, capsys) -> None:
        """References to non-existent groups remain as literal text."""
        m = re.search(r"s(\d+)", "s7")
        assert m is not None
        result = apply_substitutions("$1-$3", m)
        assert result == "7-$3"

        captured = capsys.readouterr()
        assert "non-existent capture group $3" in captured.err

    def test_no_references_returns_unchanged(self) -> None:
        """A template with no $ references is returned as-is."""
        m = re.search(r"abc", "abc")
        assert m is not None
        assert apply_substitutions("no-refs-here", m) == "no-refs-here"

    def test_adjacent_references(self) -> None:
        """Adjacent $1$2 are both replaced."""
        m = re.search(r"(\w)(\w)", "ab")
        assert m is not None
        assert apply_substitutions("$1$2", m) == "ab"


# ---------------------------------------------------------------------------
# match_rule
# ---------------------------------------------------------------------------


class TestMatchRule:
    """Tests for match_rule first-match semantics and substitution."""

    def _make_config(self, rules: list[MetadataRule]) -> MetadataConfig:
        """Build a MetadataConfig with the given rules."""
        return MetadataConfig(layouts_dir=None, rules=rules)

    def test_first_match_wins(self) -> None:
        """The first matching rule is used, even if later rules also match."""
        rules = [
            MetadataRule(pattern=r".*\.pdf", id="first", parent="p1"),
            MetadataRule(pattern=r".*\.pdf", id="second", parent="p2"),
        ]
        result = match_rule("test.pdf", self._make_config(rules))
        assert result is not None
        assert result.id == "first"
        assert result.parent == "p1"

    def test_no_match_returns_none(self) -> None:
        """None is returned when no rule pattern matches."""
        rules = [
            MetadataRule(pattern=r"^season\d+", id="x", parent="y"),
        ]
        result = match_rule("bounties/b1.pdf", self._make_config(rules))
        assert result is None

    def test_substitution_in_all_template_fields(self) -> None:
        """Capture groups are substituted in id, parent, description,
        and default_chronicle_location."""
        rules = [
            MetadataRule(
                pattern=r"s(\d+)/(\w+)\.pdf",
                id="layout-$1-$2",
                parent="parent-$1",
                description="Season $1 file $2",
                default_chronicle_location="chronicles/$1/$2.pdf",
            ),
        ]
        result = match_rule("s3/quest.pdf", self._make_config(rules))
        assert result is not None
        assert result.id == "layout-3-quest"
        assert result.parent == "parent-3"
        assert result.description == "Season 3 file quest"
        assert result.default_chronicle_location == "chronicles/3/quest.pdf"

    def test_optional_fields_none_when_omitted(self) -> None:
        """description and default_chronicle_location are None when
        the matching rule does not define them."""
        rules = [
            MetadataRule(pattern=r".*", id="id", parent="parent"),
        ]
        result = match_rule("anything.pdf", self._make_config(rules))
        assert result is not None
        assert result.description is None
        assert result.default_chronicle_location is None

    def test_skips_non_matching_rules(self) -> None:
        """Rules that don't match are skipped; the third rule matches."""
        rules = [
            MetadataRule(pattern=r"^alpha", id="a", parent="pa"),
            MetadataRule(pattern=r"^beta", id="b", parent="pb"),
            MetadataRule(pattern=r"^gamma", id="g", parent="pg"),
        ]
        result = match_rule("gamma-file.pdf", self._make_config(rules))
        assert result is not None
        assert result.id == "g"

    def test_empty_rules_returns_none(self) -> None:
        """An empty rules list always returns None."""
        result = match_rule("any.pdf", self._make_config([]))
        assert result is None

    def test_dollar_zero_in_match_rule(self) -> None:
        """$0 substitution works through match_rule."""
        rules = [
            MetadataRule(
                pattern=r"bounties/b\d+",
                id="$0-layout",
                parent="base",
            ),
        ]
        result = match_rule("bounties/b13", self._make_config(rules))
        assert result is not None
        assert result.id == "bounties/b13-layout"
