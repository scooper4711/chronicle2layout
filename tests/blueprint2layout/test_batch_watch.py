"""Property-based and unit tests for blueprint batch & watch functions.

Tests match_blueprint_ids, resolve_default_chronicle_location,
and resolve_chronicle_pdf from blueprint2layout.__main__.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from blueprint2layout.__main__ import (
    match_blueprint_ids,
    resolve_chronicle_pdf,
    resolve_default_chronicle_location,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Simple id-like strings: lowercase letters, digits, dots, dashes
_id_char = st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789.-")
_blueprint_id = st.text(_id_char, min_size=1, max_size=20)

# Patterns that include at least one wildcard character
_wildcard_pattern = st.text(
    st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789.-*?"),
    min_size=1,
    max_size=20,
).filter(lambda p: any(ch in p for ch in ("*", "?", "[")))

# Blueprint index: dict mapping ids to dummy Paths
_blueprint_index = st.dictionaries(
    keys=_blueprint_id,
    values=st.builds(Path, st.just("dummy.json")),
    min_size=1,
    max_size=15,
)


# ---------------------------------------------------------------------------
# Feature: blueprint-batch-watch, Property 1: Wildcard matching returns
# the correct sorted set
# ---------------------------------------------------------------------------


import fnmatch as _fnmatch_mod


class TestMatchBlueprintIdsProperty:
    """Property 1: Wildcard matching returns the correct sorted set.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """

    @given(index=_blueprint_index, pattern=_wildcard_pattern)
    @settings(max_examples=100)
    def test_wildcard_matches_equal_fnmatch_filtering(
        self, index: dict[str, Path], pattern: str,
    ):
        """Wildcard pattern returns sorted fnmatch-filtered ids or raises."""
        expected = sorted(
            bid for bid in index if _fnmatch_mod.fnmatch(bid, pattern)
        )
        if expected:
            result = match_blueprint_ids(pattern, index)
            assert result == expected
        else:
            with pytest.raises(ValueError):
                match_blueprint_ids(pattern, index)

    @given(index=_blueprint_index)
    @settings(max_examples=100)
    def test_literal_lookup_returns_single_id(
        self, index: dict[str, Path],
    ):
        """Literal (non-wildcard) pattern returns the id if present."""
        assume(len(index) > 0)
        # Pick an arbitrary id from the index
        literal_id = sorted(index.keys())[0]
        result = match_blueprint_ids(literal_id, index)
        assert result == [literal_id]

    @given(index=_blueprint_index)
    @settings(max_examples=100)
    def test_literal_not_found_raises(
        self, index: dict[str, Path],
    ):
        """Literal id not in the index raises ValueError."""
        missing = "zzz-definitely-not-in-index"
        assume(missing not in index)
        with pytest.raises(ValueError):
            match_blueprint_ids(missing, index)


# ---------------------------------------------------------------------------
# Feature: blueprint-batch-watch, Property 2: Chronicle resolution returns
# the leaf-most defaultChronicleLocation
# ---------------------------------------------------------------------------


@st.composite
def _chain_with_chronicle_locations(draw):
    """Generate a random inheritance chain with optional chronicle locations.

    Returns (tmp_path_factory_not_needed, chain_data) where chain_data is
    a list of dicts from root to leaf, each with an 'id', optional 'parent',
    and optional 'defaultChronicleLocation'.
    """
    length = draw(st.integers(min_value=1, max_value=5))
    chain = []
    for i in range(length):
        node_id = f"node{i}"
        node: dict = {"id": node_id}
        if i > 0:
            node["parent"] = f"node{i - 1}"
        if draw(st.booleans()):
            node["defaultChronicleLocation"] = f"chronicles/sheet{i}.pdf"
        chain.append(node)
    return chain


class TestResolveDefaultChronicleLocationProperty:
    """Property 2: Chronicle resolution returns the leaf-most value.

    **Validates: Requirements 3.1, 3.2, 3.3**
    """

    @given(chain_data=_chain_with_chronicle_locations())
    @settings(max_examples=100)
    def test_returns_leaf_most_chronicle_location(
        self, chain_data: list[dict], tmp_path_factory,
    ):
        """Resolution returns the leaf-most defaultChronicleLocation."""
        # Write chain to temp files and build index
        tmp_dir = tmp_path_factory.mktemp("blueprints")
        index: dict[str, Path] = {}
        for node in chain_data:
            file_path = tmp_dir / f"{node['id']}.json"
            file_path.write_text(json.dumps(node), encoding="utf-8")
            index[node["id"]] = file_path

        leaf_id = chain_data[-1]["id"]
        leaf_path = index[leaf_id]

        result = resolve_default_chronicle_location(leaf_path, index)

        # Compute expected: walk from leaf toward root, return first found
        expected = None
        for node in reversed(chain_data):
            if "defaultChronicleLocation" in node:
                expected = node["defaultChronicleLocation"]
                break

        assert result == expected


# ---------------------------------------------------------------------------
# Unit tests for match_blueprint_ids
# ---------------------------------------------------------------------------


class TestMatchBlueprintIdsUnit:
    """Unit tests for match_blueprint_ids edge cases.

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """

    def test_empty_index_wildcard_raises(self):
        """Wildcard against empty index raises ValueError."""
        with pytest.raises(ValueError, match="No blueprint ids match"):
            match_blueprint_ids("*", {})

    def test_empty_index_literal_raises(self):
        """Literal id against empty index raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            match_blueprint_ids("foo", {})

    def test_no_match_wildcard_raises(self):
        """Wildcard that matches nothing raises ValueError."""
        index = {"alpha": Path("a.json"), "beta": Path("b.json")}
        with pytest.raises(ValueError, match="No blueprint ids match"):
            match_blueprint_ids("zzz*", index)

    def test_literal_not_found_raises(self):
        """Literal id not in index raises ValueError."""
        index = {"alpha": Path("a.json")}
        with pytest.raises(ValueError, match="not found"):
            match_blueprint_ids("beta", index)

    def test_wildcard_returns_sorted(self):
        """Wildcard returns matches in sorted order."""
        index = {
            "pfs2.c": Path("c.json"),
            "pfs2.a": Path("a.json"),
            "pfs2.b": Path("b.json"),
            "sfs.x": Path("x.json"),
        }
        result = match_blueprint_ids("pfs2.*", index)
        assert result == ["pfs2.a", "pfs2.b", "pfs2.c"]

    def test_literal_returns_single(self):
        """Literal id returns a single-element list."""
        index = {"alpha": Path("a.json"), "beta": Path("b.json")}
        assert match_blueprint_ids("alpha", index) == ["alpha"]


# ---------------------------------------------------------------------------
# Unit tests for resolve_chronicle_pdf
# ---------------------------------------------------------------------------


class TestResolveChroniclePdfUnit:
    """Unit tests for resolve_chronicle_pdf error paths.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """

    def test_no_location_in_chain_raises(self, tmp_path):
        """Raises ValueError when no blueprint defines the location."""
        bp = {"id": "leaf"}
        bp_path = tmp_path / "leaf.json"
        bp_path.write_text(json.dumps(bp), encoding="utf-8")
        index = {"leaf": bp_path}

        with pytest.raises(ValueError, match="no defaultChronicleLocation"):
            resolve_chronicle_pdf("leaf", index)

    def test_missing_pdf_on_disk_raises(self, tmp_path):
        """Raises FileNotFoundError when the resolved PDF doesn't exist."""
        bp = {
            "id": "leaf",
            "defaultChronicleLocation": "nonexistent/file.pdf",
        }
        bp_path = tmp_path / "leaf.json"
        bp_path.write_text(json.dumps(bp), encoding="utf-8")
        index = {"leaf": bp_path}

        with pytest.raises(FileNotFoundError, match="Chronicle PDF not found"):
            resolve_chronicle_pdf("leaf", index)

    def test_resolves_existing_pdf(self, tmp_path):
        """Returns the Path when the PDF exists on disk."""
        pdf_path = tmp_path / "chronicle.pdf"
        pdf_path.write_text("fake pdf", encoding="utf-8")

        bp = {
            "id": "leaf",
            "defaultChronicleLocation": str(pdf_path),
        }
        bp_path = tmp_path / "leaf.json"
        bp_path.write_text(json.dumps(bp), encoding="utf-8")
        index = {"leaf": bp_path}

        result = resolve_chronicle_pdf("leaf", index)
        assert result == pdf_path

    def test_inherits_location_from_parent(self, tmp_path):
        """Resolves location from parent when leaf doesn't define it."""
        pdf_path = tmp_path / "parent_chronicle.pdf"
        pdf_path.write_text("fake pdf", encoding="utf-8")

        parent = {
            "id": "root",
            "defaultChronicleLocation": str(pdf_path),
        }
        child = {"id": "leaf", "parent": "root"}

        parent_path = tmp_path / "root.json"
        parent_path.write_text(json.dumps(parent), encoding="utf-8")
        child_path = tmp_path / "leaf.json"
        child_path.write_text(json.dumps(child), encoding="utf-8")

        index = {"root": parent_path, "leaf": child_path}
        result = resolve_chronicle_pdf("leaf", index)
        assert result == pdf_path


# ---------------------------------------------------------------------------
# Import derive_output_path for Task 2 tests
# ---------------------------------------------------------------------------

from blueprint2layout.__main__ import derive_output_path


# ---------------------------------------------------------------------------
# Hypothesis strategies for derive_output_path
# ---------------------------------------------------------------------------

# Blueprint id segments: lowercase letters and digits only (no dots/slashes)
_segment_char = st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-")
_segment = st.text(_segment_char, min_size=1, max_size=12)

# Blueprint id with at least one dot: prefix.suffix (suffix may contain dots)
_blueprint_id_with_dot = st.builds(
    lambda prefix, parts: prefix + "." + ".".join(parts),
    prefix=_segment,
    parts=st.lists(_segment, min_size=1, max_size=3),
)

# Relative subdirectory path (0 to 3 segments deep)
_relative_subdir_parts = st.lists(_segment, min_size=0, max_size=3)


# ---------------------------------------------------------------------------
# Feature: blueprint-batch-watch, Property 3: Output path derivation
# preserves directory structure and strips id prefix
# ---------------------------------------------------------------------------


class TestDeriveOutputPathProperty:
    """Property 3: Output path derivation preserves directory structure
    and strips id prefix.

    **Validates: Requirements 4.1, 4.2, 4.3**
    """

    @given(
        blueprint_id=_blueprint_id_with_dot,
        subdir_parts=_relative_subdir_parts,
        output_dir_name=_segment,
    )
    @settings(max_examples=100)
    def test_derived_path_structure(
        self,
        blueprint_id: str,
        subdir_parts: list[str],
        output_dir_name: str,
    ):
        """Derived path equals output_dir / relative_subdir / stripped_id.json."""
        blueprints_dir = Path("/blueprints")
        output_dir = Path("/output") / output_dir_name

        # Build the blueprint file path under the subdirectory
        subdir = Path(*subdir_parts) if subdir_parts else Path(".")
        blueprint_path = blueprints_dir / subdir / "dummy.blueprint.json"

        result = derive_output_path(
            blueprint_id, blueprint_path, blueprints_dir, output_dir,
        )

        # Expected filename: strip prefix up to first dot, append .json
        dot_index = blueprint_id.index(".")
        expected_filename = blueprint_id[dot_index + 1:] + ".json"

        # Expected relative subdir
        expected_subdir = blueprint_path.parent.relative_to(blueprints_dir)

        expected = output_dir / expected_subdir / expected_filename
        assert result == expected

    @given(
        blueprint_id=_blueprint_id_with_dot,
        output_dir_name=_segment,
    )
    @settings(max_examples=100)
    def test_root_dir_produces_no_subdir(
        self,
        blueprint_id: str,
        output_dir_name: str,
    ):
        """Blueprint in root of blueprints_dir produces output directly in output_dir."""
        blueprints_dir = Path("/blueprints")
        output_dir = Path("/output") / output_dir_name
        blueprint_path = blueprints_dir / "dummy.blueprint.json"

        result = derive_output_path(
            blueprint_id, blueprint_path, blueprints_dir, output_dir,
        )

        assert result.parent == output_dir


# ---------------------------------------------------------------------------
# Unit tests for derive_output_path
# ---------------------------------------------------------------------------


class TestDeriveOutputPathUnit:
    """Unit tests for derive_output_path edge cases.

    **Validates: Requirements 4.1, 4.2, 4.3**
    """

    def test_blueprint_in_root_dir(self):
        """Blueprint in root dir produces output directly in output_dir."""
        result = derive_output_path(
            "pfs2.bounty-layout-b13",
            Path("/blueprints/b13.blueprint.json"),
            Path("/blueprints"),
            Path("/output"),
        )
        assert result == Path("/output/bounty-layout-b13.json")

    def test_deeply_nested_subdirectory(self):
        """Blueprint in a deeply nested subdirectory mirrors the structure."""
        result = derive_output_path(
            "pfs2.bounty-layout-b13",
            Path("/blueprints/pfs2/bounties/deep/b13.blueprint.json"),
            Path("/blueprints"),
            Path("/output"),
        )
        assert result == Path("/output/pfs2/bounties/deep/bounty-layout-b13.json")

    def test_id_with_single_dot(self):
        """Id with a single dot strips the prefix correctly."""
        result = derive_output_path(
            "pfs2.layout",
            Path("/blueprints/pfs2.blueprint.json"),
            Path("/blueprints"),
            Path("/output"),
        )
        assert result == Path("/output/layout.json")

    def test_id_with_multiple_dots(self):
        """Id with multiple dots strips only up to the first dot."""
        result = derive_output_path(
            "pfs2.bounty.layout.b13",
            Path("/blueprints/pfs2/b13.blueprint.json"),
            Path("/blueprints"),
            Path("/output"),
        )
        assert result == Path("/output/pfs2/bounty.layout.b13.json")


# ---------------------------------------------------------------------------
# Import watch mode helpers for Task 4 tests
# ---------------------------------------------------------------------------

from blueprint2layout.__main__ import (
    _build_dependency_map,
    _record_mtimes,
    _find_changed_paths,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies for _build_dependency_map
# ---------------------------------------------------------------------------


@st.composite
def _index_with_chains(draw):
    """Generate a blueprint index with inheritance chains.

    Returns (tmp_dir, blueprint_ids, index) where:
    - tmp_dir is a Path to a temp directory containing blueprint JSON files
    - blueprint_ids is a list of leaf blueprint ids to watch
    - index is a dict mapping ids to file paths
    """
    # Generate 1-4 chains, each 1-3 nodes deep
    num_chains = draw(st.integers(min_value=1, max_value=4))
    all_nodes: list[dict] = []
    leaf_ids: list[str] = []

    for chain_idx in range(num_chains):
        chain_length = draw(st.integers(min_value=1, max_value=3))
        for node_idx in range(chain_length):
            node_id = f"chain{chain_idx}.node{node_idx}"
            node: dict = {"id": node_id}
            if node_idx > 0:
                node["parent"] = f"chain{chain_idx}.node{node_idx - 1}"
            all_nodes.append(node)
        leaf_ids.append(f"chain{chain_idx}.node{chain_length - 1}")

    return all_nodes, leaf_ids


# ---------------------------------------------------------------------------
# Feature: blueprint-batch-watch, Property 4: Watched paths cover all
# files in all inheritance chains
# ---------------------------------------------------------------------------


class TestBuildDependencyMapProperty:
    """Property 4: Dependency map covers all files in all inheritance chains.

    **Validates: Requirements 6.3**
    """

    @given(chain_data=_index_with_chains())
    @settings(max_examples=100)
    def test_dependency_map_covers_all_chain_files(
        self,
        chain_data: tuple[list[dict], list[str]],
        tmp_path_factory,
    ):
        """Dependency map keys are a superset of all chain files."""
        all_nodes, leaf_ids = chain_data

        # Write all nodes to temp files and build index
        tmp_dir = tmp_path_factory.mktemp("blueprints")
        index: dict[str, Path] = {}
        for node in all_nodes:
            file_path = tmp_dir / f"{node['id']}.blueprint.json"
            file_path.write_text(json.dumps(node), encoding="utf-8")
            index[node["id"]] = file_path

        dep_map = _build_dependency_map(tmp_dir, leaf_ids)

        # Verify superset: every file in every chain must be present
        from shared.layout_index import collect_inheritance_chain

        for leaf_id in leaf_ids:
            leaf_path = index[leaf_id]
            chain = collect_inheritance_chain(leaf_path, index)
            for path, _data in chain:
                assert path in dep_map, (
                    f"Path {path} from chain of {leaf_id} not in dependency map"
                )
                assert leaf_id in dep_map[path], (
                    f"Leaf {leaf_id} not mapped for {path}"
                )


# ---------------------------------------------------------------------------
# Unit tests for watch mode helpers
# ---------------------------------------------------------------------------


class TestRecordMtimesUnit:
    """Unit tests for _record_mtimes.

    **Validates: Requirements 6.1, 6.2**
    """

    def test_records_mtimes_for_real_files(self, tmp_path):
        """Returns mtime dict for each file path."""
        file_a = tmp_path / "a.json"
        file_b = tmp_path / "b.json"
        file_a.write_text("{}", encoding="utf-8")
        file_b.write_text("{}", encoding="utf-8")

        result = _record_mtimes([file_a, file_b])

        assert set(result.keys()) == {file_a, file_b}
        assert isinstance(result[file_a], float)
        assert isinstance(result[file_b], float)

    def test_empty_list_returns_empty_dict(self):
        """Empty path list returns empty dict."""
        assert _record_mtimes([]) == {}


class TestFindChangedPathsUnit:
    """Unit tests for _find_changed_paths.

    **Validates: Requirements 6.1, 6.2**
    """

    def test_detects_modification(self, tmp_path):
        """Returns changed path when a file's mtime changes."""
        file_a = tmp_path / "a.json"
        file_a.write_text("{}", encoding="utf-8")

        paths = [file_a]
        mtimes = _record_mtimes(paths)

        # Modify the file — force a different mtime
        import time as _time
        _time.sleep(0.05)
        file_a.write_text('{"changed": true}', encoding="utf-8")

        changed = _find_changed_paths(paths, mtimes)
        assert file_a in changed

    def test_no_change_returns_empty(self, tmp_path):
        """Returns empty list when no files have changed."""
        file_a = tmp_path / "a.json"
        file_a.write_text("{}", encoding="utf-8")

        paths = [file_a]
        mtimes = _record_mtimes(paths)

        assert _find_changed_paths(paths, mtimes) == []

    def test_empty_paths_returns_empty(self):
        """Empty path list always returns empty list."""
        assert _find_changed_paths([], {}) == []


# ---------------------------------------------------------------------------
# Import parse_args and main for Task 5 tests
# ---------------------------------------------------------------------------

from blueprint2layout.__main__ import parse_args, main


# ---------------------------------------------------------------------------
# Unit tests for parse_args
# ---------------------------------------------------------------------------


class TestParseArgsUnit:
    """Unit tests for parse_args.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
    """

    def test_required_args(self):
        """Both --blueprints-dir and --blueprint-id are required."""
        args = parse_args([
            "--blueprints-dir", "/some/dir",
            "--blueprint-id", "pfs2.bounty-layout-b13",
        ])
        assert args.blueprints_dir == Path("/some/dir")
        assert args.blueprint_id == "pfs2.bounty-layout-b13"

    def test_output_dir_default(self):
        """--output-dir defaults to current directory."""
        args = parse_args([
            "--blueprints-dir", "/dir",
            "--blueprint-id", "x",
        ])
        assert args.output_dir == Path(".")

    def test_output_dir_custom(self):
        """--output-dir accepts a custom path."""
        args = parse_args([
            "--blueprints-dir", "/dir",
            "--blueprint-id", "x",
            "--output-dir", "/custom/output",
        ])
        assert args.output_dir == Path("/custom/output")

    def test_watch_flag_default(self):
        """--watch defaults to False."""
        args = parse_args([
            "--blueprints-dir", "/dir",
            "--blueprint-id", "x",
        ])
        assert args.watch is False

    def test_watch_flag_enabled(self):
        """--watch sets the flag to True."""
        args = parse_args([
            "--blueprints-dir", "/dir",
            "--blueprint-id", "x",
            "--watch",
        ])
        assert args.watch is True

    def test_missing_blueprints_dir_exits(self):
        """Missing --blueprints-dir causes SystemExit."""
        with pytest.raises(SystemExit):
            parse_args(["--blueprint-id", "x"])

    def test_missing_blueprint_id_exits(self):
        """Missing --blueprint-id causes SystemExit."""
        with pytest.raises(SystemExit):
            parse_args(["--blueprints-dir", "/dir"])


# ---------------------------------------------------------------------------
# Unit tests for main
# ---------------------------------------------------------------------------


class TestMainUnit:
    """Unit tests for main.

    **Validates: Requirements 1.1–1.5, 5.3, 7.1, 7.4**
    """

    def test_invalid_blueprints_dir(self, tmp_path, capsys):
        """Returns 1 and prints error when --blueprints-dir is not a directory."""
        fake_path = tmp_path / "nonexistent"
        result = main([
            "--blueprints-dir", str(fake_path),
            "--blueprint-id", "x",
        ])
        assert result == 1
        captured = capsys.readouterr()
        assert "not a directory" in captured.err
        assert str(fake_path) in captured.err

    def test_no_matching_ids(self, tmp_path, capsys):
        """Returns 1 when no blueprint ids match the pattern."""
        # Create an empty blueprints dir (no .blueprint.json files)
        result = main([
            "--blueprints-dir", str(tmp_path),
            "--blueprint-id", "nonexistent",
        ])
        assert result == 1
        assert "not found" in capsys.readouterr().err

    def test_successful_batch_run(self, tmp_path, capsys):
        """Returns 0 and writes output for a successful batch run."""
        blueprints_dir = tmp_path / "blueprints"
        blueprints_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a minimal blueprint with a chronicle location
        pdf_path = tmp_path / "chronicle.pdf"
        pdf_path.write_text("fake pdf", encoding="utf-8")

        bp = {
            "id": "test.layout-a",
            "defaultChronicleLocation": str(pdf_path),
        }
        bp_path = blueprints_dir / "a.blueprint.json"
        bp_path.write_text(json.dumps(bp), encoding="utf-8")

        with patch("blueprint2layout.__main__.generate_layout") as mock_gen, \
             patch("blueprint2layout.__main__.write_layout") as mock_write:
            mock_gen.return_value = {"id": "test.layout-a", "canvases": []}

            result = main([
                "--blueprints-dir", str(blueprints_dir),
                "--blueprint-id", "test.layout-a",
                "--output-dir", str(output_dir),
            ])

        assert result == 0
        mock_gen.assert_called_once()
        mock_write.assert_called_once()
        captured = capsys.readouterr()
        assert "Wrote" in captured.out

    def test_watch_mode_entry(self, tmp_path):
        """In watch mode, watch_and_regenerate is called and main returns 0."""
        blueprints_dir = tmp_path / "blueprints"
        blueprints_dir.mkdir()

        pdf_path = tmp_path / "chronicle.pdf"
        pdf_path.write_text("fake pdf", encoding="utf-8")

        bp = {
            "id": "test.layout-w",
            "defaultChronicleLocation": str(pdf_path),
        }
        bp_path = blueprints_dir / "w.blueprint.json"
        bp_path.write_text(json.dumps(bp), encoding="utf-8")

        with patch("blueprint2layout.__main__.watch_and_regenerate") as mock_watch:
            result = main([
                "--blueprints-dir", str(blueprints_dir),
                "--blueprint-id", "test.layout-w",
                "--watch",
            ])

        assert result == 0
        mock_watch.assert_called_once()
        call_args = mock_watch.call_args
        assert call_args[0][0] == blueprints_dir
        targets = call_args[0][1]
        assert len(targets) == 1
        assert targets[0][0] == "test.layout-w"

    def test_pipeline_error_returns_1(self, tmp_path, capsys):
        """Returns 1 when the pipeline raises an error."""
        blueprints_dir = tmp_path / "blueprints"
        blueprints_dir.mkdir()

        pdf_path = tmp_path / "chronicle.pdf"
        pdf_path.write_text("fake pdf", encoding="utf-8")

        bp = {
            "id": "test.layout-err",
            "defaultChronicleLocation": str(pdf_path),
        }
        bp_path = blueprints_dir / "err.blueprint.json"
        bp_path.write_text(json.dumps(bp), encoding="utf-8")

        with patch("blueprint2layout.__main__.generate_layout") as mock_gen:
            mock_gen.side_effect = ValueError("Pipeline broke")
            result = main([
                "--blueprints-dir", str(blueprints_dir),
                "--blueprint-id", "test.layout-err",
            ])

        assert result == 1
        captured = capsys.readouterr()
        assert "Pipeline broke" in captured.err

    def test_error_messages_go_to_stderr(self, tmp_path, capsys):
        """All error messages are printed to stderr, not stdout."""
        fake_path = tmp_path / "nope"
        main([
            "--blueprints-dir", str(fake_path),
            "--blueprint-id", "x",
        ])
        captured = capsys.readouterr()
        assert captured.err  # stderr has content
        assert "Error" in captured.err
