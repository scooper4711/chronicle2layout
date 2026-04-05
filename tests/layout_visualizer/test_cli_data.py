"""CLI integration tests for layout_visualizer data mode.

Tests that ``--mode data`` is accepted by the argument parser,
works with ``--watch``, and produces a valid PNG output file
via the full pipeline.

Requirements: layout-data-mode 1.1, 1.2, 1.3, 8.1
"""

from pathlib import Path

from layout_visualizer.__main__ import main, parse_args

LAYOUT_ROOT = Path("modules/pfs-chronicle-generator/assets/layouts")
LAYOUT_ID = "pfs2.b13"


def _base_args(
    layout_root: str = str(LAYOUT_ROOT),
    layout_id: str = LAYOUT_ID,
) -> list[str]:
    """Build a base argument list with the required flags."""
    return [
        "--layout-root", layout_root,
        "--layout-id", layout_id,
    ]


class TestParseArgsDataMode:
    """Argument parser accepts --mode data."""

    def test_mode_data_is_accepted(self):
        args = parse_args(_base_args() + ["--mode", "data"])
        assert args.mode == "data"

    def test_mode_data_with_watch_is_accepted(self):
        args = parse_args(_base_args() + ["--mode", "data", "--watch"])
        assert args.mode == "data"
        assert args.watch is True


class TestDataModeRun:
    """End-to-end data mode run with real layout and PDF files."""

    def test_data_mode_produces_png(self, tmp_path):
        args = _base_args() + [
            "--output-dir", str(tmp_path),
            "--mode", "data",
        ]
        code = main(args)

        assert code == 0
        pngs = list(tmp_path.rglob("*.png"))
        assert len(pngs) == 1
        assert "pfs2.b13" in pngs[0].name
        assert pngs[0].stat().st_size > 0
