"""CLI integration tests for layout_visualizer.

Tests the CLI entry point via ``layout_visualizer.__main__.main(argv)``,
covering argument validation, error handling, wildcard matching,
output filename derivation, and successful end-to-end runs.

Requirements: 1.1, 1.3, 1.4, 1.5, 8.1, 8.2, 9.1, 9.2, 9.3, 9.4
"""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from layout_visualizer.__main__ import (
    _build_output_filename,
    _collect_watched_paths,
    main,
    match_layout_ids,
    parse_args,
)

LAYOUT_ROOT = Path("modules/pfs-chronicle-generator/assets/layouts")
LAYOUT_ID = "pfs2.b13"
REAL_CHRONICLE_PDF = Path(
    "modules/pfs-chronicle-generator/assets/chronicles"
    "/pfs2/bounties/B13-TheBlackwoodAbundanceChronicle.pdf"
)


def _base_args(
    layout_root: str = str(LAYOUT_ROOT),
    layout_id: str = LAYOUT_ID,
) -> list[str]:
    """Build a base argument list with the required flags."""
    return [
        "--layout-root", layout_root,
        "--layout-id", layout_id,
    ]


# ---------------------------------------------------------------------------
# Missing / invalid arguments
# ---------------------------------------------------------------------------


class TestMissingArguments:
    """Missing required arguments cause argparse to exit non-zero."""

    def test_no_arguments_exits_non_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2

    def test_missing_layout_root_exits_non_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--layout-id", "x"])
        assert exc_info.value.code == 2

    def test_missing_layout_id_exits_non_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--layout-root", "dir"])
        assert exc_info.value.code == 2


class TestInvalidLayoutRoot:
    """A non-existent layout root produces an error and exit code 1."""

    def test_bad_root_returns_one(self, capsys):
        code = main(_base_args(layout_root="nonexistent_dir"))
        assert code == 1

    def test_bad_root_prints_error(self, capsys):
        main(_base_args(layout_root="nonexistent_dir"))
        captured = capsys.readouterr()
        assert "nonexistent_dir" in captured.err


class TestUnknownLayoutId:
    """A layout id not found in the index produces an error and exit code 1."""

    def test_unknown_id_returns_one(self, capsys):
        code = main(_base_args(layout_id="does.not.exist"))
        assert code == 1

    def test_unknown_id_prints_error(self, capsys):
        main(_base_args(layout_id="does.not.exist"))
        captured = capsys.readouterr()
        assert "does.not.exist" in captured.err


class TestNoWildcardMatch:
    """A wildcard pattern matching nothing produces an error."""

    def test_no_match_returns_one(self, capsys):
        code = main(_base_args(layout_id="zzz.no.match.*"))
        assert code == 1

    def test_no_match_prints_error(self, capsys):
        main(_base_args(layout_id="zzz.no.match.*"))
        captured = capsys.readouterr()
        assert "No layout ids match" in captured.err


# ---------------------------------------------------------------------------
# Output filename derivation
# ---------------------------------------------------------------------------


class TestBuildOutputFilename:
    """Output filename is {layout_id}_{chronicle_stem}.png."""

    def test_basic_filename(self):
        result = _build_output_filename(
            "pfs2.b13",
            Path("chronicles/B13-TheBlackwoodAbundanceChronicle.pdf"),
        )
        assert result == "pfs2.b13_B13-TheBlackwoodAbundanceChronicle.png"

    def test_different_layout_same_chronicle(self):
        pdf = Path("chronicles/B1-TheWhitefangWyrmChronicle.pdf")
        name_a = _build_output_filename("pfs2.b01", pdf)
        name_b = _build_output_filename("pfs2.bounty-layout-b1", pdf)
        assert name_a != name_b
        assert name_a.endswith(".png")
        assert name_b.endswith(".png")


# ---------------------------------------------------------------------------
# Wildcard matching
# ---------------------------------------------------------------------------


class TestMatchLayoutIds:
    """match_layout_ids resolves literal ids and wildcard patterns."""

    def test_literal_id_found(self):
        index = {"pfs.b01": Path("a.json"), "pfs.b02": Path("b.json")}
        assert match_layout_ids("pfs.b01", index) == ["pfs.b01"]

    def test_literal_id_not_found_raises(self):
        index = {"pfs.b01": Path("a.json")}
        with pytest.raises(ValueError, match="not found"):
            match_layout_ids("pfs.b99", index)

    def test_wildcard_matches_multiple(self):
        index = {
            "pfs.b01": Path("a.json"),
            "pfs.b02": Path("b.json"),
            "pfs.q14": Path("c.json"),
        }
        result = match_layout_ids("pfs.b*", index)
        assert result == ["pfs.b01", "pfs.b02"]

    def test_wildcard_no_match_raises(self):
        index = {"pfs.b01": Path("a.json")}
        with pytest.raises(ValueError, match="No layout ids match"):
            match_layout_ids("zzz.*", index)

    def test_question_mark_wildcard(self):
        index = {
            "pfs.b01": Path("a.json"),
            "pfs.b02": Path("b.json"),
            "pfs.b13": Path("c.json"),
        }
        result = match_layout_ids("pfs.b0?", index)
        assert result == ["pfs.b01", "pfs.b02"]


# ---------------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Argument parsing produces expected namespace values."""

    def test_default_output_dir_is_cwd(self):
        args = parse_args([
            "--layout-root", "dir",
            "--layout-id", "pfs.b13",
        ])
        assert args.output_dir == Path(".")

    def test_explicit_output_dir(self):
        args = parse_args([
            "--layout-root", "dir",
            "--layout-id", "pfs.b13",
            "--output-dir", "/tmp/out",
        ])
        assert args.output_dir == Path("/tmp/out")

    def test_watch_flag_defaults_false(self):
        args = parse_args([
            "--layout-root", "dir",
            "--layout-id", "pfs.b13",
        ])
        assert args.watch is False

    def test_mode_defaults_to_canvases(self):
        args = parse_args([
            "--layout-root", "dir",
            "--layout-id", "pfs.b13",
        ])
        assert args.mode == "canvases"


# ---------------------------------------------------------------------------
# Watch path collection across multiple layouts
# ---------------------------------------------------------------------------


class TestCollectWatchedPaths:
    """_collect_watched_paths unions inheritance chains for all ids."""

    def test_single_id_returns_chain(self):
        paths = _collect_watched_paths(LAYOUT_ROOT, ["pfs2.b13"])
        assert len(paths) > 0
        assert all(p.exists() for p in paths)

    def test_multiple_ids_unions_chains(self):
        paths_b13 = _collect_watched_paths(LAYOUT_ROOT, ["pfs2.b13"])
        paths_q14 = _collect_watched_paths(LAYOUT_ROOT, ["pfs2.q14"])
        paths_both = _collect_watched_paths(
            LAYOUT_ROOT, ["pfs2.b13", "pfs2.q14"],
        )
        # The union should contain all paths from both individual chains
        assert set(paths_b13) <= set(paths_both)
        assert set(paths_q14) <= set(paths_both)

    def test_shared_ancestor_is_not_duplicated(self):
        # Both pfs2.b01 and pfs2.b02 share pfs2 in their chain.
        # The result should have no duplicates.
        paths = _collect_watched_paths(
            LAYOUT_ROOT, ["pfs2.b01", "pfs2.b02"],
        )
        assert len(paths) == len(set(paths))


# ---------------------------------------------------------------------------
# Successful end-to-end runs
# ---------------------------------------------------------------------------


_skip_no_pdf = pytest.mark.skipif(
    not REAL_CHRONICLE_PDF.exists(),
    reason="Real chronicle PDF not available",
)


class TestSuccessfulRun:
    """End-to-end test with real layout and PDF files."""

    @_skip_no_pdf
    def test_single_layout_produces_png(self, tmp_path):
        args = _base_args() + ["--output-dir", str(tmp_path)]
        code = main(args)

        assert code == 0
        pngs = list(tmp_path.rglob("*.png"))
        assert len(pngs) == 1
        assert "pfs2.b13" in pngs[0].name
        assert pngs[0].stat().st_size > 0

    @_skip_no_pdf
    def test_wildcard_produces_multiple_pngs(self, tmp_path):
        args = _base_args(layout_id="pfs2.b0?") + [
            "--output-dir", str(tmp_path),
        ]
        code = main(args)

        assert code == 0
        pngs = list(tmp_path.rglob("*.png"))
        assert len(pngs) > 1

    @_skip_no_pdf
    def test_output_mirrors_layout_subdirectory(self, tmp_path):
        """PNGs are written under the same subdirectory as the layout file."""
        args = _base_args() + ["--output-dir", str(tmp_path)]
        main(args)

        pngs = list(tmp_path.rglob("*.png"))
        assert len(pngs) == 1
        # pfs2.b13 lives in pfs2/bounties/ relative to layout root
        relative = pngs[0].relative_to(tmp_path)
        assert relative.parts[:-1] == ("pfs2", "bounties")


# ---------------------------------------------------------------------------
# Property test for output filename derivation
# Feature: layout-visualizer, Property 1: Output filename derivation
# ---------------------------------------------------------------------------

_layout_id_segment = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="_-.",
    ),
    min_size=1,
    max_size=30,
).filter(lambda s: not s.startswith("-"))

_pdf_stem = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="_-",
    ),
    min_size=1,
    max_size=30,
)


class TestOutputFilenameProperty:
    """Validates: Requirements 1.4

    Feature: layout-visualizer, Property 1: Output filename derivation
    """

    @given(layout_id=_layout_id_segment, stem=_pdf_stem)
    @settings(max_examples=100)
    def test_output_filename_contains_id_and_stem(
        self,
        layout_id: str,
        stem: str,
    ) -> None:
        """For any layout id and chronicle PDF, the output filename
        contains both the layout id and the chronicle stem, with a
        .png extension.

        Feature: layout-visualizer, Property 1: Output filename derivation
        """
        result = _build_output_filename(layout_id, Path(f"dir/{stem}.pdf"))

        assert result == f"{layout_id}_{stem}.png"
        assert result.endswith(".png")
        assert layout_id in result
        assert stem in result
