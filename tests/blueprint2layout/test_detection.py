"""Unit tests for detection module.

Validates Requirements: 2.1–2.6, 3.1–3.6, 4.1–4.5, 5.1–5.7, 6.1–6.6
"""

import numpy as np
import pytest

from blueprint2layout.detection import (
    detect_horizontal_black_lines,
    detect_vertical_black_lines,
    detect_grey_rules,
    detect_grey_boxes,
    detect_structures,
)


def _white_image(height: int, width: int) -> np.ndarray:
    """Create an all-white grayscale image."""
    return np.full((height, width), 255, dtype=np.uint8)


class TestDetectSingleThinHorizontalLine:
    """A 3px thick black line should be classified as h_thin."""

    def test_detect_single_thin_horizontal_line(self) -> None:
        """Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6"""
        image = _white_image(100, 200)
        image[49:52, :] = 0  # 3px thick line at rows 49-51

        h_thin, h_bar = detect_horizontal_black_lines(image)

        assert len(h_thin) == 1
        assert len(h_bar) == 0

        line = h_thin[0]
        assert line.thickness_px == 3
        assert line.y == pytest.approx(49.0, abs=0.5)
        assert line.x == pytest.approx(0.0, abs=0.5)
        assert line.x2 == pytest.approx(99.5, abs=1.0)


class TestDetectSingleBarHorizontalLine:
    """A 10px thick black line should be classified as h_bar."""

    def test_detect_single_bar_horizontal_line(self) -> None:
        """Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6"""
        image = _white_image(100, 200)
        image[30:40, :] = 0  # 10px thick line at rows 30-39

        h_thin, h_bar = detect_horizontal_black_lines(image)

        assert len(h_thin) == 0
        assert len(h_bar) == 1

        line = h_bar[0]
        assert line.thickness_px == 10
        assert line.y == pytest.approx(30.0, abs=0.5)


class TestDetectMultipleLinesSortedByY:
    """Multiple thin lines should be sorted by y ascending."""

    def test_detect_multiple_lines_sorted_by_y(self) -> None:
        """Validates: Requirements 2.2, 2.5"""
        image = _white_image(100, 200)
        image[78:81, :] = 0  # 3px line at row 78 (lower)
        image[18:21, :] = 0  # 3px line at row 18 (upper)

        h_thin, h_bar = detect_horizontal_black_lines(image)

        assert len(h_thin) == 2
        assert len(h_bar) == 0
        assert h_thin[0].y < h_thin[1].y  # row 18 first, row 78 second


class TestDetectMixedThinAndBar:
    """A thin line and a bar should go to their respective lists."""

    def test_detect_mixed_thin_and_bar(self) -> None:
        """Validates: Requirements 2.4, 2.5"""
        image = _white_image(200, 200)
        image[30:33, :] = 0   # 3px thin line
        image[100:110, :] = 0  # 10px bar

        h_thin, h_bar = detect_horizontal_black_lines(image)

        assert len(h_thin) == 1
        assert len(h_bar) == 1
        assert h_thin[0].thickness_px == 3
        assert h_bar[0].thickness_px == 10


class TestNoLinesDetectedOnBlankImage:
    """An all-white image should produce empty lists."""

    def test_no_lines_detected_on_blank_image(self) -> None:
        """Validates: Requirements 2.1"""
        image = _white_image(100, 200)

        h_thin, h_bar = detect_horizontal_black_lines(image)

        assert h_thin == []
        assert h_bar == []


class TestShortRunNotDetected:
    """A black line shorter than 5% of page width should not be detected."""

    def test_short_run_not_detected(self) -> None:
        """Validates: Requirements 2.1"""
        image = _white_image(100, 200)
        # 2% of 200px = 4px, well below the 5% threshold (10px)
        image[50, 0:4] = 0

        h_thin, h_bar = detect_horizontal_black_lines(image)

        assert h_thin == []
        assert h_bar == []


class TestPercentageCoordinatesCorrect:
    """Percentage coordinates should be computed from pixel positions."""

    def test_percentage_coordinates_correct(self) -> None:
        """Validates: Requirements 2.3, 2.6"""
        image = _white_image(1000, 2000)
        # 3px line at row 500, from column 100 to column 1899
        image[499:502, 100:1900] = 0

        h_thin, _ = detect_horizontal_black_lines(image)

        assert len(h_thin) == 1
        line = h_thin[0]

        # Expected: row 499 / 1000 height gives ~49.9%
        assert line.y == pytest.approx(49.9, abs=0.2)
        # Expected: col 100 / 2000 width gives 5.0%
        assert line.x == pytest.approx(5.0, abs=0.2)
        # Expected: col 1899 / 2000 width gives ~95.0%
        assert line.x2 == pytest.approx(95.0, abs=0.5)
        assert line.thickness_px == 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _white_grayscale(height: int, width: int) -> np.ndarray:
    """Create an all-white grayscale image."""
    return np.full((height, width), 255, dtype=np.uint8)


def _white_rgb(height: int, width: int) -> np.ndarray:
    """Create an all-white RGB image."""
    return np.full((height, width, 3), 255, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Vertical black line detection tests (Requirements 3.1–3.6)
# ---------------------------------------------------------------------------


class TestDetectSingleThinVerticalLine:
    """A 3px wide black column should be classified as v_thin."""

    def test_single_thin_vertical_line(self) -> None:
        """Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6"""
        image = _white_grayscale(100, 200)
        image[:, 49:52] = 0  # 3px wide column at cols 49-51

        v_thin, v_bar = detect_vertical_black_lines(image)

        assert len(v_thin) == 1
        assert len(v_bar) == 0

        line = v_thin[0]
        assert line.thickness_px == 3
        # x = 49 / 200 * 100 = 24.5%
        assert line.x == pytest.approx(24.5, abs=0.5)
        # y should start near 0%, y2 near 99%
        assert line.y == pytest.approx(0.0, abs=0.5)
        assert line.y2 == pytest.approx(99.0, abs=1.0)


class TestDetectSingleBarVerticalLine:
    """A 10px wide black column should be classified as v_bar."""

    def test_single_bar_vertical_line(self) -> None:
        """Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6"""
        image = _white_grayscale(100, 200)
        image[:, 30:40] = 0  # 10px wide column at cols 30-39

        v_thin, v_bar = detect_vertical_black_lines(image)

        assert len(v_thin) == 0
        assert len(v_bar) == 1

        line = v_bar[0]
        assert line.thickness_px == 10
        # x = 30 / 200 * 100 = 15.0%
        assert line.x == pytest.approx(15.0, abs=0.5)


class TestDetectMultipleVerticalLinesSortedByX:
    """Multiple thin vertical lines should be sorted by x ascending."""

    def test_multiple_vertical_lines_sorted_by_x(self) -> None:
        """Validates: Requirements 3.2, 3.5"""
        image = _white_grayscale(100, 200)
        image[:, 150:153] = 0  # 3px line at col 150 (rightward)
        image[:, 30:33] = 0   # 3px line at col 30 (leftward)

        v_thin, v_bar = detect_vertical_black_lines(image)

        assert len(v_thin) == 2
        assert len(v_bar) == 0
        assert v_thin[0].x < v_thin[1].x  # col 30 first, col 150 second


class TestNoVerticalLinesOnBlankImage:
    """An all-white image should produce empty vertical line lists."""

    def test_no_vertical_lines_on_blank_image(self) -> None:
        """Validates: Requirements 3.1"""
        image = _white_grayscale(100, 200)

        v_thin, v_bar = detect_vertical_black_lines(image)

        assert v_thin == []
        assert v_bar == []


# ---------------------------------------------------------------------------
# Grey rule detection tests (Requirements 4.1–4.5)
# ---------------------------------------------------------------------------


class TestDetectGreyRules:
    """A grey line (value 120) should be detected as a grey rule."""

    def test_detect_grey_rule(self) -> None:
        """Validates: Requirements 4.1, 4.2, 4.3, 4.5"""
        image = _white_grayscale(200, 100)
        image[50, :] = 120  # single-row grey line at row 50

        h_thin: list = []
        h_bar: list = []

        rules = detect_grey_rules(image, h_thin, h_bar)

        assert len(rules) == 1
        rule = rules[0]
        # y = 50 / 200 * 100 = 25.0%
        assert rule.y == pytest.approx(25.0, abs=0.5)


class TestGreyRuleDeduplication:
    """A grey line at the same y as a black line should be discarded."""

    def test_grey_rule_deduplicated_near_black_line(self) -> None:
        """Validates: Requirements 4.4"""
        from blueprint2layout.models import HorizontalLine

        image = _white_grayscale(200, 100)
        # Draw a grey line at row 50
        image[50, :] = 120

        # Simulate a black line at y = 25.0% (row 50 / 200 = 25.0%)
        black_line = HorizontalLine(y=25.0, x=0.0, x2=100.0, thickness_px=3)
        h_thin = [black_line]
        h_bar: list = []

        rules = detect_grey_rules(image, h_thin, h_bar)

        assert len(rules) == 0


class TestGreyRuleNotDeduplicatedWhenFarFromBlack:
    """A grey line far from any black line should be kept."""

    def test_grey_rule_kept_when_far_from_black(self) -> None:
        """Validates: Requirements 4.4, 4.5"""
        from blueprint2layout.models import HorizontalLine

        image = _white_grayscale(200, 100)
        # Draw a grey line at row 50 → y = 25.0%
        image[50, :] = 120

        # Black line at y = 80.0% — far away from 25.0%
        black_line = HorizontalLine(y=80.0, x=0.0, x2=100.0, thickness_px=3)
        h_thin = [black_line]
        h_bar: list = []

        rules = detect_grey_rules(image, h_thin, h_bar)

        assert len(rules) == 1
        assert rules[0].y == pytest.approx(25.0, abs=0.5)


# ---------------------------------------------------------------------------
# Grey box detection tests (Requirements 5.1–5.7)
# ---------------------------------------------------------------------------


class TestDetectGreyBox:
    """A 50x50 grey rectangle should be detected as a grey box."""

    def test_detect_grey_box(self) -> None:
        """Validates: Requirements 5.1, 5.2, 5.3, 5.5, 5.6, 5.7"""
        image = _white_rgb(200, 200)
        # Draw a 50x50 grey rectangle (value 230) at position (50, 50)
        image[50:100, 50:100] = 230

        boxes = detect_grey_boxes(image)

        assert len(boxes) == 1
        box = boxes[0]
        # x = 50 / 200 * 100 = 25.0%
        assert box.x == pytest.approx(25.0, abs=1.0)
        # y = 50 / 200 * 100 = 25.0%
        assert box.y == pytest.approx(25.0, abs=1.0)
        # x2 = 99 / 200 * 100 ≈ 49.5%
        assert box.x2 == pytest.approx(49.5, abs=1.5)
        # y2 = 99 / 200 * 100 ≈ 49.5%
        assert box.y2 == pytest.approx(49.5, abs=1.5)


class TestSmallGreyBoxDiscarded:
    """A tiny grey rectangle (5x5 pixels) should be discarded."""

    def test_small_grey_box_discarded(self) -> None:
        """Validates: Requirements 5.4, 5.6"""
        image = _white_rgb(200, 200)
        # 5x5 = 25 px² area, well below GREY_BOX_MIN_AREA (500)
        # Also only covers part of one 10x10 block, so < 3 blocks
        image[10:15, 10:15] = 230

        boxes = detect_grey_boxes(image)

        assert len(boxes) == 0


class TestNoGreyBoxesOnWhiteImage:
    """An all-white RGB image should produce no grey boxes."""

    def test_no_grey_boxes_on_white_image(self) -> None:
        """Validates: Requirements 5.1"""
        image = _white_rgb(200, 200)

        boxes = detect_grey_boxes(image)

        assert len(boxes) == 0


# ---------------------------------------------------------------------------
# detect_structures orchestrator test (Requirements 6.1–6.6)
# ---------------------------------------------------------------------------


class TestDetectStructures:
    """detect_structures should assemble all six arrays correctly."""

    def test_detect_structures_assembles_all_arrays(self) -> None:
        """Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6"""
        height, width = 200, 200
        grayscale = _white_grayscale(height, width)
        rgb = _white_rgb(height, width)

        # Draw a horizontal thin line (3px) at rows 20-22
        grayscale[20:23, :] = 0

        # Draw a vertical thin line (3px) at cols 80-82
        grayscale[:, 80:83] = 0

        # Draw a 50x50 grey box at (120, 120)
        rgb[120:170, 120:170] = 230

        result = detect_structures(grayscale, rgb)

        # Verify all six arrays exist
        assert hasattr(result, "h_thin")
        assert hasattr(result, "h_bar")
        assert hasattr(result, "h_rule")
        assert hasattr(result, "v_thin")
        assert hasattr(result, "v_bar")
        assert hasattr(result, "grey_box")

        # We drew a thin horizontal line
        assert len(result.h_thin) >= 1
        assert result.h_thin[0].y == pytest.approx(10.0, abs=1.0)

        # We drew a thin vertical line
        assert len(result.v_thin) >= 1
        assert result.v_thin[0].x == pytest.approx(40.0, abs=1.0)

        # We drew a grey box
        assert len(result.grey_box) >= 1
        assert result.grey_box[0].y == pytest.approx(60.0, abs=2.0)

        # h_bar, h_rule, v_bar may be empty (we didn't draw those)
        assert isinstance(result.h_bar, list)
        assert isinstance(result.h_rule, list)
        assert isinstance(result.v_bar, list)
