"""Unit tests for extended edge value resolution.

Tests secondary axis references on horizontal/vertical lines and grey
boxes, plain line reference backward compatibility, and error cases
for invalid secondary edges and unrecognized patterns.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 12.1, 12.3, 12.5
"""

import pytest

from blueprint2layout.models import (
    DetectionResult,
    GreyBox,
    HorizontalLine,
    VerticalLine,
)
from blueprint2layout.resolver import resolve_edge_value


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def detection_with_all() -> DetectionResult:
    """A DetectionResult with h_thin, h_bar, v_thin, v_bar, and grey_box."""
    return DetectionResult(
        h_thin=[
            HorizontalLine(y=10.0, x=5.0, x2=80.0, thickness_px=2),
            HorizontalLine(y=30.0, x=3.0, x2=97.0, thickness_px=2),
        ],
        h_bar=[
            HorizontalLine(y=20.0, x=1.0, x2=99.0, thickness_px=8),
        ],
        v_thin=[
            VerticalLine(x=15.0, y=4.0, y2=90.0, thickness_px=2),
        ],
        v_bar=[
            VerticalLine(x=85.0, y=6.0, y2=94.0, thickness_px=8),
        ],
        grey_box=[
            GreyBox(x=10.0, y=20.0, x2=60.0, y2=70.0),
        ],
    )


# ---------------------------------------------------------------------------
# Secondary axis references — horizontal lines
# ---------------------------------------------------------------------------


class TestHorizontalSecondaryAxis:
    """Tests for .left and .right on horizontal lines (Req 4.1)."""

    def test_h_thin_left_resolves_to_x(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("h_thin[0].left", detection_with_all, {})
        assert result == 5.0

    def test_h_thin_right_resolves_to_x2(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("h_thin[0].right", detection_with_all, {})
        assert result == 80.0

    def test_h_bar_left_resolves_to_x(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("h_bar[0].left", detection_with_all, {})
        assert result == 1.0

    def test_h_bar_right_resolves_to_x2(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("h_bar[0].right", detection_with_all, {})
        assert result == 99.0

    def test_h_thin_second_element(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("h_thin[1].left", detection_with_all, {})
        assert result == 3.0


# ---------------------------------------------------------------------------
# Secondary axis references — vertical lines
# ---------------------------------------------------------------------------


class TestVerticalSecondaryAxis:
    """Tests for .top and .bottom on vertical lines (Req 4.2)."""

    def test_v_thin_top_resolves_to_y(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("v_thin[0].top", detection_with_all, {})
        assert result == 4.0

    def test_v_thin_bottom_resolves_to_y2(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("v_thin[0].bottom", detection_with_all, {})
        assert result == 90.0

    def test_v_bar_top_resolves_to_y(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("v_bar[0].top", detection_with_all, {})
        assert result == 6.0

    def test_v_bar_bottom_resolves_to_y2(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("v_bar[0].bottom", detection_with_all, {})
        assert result == 94.0


# ---------------------------------------------------------------------------
# Grey box edge references
# ---------------------------------------------------------------------------


class TestGreyBoxEdgeReferences:
    """Tests for all four edges on grey_box (Req 4.5, 12.3)."""

    def test_grey_box_left_resolves_to_x(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("grey_box[0].left", detection_with_all, {})
        assert result == 10.0

    def test_grey_box_right_resolves_to_x2(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("grey_box[0].right", detection_with_all, {})
        assert result == 60.0

    def test_grey_box_top_resolves_to_y(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("grey_box[0].top", detection_with_all, {})
        assert result == 20.0

    def test_grey_box_bottom_resolves_to_y2(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("grey_box[0].bottom", detection_with_all, {})
        assert result == 70.0


# ---------------------------------------------------------------------------
# Plain line references — backward compatibility
# ---------------------------------------------------------------------------


class TestPlainLineReferencesUnchanged:
    """Tests that plain line references still resolve to primary axis (Req 4.3, 12.4)."""

    def test_plain_h_bar_resolves_to_y(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("h_bar[0]", detection_with_all, {})
        assert result == 20.0

    def test_plain_v_thin_resolves_to_x(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("v_thin[0]", detection_with_all, {})
        assert result == 15.0

    def test_plain_h_thin_resolves_to_y(
        self, detection_with_all: DetectionResult,
    ):
        result = resolve_edge_value("h_thin[0]", detection_with_all, {})
        assert result == 10.0


# ---------------------------------------------------------------------------
# Invalid secondary edge names
# ---------------------------------------------------------------------------


class TestInvalidSecondaryEdge:
    """Tests that invalid secondary edges raise descriptive errors (Req 4.4)."""

    def test_h_thin_top_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        with pytest.raises(ValueError, match="Invalid secondary edge '.top' for 'h_thin'"):
            resolve_edge_value("h_thin[0].top", detection_with_all, {})

    def test_h_thin_bottom_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        with pytest.raises(ValueError, match="Invalid secondary edge '.bottom' for 'h_thin'"):
            resolve_edge_value("h_thin[0].bottom", detection_with_all, {})

    def test_v_thin_left_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        with pytest.raises(ValueError, match="Invalid secondary edge '.left' for 'v_thin'"):
            resolve_edge_value("v_thin[0].left", detection_with_all, {})

    def test_v_thin_right_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        with pytest.raises(ValueError, match="Invalid secondary edge '.right' for 'v_thin'"):
            resolve_edge_value("v_thin[0].right", detection_with_all, {})


# ---------------------------------------------------------------------------
# Unrecognized edge value strings
# ---------------------------------------------------------------------------


class TestUnrecognizedEdgeValue:
    """Tests that unrecognized patterns raise descriptive errors (Req 12.5)."""

    def test_totally_invalid_string_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        with pytest.raises(ValueError, match="not a recognized pattern"):
            resolve_edge_value("totally_invalid_string", detection_with_all, {})

    def test_plain_grey_box_reference_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        """Plain grey_box[0] without a secondary edge is not valid."""
        with pytest.raises(ValueError, match="not a recognized pattern"):
            resolve_edge_value("grey_box[0]", detection_with_all, {})


# ---------------------------------------------------------------------------
# Index out of bounds with secondary axis
# ---------------------------------------------------------------------------


class TestSecondaryAxisOutOfBounds:
    """Tests that out-of-bounds indices raise errors on secondary refs."""

    def test_h_thin_out_of_bounds_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        with pytest.raises(ValueError, match="Index 99 out of bounds.*h_thin"):
            resolve_edge_value("h_thin[99].left", detection_with_all, {})

    def test_v_bar_out_of_bounds_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        with pytest.raises(ValueError, match="Index 5 out of bounds.*v_bar"):
            resolve_edge_value("v_bar[5].top", detection_with_all, {})

    def test_grey_box_out_of_bounds_raises_error(
        self, detection_with_all: DetectionResult,
    ):
        with pytest.raises(ValueError, match="Index 3 out of bounds.*grey_box"):
            resolve_edge_value("grey_box[3].left", detection_with_all, {})
