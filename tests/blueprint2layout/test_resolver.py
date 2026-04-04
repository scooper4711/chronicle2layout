"""Unit tests for edge value resolution.

Tests resolve_edge_value with numeric, line reference, and canvas reference
inputs, plus error cases. Tests resolve_canvases with inherited and target
canvases, verifying backward-only reference enforcement.

Requirements: 9.1–9.6, 10.1–10.4
"""

import pytest

from blueprint2layout.models import (
    CanvasEntry,
    DetectionResult,
    HorizontalLine,
    ResolvedCanvas,
    VerticalLine,
)
from blueprint2layout.resolver import resolve_canvases, resolve_edge_value


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def empty_detection() -> DetectionResult:
    """A DetectionResult with no detected elements."""
    return DetectionResult()


@pytest.fixture()
def detection_with_h_bar() -> DetectionResult:
    """A DetectionResult with two h_bar entries."""
    return DetectionResult(
        h_bar=[
            HorizontalLine(y=10.0, x=2.0, x2=98.0, thickness_px=8),
            HorizontalLine(y=50.0, x=2.0, x2=98.0, thickness_px=8),
        ],
    )


@pytest.fixture()
def detection_with_v_thin() -> DetectionResult:
    """A DetectionResult with one v_thin entry."""
    return DetectionResult(
        v_thin=[
            VerticalLine(x=25.0, y=5.0, y2=95.0, thickness_px=2),
        ],
    )


@pytest.fixture()
def detection_with_lines() -> DetectionResult:
    """A DetectionResult with h_bar, h_thin, and v_thin entries for resolve_canvases tests."""
    return DetectionResult(
        h_bar=[
            HorizontalLine(y=5.0, x=1.0, x2=99.0, thickness_px=8),
            HorizontalLine(y=30.0, x=1.0, x2=99.0, thickness_px=8),
            HorizontalLine(y=60.0, x=1.0, x2=99.0, thickness_px=8),
        ],
        h_thin=[
            HorizontalLine(y=15.0, x=3.0, x2=97.0, thickness_px=2),
        ],
        v_thin=[
            VerticalLine(x=10.0, y=5.0, y2=95.0, thickness_px=2),
            VerticalLine(x=90.0, y=5.0, y2=95.0, thickness_px=2),
        ],
    )


@pytest.fixture()
def page_canvas() -> ResolvedCanvas:
    """A resolved 'page' canvas spanning the full page."""
    return ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0)


# ---------------------------------------------------------------------------
# resolve_edge_value tests
# ---------------------------------------------------------------------------

class TestResolveEdgeValueNumeric:
    """Tests for numeric literal edge values (Requirement 9.1)."""

    def test_numeric_int_returns_float(self, empty_detection: DetectionResult):
        result = resolve_edge_value(42, empty_detection, {})
        assert result == 42.0
        assert isinstance(result, float)

    def test_numeric_float_returns_float(self, empty_detection: DetectionResult):
        result = resolve_edge_value(3.14, empty_detection, {})
        assert result == 3.14
        assert isinstance(result, float)


class TestResolveEdgeValueLineReference:
    """Tests for line reference edge values (Requirement 9.2)."""

    def test_line_reference_horizontal(self, detection_with_h_bar: DetectionResult):
        result = resolve_edge_value("h_bar[0]", detection_with_h_bar, {})
        assert result == 10.0

    def test_line_reference_vertical(self, detection_with_v_thin: DetectionResult):
        result = resolve_edge_value("v_thin[0]", detection_with_v_thin, {})
        assert result == 25.0


class TestResolveEdgeValueCanvasReference:
    """Tests for canvas reference edge values (Requirement 9.3)."""

    def test_canvas_reference(self, empty_detection: DetectionResult, page_canvas: ResolvedCanvas):
        resolved = {"page": page_canvas}
        result = resolve_edge_value("page.left", empty_detection, resolved)
        assert result == 0.0


class TestResolveEdgeValueErrors:
    """Tests for error cases (Requirements 9.4, 9.5, 9.6)."""

    def test_unknown_category_raises_error(self, empty_detection: DetectionResult):
        with pytest.raises(ValueError, match="not a recognized pattern"):
            resolve_edge_value("unknown[0]", empty_detection, {})

    def test_out_of_bounds_index_raises_error(self, detection_with_h_bar: DetectionResult):
        with pytest.raises(ValueError, match="Index 99 out of bounds.*h_bar"):
            resolve_edge_value("h_bar[99]", detection_with_h_bar, {})

    def test_forward_reference_raises_error(self, empty_detection: DetectionResult):
        with pytest.raises(ValueError, match="has not been resolved yet"):
            resolve_edge_value("future.left", empty_detection, {})

    def test_grey_box_plain_reference_raises_error(self, empty_detection: DetectionResult):
        """Plain grey_box[0] is not valid — grey_box requires a secondary edge."""
        with pytest.raises(ValueError, match="not a recognized pattern"):
            resolve_edge_value("grey_box[0]", empty_detection, {})


# ---------------------------------------------------------------------------
# resolve_canvases tests
# ---------------------------------------------------------------------------

class TestResolveCanvasesNumericEdges:
    """Tests for resolve_canvases with all-numeric edges (Requirement 10.1, 10.4)."""

    def test_resolve_canvases_with_numeric_edges(self, empty_detection: DetectionResult):
        canvases = [
            CanvasEntry(name="page", left=0, right=100, top=0, bottom=100),
            CanvasEntry(name="main", left=5, right=95, top=10, bottom=90, parent="page"),
        ]
        result = resolve_canvases([], canvases, empty_detection)

        assert len(result) == 2
        assert result["page"] == ResolvedCanvas(
            name="page", left=0.0, right=100.0, top=0.0, bottom=100.0,
        )
        assert result["main"] == ResolvedCanvas(
            name="main", left=5.0, right=95.0, top=10.0, bottom=90.0, parent="page",
        )


class TestResolveCanvasesLineReferences:
    """Tests for resolve_canvases with line references (Requirement 10.1)."""

    def test_resolve_canvases_with_line_references(self, detection_with_lines: DetectionResult):
        canvases = [
            CanvasEntry(
                name="header",
                left="v_thin[0]",
                right="v_thin[1]",
                top="h_bar[0]",
                bottom="h_bar[1]",
            ),
        ]
        result = resolve_canvases([], canvases, detection_with_lines)

        assert result["header"].left == 10.0
        assert result["header"].right == 90.0
        assert result["header"].top == 5.0
        assert result["header"].bottom == 30.0


class TestResolveCanvasesCanvasReferences:
    """Tests for resolve_canvases with backward canvas references (Requirement 10.2)."""

    def test_resolve_canvases_with_canvas_references(self, empty_detection: DetectionResult):
        canvases = [
            CanvasEntry(name="page", left=0, right=100, top=0, bottom=100),
            CanvasEntry(
                name="inner",
                left="page.left",
                right="page.right",
                top="page.top",
                bottom="page.bottom",
                parent="page",
            ),
        ]
        result = resolve_canvases([], canvases, empty_detection)

        assert result["inner"].left == 0.0
        assert result["inner"].right == 100.0
        assert result["inner"].top == 0.0
        assert result["inner"].bottom == 100.0


class TestResolveCanvasesForwardReference:
    """Tests for forward reference enforcement (Requirement 10.3)."""

    def test_resolve_canvases_forward_reference_raises_error(self, empty_detection: DetectionResult):
        canvases = [
            CanvasEntry(
                name="first",
                left="second.left",
                right=100,
                top=0,
                bottom=100,
            ),
            CanvasEntry(name="second", left=10, right=90, top=10, bottom=90),
        ]
        with pytest.raises(ValueError, match="has not been resolved yet"):
            resolve_canvases([], canvases, empty_detection)


class TestResolveCanvasesInheritedThenTarget:
    """Tests for inherited-first resolution order (Requirements 10.1, 10.2)."""

    def test_resolve_canvases_inherited_then_target(self, empty_detection: DetectionResult):
        inherited = [
            CanvasEntry(name="page", left=0, right=100, top=0, bottom=100),
            CanvasEntry(name="main", left=5, right=95, top=5, bottom=95, parent="page"),
        ]
        target = [
            CanvasEntry(
                name="summary",
                left="main.left",
                right="main.right",
                top="main.top",
                bottom=50,
                parent="main",
            ),
        ]
        result = resolve_canvases(inherited, target, empty_detection)

        assert len(result) == 3
        # Inherited canvases resolved first
        assert result["page"].left == 0.0
        assert result["main"].left == 5.0
        # Target canvas references inherited canvases
        assert result["summary"].left == 5.0
        assert result["summary"].right == 95.0
        assert result["summary"].top == 5.0
        assert result["summary"].bottom == 50.0
        assert result["summary"].parent == "main"
