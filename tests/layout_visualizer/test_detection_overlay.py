"""Tests for composable --show overlay collection.

Covers parse_show_value validation, detection rect construction with
blueprint-reference names, color assignment per category, and
end-to-end CLI runs with --show against real assets.
"""

from pathlib import Path

import pytest

from blueprint2layout.models import GreyBox, HorizontalLine, VerticalLine
from layout_visualizer.__main__ import main, parse_args
from layout_visualizer.detection_overlay import (
    DETECTION_COLORS,
    OVERLAY_CATEGORIES,
    _detection_rects,
    collect_overlay_rects,
    parse_show_value,
)

LAYOUT_ROOT = Path("modules/pfs-chronicle-generator/assets/layouts")
LAYOUT_ID = "pfs2.b13"
REAL_CHRONICLE_PDF = Path(
    "modules/pfs-chronicle-generator/assets/chronicles/pfs2/bounties/B13-TheBlackwoodAbundanceChronicle.pdf"
)

_skip_no_pdf = pytest.mark.skipif(
    not REAL_CHRONICLE_PDF.exists(),
    reason="Real chronicle PDF not available",
)


class TestParseShowValue:
    """parse_show_value accepts known categories and rejects unknown ones."""

    def test_single_category(self):
        assert parse_show_value("h_thin") == frozenset({"h_thin"})

    def test_multiple_categories(self):
        result = parse_show_value("h_thin,canvases,fields")
        assert result == frozenset({"h_thin", "canvases", "fields"})

    def test_whitespace_tolerated(self):
        assert parse_show_value(" h_thin , v_bar ") == frozenset({"h_thin", "v_bar"})

    def test_empty_string_yields_empty_set(self):
        assert parse_show_value("") == frozenset()

    def test_all_categories_parse(self):
        value = ",".join(OVERLAY_CATEGORIES)
        assert parse_show_value(value) == frozenset(OVERLAY_CATEGORIES)

    def test_unknown_category_raises(self):
        with pytest.raises(Exception, match="unknown --show category"):
            parse_show_value("h_thin,bogus")

    def test_unknown_lists_choices(self):
        with pytest.raises(Exception, match="h_thin"):
            parse_show_value("bogus")


class TestDetectionRects:
    """Detection elements become PixelRects with blueprint-reference names."""

    def _detection_result(self):
        from blueprint2layout.models import DetectionResult

        return DetectionResult(
            h_thin=[HorizontalLine(y=10.0, x=5.0, x2=90.0, thickness_px=2, y2=10.5)],
            h_bar=[HorizontalLine(y=20.0, x=5.0, x2=90.0, thickness_px=8, y2=21.0)],
            v_thin=[VerticalLine(x=15.0, y=5.0, y2=95.0, thickness_px=2, x2=15.5)],
            grey_box=[GreyBox(x=40.0, y=40.0, x2=60.0, y2=55.0)],
        )

    def test_names_use_blueprint_reference_form(self):
        result = self._detection_result()
        rects = _detection_rects(
            result,
            frozenset(OVERLAY_CATEGORIES),
            1000,
            2000,
        )
        assert "h_thin[0]" in rects
        assert "h_bar[0]" in rects
        assert "v_thin[0]" in rects
        assert "grey_box[0]" in rects

    def test_percentages_convert_to_pixels(self):
        result = self._detection_result()
        rects = _detection_rects(result, frozenset({"h_thin"}), 1000, 2000)
        rect = rects["h_thin[0]"]
        assert rect.x == pytest.approx(50.0)
        assert rect.y == pytest.approx(200.0)
        assert rect.x2 == pytest.approx(900.0)

    def test_unrequested_categories_excluded(self):
        result = self._detection_result()
        rects = _detection_rects(result, frozenset({"v_thin"}), 1000, 2000)
        assert set(rects) == {"v_thin[0]"}

    def test_multiple_elements_get_sequential_indexes(self):
        from blueprint2layout.models import DetectionResult

        detection = DetectionResult(
            h_thin=[
                HorizontalLine(y=1.0, x=0.0, x2=50.0, thickness_px=1, y2=1.5),
                HorizontalLine(y=2.0, x=0.0, x2=50.0, thickness_px=1, y2=2.5),
                HorizontalLine(y=3.0, x=0.0, x2=50.0, thickness_px=1, y2=3.5),
            ],
        )
        rects = _detection_rects(detection, frozenset({"h_thin"}), 100, 100)
        assert set(rects) == {"h_thin[0]", "h_thin[1]", "h_thin[2]"}


class TestDetectionColors:
    """Each detection category gets its dedicated fixed color."""

    @pytest.mark.parametrize("category", list(DETECTION_COLORS))
    def test_every_category_has_a_color(self, category):
        assert category in DETECTION_COLORS
        color = DETECTION_COLORS[category]
        assert len(color) == 3
        assert all(0 <= channel <= 255 for channel in color)

    def test_category_colors_are_distinct(self):
        assert len(set(DETECTION_COLORS.values())) == len(DETECTION_COLORS)


class TestCollectOverlayRects:
    """collect_overlay_rects combines categories and returns matching colors."""

    @_skip_no_pdf
    def test_canvases_only(self):
        from layout_visualizer.layout_loader import build_layout_index

        index = build_layout_index(LAYOUT_ROOT)
        layout_path = index[LAYOUT_ID]
        rects, colors = collect_overlay_rects(
            layout_path,
            index,
            REAL_CHRONICLE_PDF,
            1275,
            1650,
            frozenset({"canvases"}),
        )
        assert rects
        assert set(rects) == set(colors)
        assert all(not name.startswith("h_thin") for name in rects)

    @_skip_no_pdf
    def test_detection_category_produces_indexed_names(self):
        from layout_visualizer.layout_loader import build_layout_index

        index = build_layout_index(LAYOUT_ROOT)
        layout_path = index[LAYOUT_ID]
        rects, colors = collect_overlay_rects(
            layout_path,
            index,
            REAL_CHRONICLE_PDF,
            1275,
            1650,
            frozenset({"h_thin"}),
        )
        assert rects
        assert all(name.startswith("h_thin[") for name in rects)
        assert all(colors[name] == DETECTION_COLORS["h_thin"] for name in rects)

    @_skip_no_pdf
    def test_combined_categories_share_color_map(self):
        from layout_visualizer.layout_loader import build_layout_index

        index = build_layout_index(LAYOUT_ROOT)
        layout_path = index[LAYOUT_ID]
        rects, colors = collect_overlay_rects(
            layout_path,
            index,
            REAL_CHRONICLE_PDF,
            1275,
            1650,
            frozenset({"h_thin", "canvases"}),
        )
        assert set(rects) == set(colors)
        assert any(name.startswith("h_thin[") for name in rects)
        assert any(not "[" in name for name in rects)


class TestShowCli:
    """CLI accepts --show and end-to-end produces a PNG."""

    def test_parse_args_defaults_show_to_none(self):
        args = parse_args(
            [
                "--layout-root",
                "dir",
                "--layout-id",
                "pfs.b13",
            ]
        )
        assert args.show is None

    def test_parse_args_reads_show(self):
        args = parse_args(
            [
                "--layout-root",
                "dir",
                "--layout-id",
                "pfs.b13",
                "--show",
                "h_thin,canvases",
            ]
        )
        assert args.show == frozenset({"h_thin", "canvases"})

    def test_unknown_show_category_exits_two(self):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(
                [
                    "--layout-root",
                    "dir",
                    "--layout-id",
                    "pfs.b13",
                    "--show",
                    "bogus",
                ]
            )
        assert exc_info.value.code == 2

    @_skip_no_pdf
    def test_show_end_to_end_writes_png(self, tmp_path):
        code = main(
            [
                "--layout-root",
                str(LAYOUT_ROOT),
                "--layout-id",
                LAYOUT_ID,
                "--output-dir",
                str(tmp_path),
                "--show",
                "h_thin,canvases",
            ]
        )
        assert code == 0
        pngs = list(tmp_path.rglob("*.png"))
        assert len(pngs) == 1
        assert pngs[0].stat().st_size > 0

    @_skip_no_pdf
    def test_show_empty_set_still_writes_png(self, tmp_path):
        code = main(
            [
                "--layout-root",
                str(LAYOUT_ROOT),
                "--layout-id",
                LAYOUT_ID,
                "--output-dir",
                str(tmp_path),
                "--show",
                "",
            ]
        )
        assert code == 0
        assert list(tmp_path.rglob("*.png"))
