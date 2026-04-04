"""Unit tests for field resolver style composition.

Tests resolve_field_styles: single style, chained styles, direct
property override, circular reference detection, and undefined
style reference errors.

Requirements: 6.3, 6.4, 6.5, 6.6, 6.7, 6.9
"""

import pytest

from blueprint2layout.field_resolver import resolve_field_styles
from blueprint2layout.models import FieldEntry


# ---------------------------------------------------------------------------
# Single style resolution
# ---------------------------------------------------------------------------


class TestSingleStyleResolution:
    """Tests that a field inherits properties from a single style."""

    def test_inherits_font_properties(self):
        field = FieldEntry(name="f1", styles=["base"])
        styles = {"base": {"font": "Helvetica", "fontsize": 14}}

        result = resolve_field_styles(field, styles)

        assert result["font"] == "Helvetica"
        assert result["fontsize"] == 14

    def test_inherits_canvas_and_type(self):
        field = FieldEntry(name="f1", styles=["base"])
        styles = {"base": {"canvas": "main", "type": "text"}}

        result = resolve_field_styles(field, styles)

        assert result["canvas"] == "main"
        assert result["type"] == "text"

    def test_inherits_all_style_properties(self):
        field = FieldEntry(name="f1", styles=["full"])
        styles = {
            "full": {
                "canvas": "main",
                "type": "text",
                "font": "Helvetica",
                "fontsize": 12,
                "fontweight": "bold",
                "align": "CM",
                "color": "black",
                "linewidth": 0.5,
                "size": 10,
                "lines": 3,
                "left": 0,
                "right": 100,
                "top": 0,
                "bottom": 50,
            },
        }

        result = resolve_field_styles(field, styles)

        assert len(result) == 14

    def test_no_styles_returns_only_direct_properties(self):
        field = FieldEntry(name="f1", font="Arial", fontsize=10)

        result = resolve_field_styles(field, {})

        assert result == {"font": "Arial", "fontsize": 10}


# ---------------------------------------------------------------------------
# Chained style resolution
# ---------------------------------------------------------------------------


class TestChainedStyleResolution:
    """Tests that styles referencing other styles resolve depth-first."""

    def test_base_style_resolved_first(self):
        field = FieldEntry(name="f1", styles=["rightbar_field"])
        styles = {
            "defaultfont": {"font": "Helvetica", "fontsize": 14},
            "rightbar_field": {
                "styles": ["defaultfont"],
                "canvas": "rightbar",
                "align": "CM",
            },
        }

        result = resolve_field_styles(field, styles)

        assert result["font"] == "Helvetica"
        assert result["fontsize"] == 14
        assert result["canvas"] == "rightbar"
        assert result["align"] == "CM"

    def test_deeper_chain_resolves_correctly(self):
        field = FieldEntry(name="f1", styles=["specific"])
        styles = {
            "base": {"font": "Helvetica", "fontsize": 10, "align": "LB"},
            "mid": {"styles": ["base"], "fontsize": 12, "canvas": "main"},
            "specific": {"styles": ["mid"], "fontsize": 14},
        }

        result = resolve_field_styles(field, styles)

        assert result["font"] == "Helvetica"
        assert result["fontsize"] == 14
        assert result["canvas"] == "main"
        assert result["align"] == "LB"

    def test_later_style_overrides_earlier(self):
        field = FieldEntry(name="f1", styles=["style_a", "style_b"])
        styles = {
            "style_a": {"font": "Arial", "fontsize": 10},
            "style_b": {"font": "Helvetica"},
        }

        result = resolve_field_styles(field, styles)

        assert result["font"] == "Helvetica"
        assert result["fontsize"] == 10


# ---------------------------------------------------------------------------
# Direct property override
# ---------------------------------------------------------------------------


class TestDirectPropertyOverride:
    """Tests that field direct properties override style properties."""

    def test_direct_overrides_style(self):
        field = FieldEntry(
            name="f1",
            styles=["base"],
            font="Courier",
            fontweight="bold",
        )
        styles = {"base": {"font": "Helvetica", "fontsize": 14}}

        result = resolve_field_styles(field, styles)

        assert result["font"] == "Courier"
        assert result["fontsize"] == 14
        assert result["fontweight"] == "bold"

    def test_direct_overrides_chained_style(self):
        field = FieldEntry(
            name="f1",
            styles=["specific"],
            align="LB",
        )
        styles = {
            "base": {"align": "CM", "font": "Helvetica"},
            "specific": {"styles": ["base"], "align": "RT"},
        }

        result = resolve_field_styles(field, styles)

        assert result["align"] == "LB"
        assert result["font"] == "Helvetica"


# ---------------------------------------------------------------------------
# None values are skipped
# ---------------------------------------------------------------------------


class TestNoneValuesSkipped:
    """Tests that None values on the field entry do not override styles."""

    def test_none_field_property_does_not_override(self):
        field = FieldEntry(name="f1", styles=["base"], font=None)
        styles = {"base": {"font": "Helvetica"}}

        result = resolve_field_styles(field, styles)

        assert result["font"] == "Helvetica"

    def test_none_style_property_is_skipped(self):
        field = FieldEntry(name="f1", styles=["base"])
        styles = {"base": {"font": "Helvetica", "fontsize": None}}

        result = resolve_field_styles(field, styles)

        assert result["font"] == "Helvetica"
        assert "fontsize" not in result


# ---------------------------------------------------------------------------
# Undefined style reference
# ---------------------------------------------------------------------------


class TestUndefinedStyleReference:
    """Tests that referencing an undefined style raises ValueError."""

    def test_field_references_undefined_style(self):
        field = FieldEntry(name="myfield", styles=["nonexistent"])

        with pytest.raises(ValueError, match="undefined style 'nonexistent'"):
            resolve_field_styles(field, {})

    def test_style_chain_references_undefined_base(self):
        field = FieldEntry(name="myfield", styles=["child_style"])
        styles = {"child_style": {"styles": ["missing_base"], "font": "Arial"}}

        with pytest.raises(ValueError, match="undefined style 'missing_base'"):
            resolve_field_styles(field, styles)


# ---------------------------------------------------------------------------
# Circular style reference
# ---------------------------------------------------------------------------


class TestCircularStyleReference:
    """Tests that circular style references raise ValueError."""

    def test_self_referencing_style(self):
        field = FieldEntry(name="myfield", styles=["loop"])
        styles = {"loop": {"styles": ["loop"], "font": "Arial"}}

        with pytest.raises(ValueError, match="Circular style reference.*'loop'"):
            resolve_field_styles(field, styles)

    def test_indirect_circular_reference(self):
        field = FieldEntry(name="myfield", styles=["a"])
        styles = {
            "a": {"styles": ["b"]},
            "b": {"styles": ["c"]},
            "c": {"styles": ["a"]},
        }

        with pytest.raises(ValueError, match="Circular style reference.*'a'"):
            resolve_field_styles(field, styles)

    def test_mutual_circular_reference(self):
        field = FieldEntry(name="myfield", styles=["x"])
        styles = {
            "x": {"styles": ["y"]},
            "y": {"styles": ["x"]},
        }

        with pytest.raises(ValueError, match="Circular style reference.*'x'"):
            resolve_field_styles(field, styles)


# ---------------------------------------------------------------------------
# Empty styles list
# ---------------------------------------------------------------------------


class TestEmptyStylesList:
    """Tests edge cases with empty styles."""

    def test_no_styles_no_direct_properties(self):
        field = FieldEntry(name="f1")

        result = resolve_field_styles(field, {})

        assert result == {}

    def test_style_with_empty_styles_list(self):
        field = FieldEntry(name="f1", styles=["base"])
        styles = {"base": {"styles": [], "font": "Helvetica"}}

        result = resolve_field_styles(field, styles)

        assert result == {"font": "Helvetica"}


# ---------------------------------------------------------------------------
# Non-style properties are ignored
# ---------------------------------------------------------------------------


class TestNonStylePropertiesIgnored:
    """Tests that properties not in STYLE_PROPERTIES are not inherited."""

    def test_extra_properties_in_style_are_ignored(self):
        field = FieldEntry(name="f1", styles=["base"])
        styles = {
            "base": {"font": "Helvetica", "trigger": "some_param", "unknown": 42},
        }

        result = resolve_field_styles(field, styles)

        assert result == {"font": "Helvetica"}
        assert "trigger" not in result
        assert "unknown" not in result


# ---------------------------------------------------------------------------
# resolve_field_edge tests
# ---------------------------------------------------------------------------

from blueprint2layout.field_resolver import (
    compute_top_default,
    resolve_field_edge,
    resolve_fields,
)
from blueprint2layout.models import (
    DetectionResult,
    HorizontalLine,
    ResolvedCanvas,
    ResolvedField,
    VerticalLine,
)


def _make_detection(**kwargs) -> DetectionResult:
    """Create a DetectionResult with specified line arrays."""
    return DetectionResult(**kwargs)


def _make_canvases() -> dict[str, ResolvedCanvas]:
    """Create a minimal set of resolved canvases for testing."""
    return {
        "page": ResolvedCanvas(
            name="page", left=0.0, right=100.0, top=0.0, bottom=100.0,
        ),
        "main": ResolvedCanvas(
            name="main", left=10.0, right=90.0, top=5.0, bottom=95.0,
            parent="page",
        ),
    }


class TestResolveFieldEdgeNumeric:
    """Tests that numeric edge values pass through correctly."""

    def test_integer_value(self):
        result = resolve_field_edge(
            42, "left", None, "603:783",
            _make_detection(), _make_canvases(),
        )
        assert result == 42.0

    def test_float_value(self):
        result = resolve_field_edge(
            12.5, "top", None, "603:783",
            _make_detection(), _make_canvases(),
        )
        assert result == 12.5


class TestResolveFieldEdgeLineReference:
    """Tests that line references delegate to resolve_edge_value."""

    def test_horizontal_line_reference(self):
        detection = _make_detection(
            h_thin=[HorizontalLine(y=25.0, x=5.0, x2=95.0, thickness_px=2)],
        )
        result = resolve_field_edge(
            "h_thin[0]", "bottom", None, "603:783",
            detection, _make_canvases(),
        )
        assert result == 25.0

    def test_canvas_reference(self):
        result = resolve_field_edge(
            "main.left", "left", None, "603:783",
            _make_detection(), _make_canvases(),
        )
        assert result == 10.0


class TestResolveFieldEdgeEmOffset:
    """Tests em offset expression parsing and computation."""

    def test_subtract_em_on_vertical_edge(self):
        # "h_thin[0] - 1em" with fontsize=14, height=783
        # base=25.0, offset=14/783*100=1.7880..., result=25.0-1.788=23.212...
        detection = _make_detection(
            h_thin=[HorizontalLine(y=25.0, x=5.0, x2=95.0, thickness_px=2)],
        )
        result = resolve_field_edge(
            "h_thin[0] - 1em", "top", 14.0, "603:783",
            detection, _make_canvases(),
        )
        expected = 25.0 - (14.0 / 783.0 * 100)
        assert abs(result - expected) < 1e-10

    def test_add_em_on_vertical_edge(self):
        detection = _make_detection(
            h_thin=[HorizontalLine(y=25.0, x=5.0, x2=95.0, thickness_px=2)],
        )
        result = resolve_field_edge(
            "h_thin[0] + 2em", "bottom", 10.0, "603:783",
            detection, _make_canvases(),
        )
        expected = 25.0 + (2.0 * 10.0 / 783.0 * 100)
        assert abs(result - expected) < 1e-10

    def test_em_offset_on_horizontal_edge_uses_width(self):
        # For left/right edges, page_dimension = width
        detection = _make_detection(
            v_thin=[VerticalLine(x=30.0, y=0.0, y2=100.0, thickness_px=2)],
        )
        result = resolve_field_edge(
            "v_thin[0] - 1.5em", "left", 12.0, "603:783",
            detection, _make_canvases(),
        )
        expected = 30.0 - (1.5 * 12.0 / 603.0 * 100)
        assert abs(result - expected) < 1e-10

    def test_em_offset_with_canvas_reference_base(self):
        result = resolve_field_edge(
            "main.right + 1em", "right", 10.0, "603:783",
            _make_detection(), _make_canvases(),
        )
        expected = 90.0 + (1.0 * 10.0 / 603.0 * 100)
        assert abs(result - expected) < 1e-10

    def test_em_offset_with_decimal_em_count(self):
        detection = _make_detection(
            h_thin=[HorizontalLine(y=50.0, x=0.0, x2=100.0, thickness_px=2)],
        )
        result = resolve_field_edge(
            "h_thin[0] - 0.5em", "top", 14.0, "603:783",
            detection, _make_canvases(),
        )
        expected = 50.0 - (0.5 * 14.0 / 783.0 * 100)
        assert abs(result - expected) < 1e-10

    def test_em_offset_without_fontsize_raises(self):
        detection = _make_detection(
            h_thin=[HorizontalLine(y=25.0, x=5.0, x2=95.0, thickness_px=2)],
        )
        with pytest.raises(ValueError, match="requires a fontsize"):
            resolve_field_edge(
                "h_thin[0] - 1em", "top", None, "603:783",
                detection, _make_canvases(),
            )


# ---------------------------------------------------------------------------
# compute_top_default tests
# ---------------------------------------------------------------------------


class TestComputeTopDefault:
    """Tests the top-edge default computation (bottom - 1em)."""

    def test_basic_computation(self):
        # bottom=50.0, fontsize=14, height=783
        result = compute_top_default(50.0, 14.0, "603:783")
        expected = 50.0 - (14.0 / 783.0 * 100)
        assert abs(result - expected) < 1e-10

    def test_different_aspectratio(self):
        result = compute_top_default(80.0, 10.0, "612:792")
        expected = 80.0 - (10.0 / 792.0 * 100)
        assert abs(result - expected) < 1e-10


# ---------------------------------------------------------------------------
# resolve_fields tests
# ---------------------------------------------------------------------------


class TestResolveFieldsValidation:
    """Tests validation in resolve_fields."""

    def test_missing_canvas_raises(self):
        fields = [FieldEntry(name="f1", type="text", left=0, right=100, top=0, bottom=50)]
        with pytest.raises(ValueError, match="no effective 'canvas'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_missing_type_raises(self):
        fields = [FieldEntry(name="f1", canvas="main", left=10, right=90, top=5, bottom=95)]
        with pytest.raises(ValueError, match="no effective 'type'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_invalid_type_raises(self):
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="checkbox",
                left=10, right=90, top=5, bottom=95,
            ),
        ]
        with pytest.raises(ValueError, match="invalid type 'checkbox'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_undefined_canvas_raises(self):
        fields = [
            FieldEntry(
                name="f1", canvas="nonexistent", type="text",
                left=10, right=90, top=5, bottom=95,
            ),
        ]
        with pytest.raises(ValueError, match="undefined canvas 'nonexistent'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_missing_top_without_bottom_raises(self):
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                fontsize=14, left=10, right=90,
            ),
        ]
        with pytest.raises(ValueError, match="omits 'top' but lacks 'bottom'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_missing_top_without_fontsize_raises(self):
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=10, right=90, bottom=50,
            ),
        ]
        with pytest.raises(ValueError, match="omits 'top' but lacks 'bottom' or 'fontsize'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")


class TestResolveFieldsCoordinateConversion:
    """Tests full field resolution with parent-relative conversion."""

    def test_basic_field_resolution(self):
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text", param="char",
                font="Helvetica", fontsize=14, align="CM",
                left=20.0, right=80.0, top=10.0, bottom=50.0,
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), _make_detection(), "603:783",
        )

        assert len(result) == 1
        rf = result[0]
        assert rf.name == "f1"
        assert rf.canvas == "main"
        assert rf.type == "text"
        assert rf.param == "char"
        assert rf.font == "Helvetica"
        assert rf.fontsize == 14
        assert rf.align == "CM"
        # Parent-relative: main is left=10, right=90, top=5, bottom=95
        # x = (20-10)/(90-10)*100 = 12.5
        assert rf.x == 12.5
        # y = (10-5)/(95-5)*100 = 5.6 (rounded to 1 decimal)
        assert abs(rf.y - 5.6) < 0.1

    def test_top_edge_default_applied(self):
        # Field omits top, has bottom=50 and fontsize=14
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text", param="char",
                fontsize=14, left=20.0, right=80.0, bottom=50.0,
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), _make_detection(), "603:783",
        )

        assert len(result) == 1
        rf = result[0]
        # top should be bottom - 1em = 50.0 - (14/783*100)
        expected_top_abs = 50.0 - (14.0 / 783.0 * 100)
        # Convert to parent-relative: y = (top_abs - 5) / (95 - 5) * 100
        expected_y = round((expected_top_abs - 5.0) / 90.0 * 100, 1)
        assert rf.y == expected_y

    def test_preserves_field_order(self):
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=10, right=90, top=5, bottom=20,
            ),
            FieldEntry(
                name="f2", canvas="main", type="line",
                left=10, right=90, top=20, bottom=20,
            ),
            FieldEntry(
                name="f3", canvas="main", type="rectangle",
                left=10, right=90, top=20, bottom=50,
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), _make_detection(), "603:783",
        )

        assert [rf.name for rf in result] == ["f1", "f2", "f3"]

    def test_styles_applied_during_resolution(self):
        styles = {
            "base": {"canvas": "main", "type": "text", "font": "Helvetica", "fontsize": 14},
        }
        fields = [
            FieldEntry(
                name="f1", styles=["base"], param="char",
                left=20.0, right=80.0, top=10.0, bottom=50.0,
            ),
        ]
        result = resolve_fields(
            fields, styles, _make_canvases(), _make_detection(), "603:783",
        )

        assert len(result) == 1
        rf = result[0]
        assert rf.canvas == "main"
        assert rf.type == "text"
        assert rf.font == "Helvetica"
        assert rf.fontsize == 14

    def test_trigger_preserved(self):
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                trigger="societyid", param="player",
                left=10, right=90, top=5, bottom=50,
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), _make_detection(), "603:783",
        )

        assert result[0].trigger == "societyid"

    def test_value_field_preserved(self):
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                value="static text",
                left=10, right=90, top=5, bottom=50,
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), _make_detection(), "603:783",
        )

        assert result[0].value == "static text"
        assert result[0].param is None


# ---------------------------------------------------------------------------
# Field bounds validation tests
# ---------------------------------------------------------------------------

from blueprint2layout.field_resolver import _validate_field_within_canvas


class TestFieldBoundsValidation:
    """Tests that fields outside their canvas bounds raise errors."""

    def test_field_left_outside_canvas_raises(self):
        """Field left edge before canvas left raises ValueError."""
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=5.0, right=50.0, top=10.0, bottom=50.0,
            ),
        ]
        with pytest.raises(ValueError, match="edge 'left'.*left of.*'main'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_field_right_outside_canvas_raises(self):
        """Field right edge past canvas right raises ValueError."""
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=20.0, right=95.0, top=10.0, bottom=50.0,
            ),
        ]
        with pytest.raises(ValueError, match="edge 'right'.*right of.*'main'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_field_top_outside_canvas_raises(self):
        """Field top edge above canvas top raises ValueError."""
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=20.0, right=80.0, top=2.0, bottom=50.0,
            ),
        ]
        with pytest.raises(ValueError, match="edge 'top'.*above.*'main'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_field_bottom_outside_canvas_raises(self):
        """Field bottom edge below canvas bottom raises ValueError."""
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=20.0, right=80.0, top=10.0, bottom=98.0,
            ),
        ]
        with pytest.raises(ValueError, match="edge 'bottom'.*below.*'main'"):
            resolve_fields(fields, {}, _make_canvases(), _make_detection(), "603:783")

    def test_field_exactly_on_canvas_boundary_passes(self):
        """Field edges exactly matching canvas bounds should pass."""
        # main canvas: left=10, right=90, top=5, bottom=95
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=10.0, right=90.0, top=5.0, bottom=95.0,
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), _make_detection(), "603:783",
        )
        assert len(result) == 1

    def test_field_within_canvas_passes(self):
        """Field fully inside canvas bounds should pass."""
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=20.0, right=80.0, top=10.0, bottom=50.0,
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), _make_detection(), "603:783",
        )
        assert len(result) == 1

    def test_error_message_lists_elements_within_canvas(self):
        """Error message includes h_rule elements within the canvas bounds."""
        # Canvas "main" spans top=5, bottom=95
        # h_rule[0] at y=50 is inside, h_rule[1] at y=2 is outside
        detection = _make_detection(
            h_rule=[
                HorizontalLine(y=2.0, x=5.0, x2=95.0, thickness_px=3),
                HorizontalLine(y=50.0, x=10.0, x2=90.0, thickness_px=3),
            ],
        )
        # Field references h_rule[0] (y=2.0) which is above main (top=5.0)
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=20.0, right=80.0, top="h_rule[0]", bottom=50.0,
            ),
        ]
        with pytest.raises(ValueError, match=r"h_rule\[1\]: y=50\.0%") as exc_info:
            resolve_fields(fields, {}, _make_canvases(), detection, "603:783")
        # Should list the element within canvas, not the one outside
        assert "h_rule[0]" not in str(exc_info.value).split("\n", 1)[-1]


# ---------------------------------------------------------------------------
# Canvas-scoped @ reference tests
# ---------------------------------------------------------------------------


class TestCanvasScopedReferences:
    """Tests for @ canvas-scoped element references."""

    def test_scoped_reference_uses_canvas_local_index(self):
        """@h_rule[0] resolves to the first h_rule within the canvas."""
        # Canvas "main" spans top=5, bottom=95
        # h_rule[0] at y=2 is outside, h_rule[1] at y=50 is inside
        # So @h_rule[0] within main should resolve to h_rule[1] (y=50)
        detection = _make_detection(
            h_rule=[
                HorizontalLine(y=2.0, x=5.0, x2=95.0, thickness_px=3),
                HorizontalLine(y=50.0, x=10.0, x2=90.0, thickness_px=3),
            ],
        )
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=20.0, right=80.0, top=10.0, bottom="@h_rule[0]",
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), detection, "603:783",
        )
        # h_rule[1] (y=50) is @h_rule[0] within main
        # parent-relative bottom: (50-5)/(95-5)*100 = 50.0
        assert result[0].y2 == 50.0

    def test_scoped_secondary_axis_reference(self):
        """@h_rule[0].left resolves secondary axis on scoped element."""
        detection = _make_detection(
            h_rule=[
                HorizontalLine(y=2.0, x=1.0, x2=99.0, thickness_px=3),
                HorizontalLine(y=50.0, x=15.0, x2=85.0, thickness_px=3),
            ],
        )
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left="@h_rule[0].left", right="@h_rule[0].right",
                top=10.0, bottom="@h_rule[0]",
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), detection, "603:783",
        )
        # @h_rule[0] within main is h_rule[1] (y=50, x=15, x2=85)
        # parent-relative left: (15-10)/(90-10)*100 = 6.2
        assert result[0].x == 6.2

    def test_scoped_out_of_bounds_raises_with_hint(self):
        """@h_rule[99] raises error when index exceeds scoped elements."""
        detection = _make_detection(
            h_rule=[
                HorizontalLine(y=50.0, x=10.0, x2=90.0, thickness_px=3),
            ],
        )
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=20.0, right=80.0, top=10.0, bottom="@h_rule[99]",
            ),
        ]
        with pytest.raises(ValueError, match="Index 99 out of bounds"):
            resolve_fields(
                fields, {}, _make_canvases(), detection, "603:783",
            )

    def test_global_reference_still_works(self):
        """Plain h_rule[1] still uses global indexing."""
        detection = _make_detection(
            h_rule=[
                HorizontalLine(y=2.0, x=5.0, x2=95.0, thickness_px=3),
                HorizontalLine(y=50.0, x=10.0, x2=90.0, thickness_px=3),
            ],
        )
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text",
                left=20.0, right=80.0, top=10.0, bottom="h_rule[1]",
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), detection, "603:783",
        )
        # h_rule[1] globally is y=50
        assert result[0].y2 == 50.0

    def test_scoped_em_offset(self):
        """@h_rule[0] - 1em works with canvas-scoped reference."""
        detection = _make_detection(
            h_rule=[
                HorizontalLine(y=2.0, x=5.0, x2=95.0, thickness_px=3),
                HorizontalLine(y=50.0, x=10.0, x2=90.0, thickness_px=3),
            ],
        )
        fields = [
            FieldEntry(
                name="f1", canvas="main", type="text", fontsize=14.0,
                left=20.0, right=80.0, bottom="@h_rule[0]",
                top="@h_rule[0] - 1em",
            ),
        ]
        result = resolve_fields(
            fields, {}, _make_canvases(), detection, "603:783",
        )
        # @h_rule[0] within main is h_rule[1] (y=50)
        expected_top = 50.0 - (14.0 / 783.0 * 100)
        expected_y = round((expected_top - 5.0) / 90.0 * 100, 1)
        assert result[0].y == expected_y
