"""CLI integration tests and property tests for layout_visualizer.

Tests the CLI entry point via ``layout_visualizer.__main__.main(argv)``,
covering argument validation, error handling, default output path derivation,
and a successful end-to-end run with real files.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 9.1, 9.2, 9.3, 9.4
"""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from layout_visualizer.__main__ import main, parse_args

LAYOUT_ROOT = Path("modules/pfs-chronicle-generator/assets/layouts")
LAYOUT_ID = "pfs.b13"
REAL_PDF = Path(
    "modules/pfs-chronicle-generator/assets/chronicles"
    "/pfs/Bounties/B13-TheBlackwoodAbundanceChronicle.pdf"
)


def _base_args(
    layout_root: str = str(LAYOUT_ROOT),
    layout_id: str = LAYOUT_ID,
    pdf: str = str(REAL_PDF),
) -> list[str]:
    """Build a base argument list with the required flags."""
    return [
        "--layout-root", layout_root,
        "--layout-id", layout_id,
        pdf,
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
            main(["--layout-id", "x", "some.pdf"])
        assert exc_info.value.code == 2

    def test_missing_layout_id_exits_non_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--layout-root", "dir", "some.pdf"])
        assert exc_info.value.code == 2

    def test_missing_pdf_exits_non_zero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--layout-root", "dir", "--layout-id", "x"])
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


class TestMissingPdfFile:
    """A non-existent PDF file produces an error and exit code 1."""

    def test_missing_pdf_returns_one(self, capsys):
        code = main(_base_args(pdf="nonexistent.pdf"))
        assert code == 1

    def test_missing_pdf_prints_error(self, capsys):
        main(_base_args(pdf="nonexistent.pdf"))
        captured = capsys.readouterr()
        assert "nonexistent.pdf" in captured.err


class TestUnknownLayoutId:
    """A layout id not found in the index produces an error and exit code 1."""

    def test_unknown_id_returns_one(self, capsys):
        code = main(_base_args(layout_id="does.not.exist"))
        assert code == 1

    def test_unknown_id_prints_error(self, capsys):
        main(_base_args(layout_id="does.not.exist"))
        captured = capsys.readouterr()
        assert "does.not.exist" in captured.err


# ---------------------------------------------------------------------------
# Default output path
# ---------------------------------------------------------------------------


class TestDefaultOutputPath:
    """When no output path is given, the default is <layout_id>.png."""

    def test_default_output_has_png_extension(self):
        args = parse_args([
            "--layout-root", "dir",
            "--layout-id", "pfs2.season7",
            "some.pdf",
        ])
        assert args.output == Path("pfs2.season7.png")

    def test_explicit_output_overrides_default(self):
        args = parse_args([
            "--layout-root", "dir",
            "--layout-id", "pfs2.season7",
            "some.pdf",
            "custom/out.png",
        ])
        assert args.output == Path("custom/out.png")


# ---------------------------------------------------------------------------
# Successful end-to-end run
# ---------------------------------------------------------------------------


class TestSuccessfulRun:
    """End-to-end test with real layout and PDF files."""

    def test_produces_png_file(self, tmp_path):
        output_png = tmp_path / "output.png"
        args = _base_args() + [str(output_png)]
        code = main(args)

        assert code == 0
        assert output_png.exists()
        assert output_png.stat().st_size > 0


# ---------------------------------------------------------------------------
# Property test for default output path derivation
# Feature: layout-visualizer, Property 1: Default output path derivation
# ---------------------------------------------------------------------------

_layout_id_segment = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="_-.",
    ),
    min_size=1,
    max_size=30,
).filter(lambda s: not s.startswith("-"))


class TestDefaultOutputPathProperty:
    """Validates: Requirements 1.4

    Feature: layout-visualizer, Property 1: Default output path derivation
    """

    @given(layout_id=_layout_id_segment)
    @settings(max_examples=100)
    def test_default_output_is_layout_id_with_png_extension(
        self,
        layout_id: str,
    ) -> None:
        """For any layout id, when no output is provided, the default
        output path is ``<layout_id>.png`` in the current directory.

        Feature: layout-visualizer, Property 1: Default output path derivation
        """
        args = parse_args([
            "--layout-root", "dir",
            "--layout-id", layout_id,
            "dummy.pdf",
        ])

        assert args.output == Path(f"{layout_id}.png")
        assert args.output.suffix == ".png"
