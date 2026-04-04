"""Property-based tests for field resolver.

Uses Hypothesis to verify universal correctness properties for
em offset computation, style override ordering, top-edge defaults,
and missing required field properties.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.8, 5.9, 6.4, 6.5,
    7.10, 8.1, 8.2, 12.2
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from blueprint2layout.field_resolver import (
    compute_top_default,
    resolve_field_edge,
    resolve_field_styles,
    resolve_fields,
)
from blueprint2layout.models import (
    DetectionResult,
    FieldEntry,
    GreyBox,
    HorizontalLine,
    ResolvedCanvas,
    VerticalLine,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_percentage = st.floats(
    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False,
)
_thickness = st.integers(min_value=1, max_value=20)
_fontsize = st.floats(min_value=6.0, max_value=72.0, allow_nan=False, allow_infinity=False)
_em_count = st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)
_operator = st.sampled_from(["+", "-"])
_edge_name = st.sampled_from(["top", "bottom", "left", "right"])

_horizontal_line = st.builds(
    HorizontalLine,
    y=_percentage,
    x=_percentage,
    x2=_percentage,
    thickness_px=_thickness,
)

_vertical_line = st.builds(
    VerticalLine,
    x=_percentage,
    y=_percentage,
    y2=_percentage,
    thickness_px=_thickness,
)


@st.composite
def aspectratio_strings(draw):
    """Generate valid aspectratio strings like '603:783'."""
    width = draw(st.integers(min_value=100, max_value=2000))
    height = draw(st.integers(min_value=100, max_value=2000))
    return f"{width}:{height}"


@st.composite
def detection_with_lines(draw):
    """Generate a DetectionResult with at least one element per line category."""
    return DetectionResult(
        h_thin=draw(st.lists(_horizontal_line, min_size=1, max_size=3)),
        h_bar=draw(st.lists(_horizontal_line, min_size=1, max_size=3)),
        h_rule=draw(st.lists(_horizontal_line, min_size=1, max_size=3)),
        v_thin=draw(st.lists(_vertical_line, min_size=1, max_size=3)),
        v_bar=draw(st.lists(_vertical_line, min_size=1, max_size=3)),
        grey_box=draw(
            st.lists(
                st.builds(GreyBox, x=_percentage, y=_percentage, x2=_percentage, y2=_percentage),
                min_size=1,
                max_size=3,
            ),
        ),
    )


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


# ---------------------------------------------------------------------------
# Property 5: Em offset computation is correct
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 5: Em offset computation is correct


class TestEmOffsetComputationProperty:
    """**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.8, 5.9, 12.2**

    For any valid base reference, em count, fontsize, and aspectratio,
    the em offset computation SHALL produce:
    base_value ± (em_count * fontsize / page_dimension * 100).
    """

    @given(
        base_value=_percentage,
        em_count=_em_count,
        fontsize=_fontsize,
        aspectratio=aspectratio_strings(),
        operator=_operator,
        edge_name=_edge_name,
    )
    @settings(max_examples=100)
    def test_em_offset_matches_manual_computation(
        self,
        base_value: float,
        em_count: float,
        fontsize: float,
        aspectratio: str,
        operator: str,
        edge_name: str,
    ) -> None:
        """Resolved em offset equals base ± (em_count * fontsize / dim * 100)."""
        width_str, height_str = aspectratio.split(":")
        width = float(width_str)
        height = float(height_str)
        page_dimension = height if edge_name in ("top", "bottom") else width

        # Build a detection with a single h_thin line at base_value
        detection = DetectionResult(
            h_thin=[HorizontalLine(y=base_value, x=0.0, x2=100.0, thickness_px=2)],
        )
        canvases = _make_canvases()

        expression = f"h_thin[0] {operator} {em_count}em"
        result = resolve_field_edge(
            expression, edge_name, fontsize, aspectratio, detection, canvases,
        )

        offset = em_count * fontsize / page_dimension * 100
        if operator == "+":
            expected = base_value + offset
        else:
            expected = base_value - offset

        assert abs(result - expected) < 1e-9

    @given(
        base_value=_percentage,
        em_count=_em_count,
        fontsize=_fontsize,
        aspectratio=aspectratio_strings(),
    )
    @settings(max_examples=100)
    def test_em_offset_with_canvas_reference_base(
        self,
        base_value: float,
        em_count: float,
        fontsize: float,
        aspectratio: str,
    ) -> None:
        """Em offset works with canvas reference as base."""
        canvases = {
            "page": ResolvedCanvas(
                name="page", left=0.0, right=100.0, top=0.0, bottom=100.0,
            ),
            "test_canvas": ResolvedCanvas(
                name="test_canvas", left=base_value, right=100.0,
                top=0.0, bottom=100.0, parent="page",
            ),
        }
        detection = DetectionResult()

        width_str, _ = aspectratio.split(":")
        width = float(width_str)
        page_dimension = width  # left is a horizontal edge

        expression = f"test_canvas.left + {em_count}em"
        result = resolve_field_edge(
            expression, "left", fontsize, aspectratio, detection, canvases,
        )

        expected = base_value + (em_count * fontsize / page_dimension * 100)
        assert abs(result - expected) < 1e-9


# ---------------------------------------------------------------------------
# Property 6: Style override ordering follows last-writer-wins
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 6: Style override ordering follows last-writer-wins


_STYLE_PROPS = ("font", "fontsize", "fontweight", "align", "canvas", "type")

_style_value_for_prop = {
    "font": st.sampled_from(["Helvetica", "Arial", "Courier", "Times"]),
    "fontsize": st.floats(min_value=6.0, max_value=72.0, allow_nan=False, allow_infinity=False),
    "fontweight": st.sampled_from(["bold", "normal", "light"]),
    "align": st.sampled_from(["CM", "LB", "RT", "LM", "CB"]),
    "canvas": st.sampled_from(["main", "sidebar", "header"]),
    "type": st.sampled_from(["text", "multiline", "line", "rectangle"]),
}


@st.composite
def style_dict_for_props(draw, props):
    """Generate a style dict with values for the given property names."""
    result = {}
    for prop in props:
        result[prop] = draw(_style_value_for_prop[prop])
    return result


class TestStyleOverrideOrderingProperty:
    """**Validates: Requirements 6.4, 6.5**

    For any field with multiple styles, later styles override earlier
    ones, and direct properties override all styles.
    """

    @given(data=st.data())
    @settings(max_examples=100)
    def test_later_style_overrides_earlier(self, data: st.DataObject) -> None:
        """Later styles in the array override earlier styles."""
        prop = data.draw(st.sampled_from(list(_STYLE_PROPS)))
        style_a_val = data.draw(_style_value_for_prop[prop])
        style_b_val = data.draw(_style_value_for_prop[prop])

        styles = {
            "style_a": {prop: style_a_val},
            "style_b": {prop: style_b_val},
        }
        field = FieldEntry(name="f1", styles=["style_a", "style_b"])

        result = resolve_field_styles(field, styles)

        assert result[prop] == style_b_val

    @given(data=st.data())
    @settings(max_examples=100)
    def test_direct_property_overrides_all_styles(
        self, data: st.DataObject,
    ) -> None:
        """Direct field properties override all style-inherited values."""
        prop = data.draw(st.sampled_from(list(_STYLE_PROPS)))
        style_val = data.draw(_style_value_for_prop[prop])
        direct_val = data.draw(_style_value_for_prop[prop])

        styles = {"base": {prop: style_val}}
        kwargs = {"name": "f1", "styles": ["base"], prop: direct_val}
        field = FieldEntry(**kwargs)

        result = resolve_field_styles(field, styles)

        assert result[prop] == direct_val

    @given(data=st.data())
    @settings(max_examples=100)
    def test_chained_style_base_overridden_by_child(
        self, data: st.DataObject,
    ) -> None:
        """In a style chain, the child style overrides the base style."""
        prop = data.draw(st.sampled_from(list(_STYLE_PROPS)))
        base_val = data.draw(_style_value_for_prop[prop])
        child_val = data.draw(_style_value_for_prop[prop])

        styles = {
            "base_style": {prop: base_val},
            "child_style": {"styles": ["base_style"], prop: child_val},
        }
        field = FieldEntry(name="f1", styles=["child_style"])

        result = resolve_field_styles(field, styles)

        assert result[prop] == child_val


# ---------------------------------------------------------------------------
# Property 8: Top edge defaults to bottom minus one em
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 8: Top edge defaults to bottom minus one em


class TestTopEdgeDefaultProperty:
    """**Validates: Requirements 8.1**

    For any field that omits top but has bottom and fontsize, the
    computed top SHALL equal bottom - (fontsize / page_height * 100).
    """

    @given(
        bottom_value=_percentage,
        fontsize=_fontsize,
        aspectratio=aspectratio_strings(),
    )
    @settings(max_examples=100)
    def test_top_default_equals_bottom_minus_one_em(
        self,
        bottom_value: float,
        fontsize: float,
        aspectratio: str,
    ) -> None:
        """compute_top_default produces bottom - (fontsize / height * 100)."""
        _, height_str = aspectratio.split(":")
        height = float(height_str)

        result = compute_top_default(bottom_value, fontsize, aspectratio)

        expected = bottom_value - (fontsize / height * 100)
        assert abs(result - expected) < 1e-9


# ---------------------------------------------------------------------------
# Property 15: Missing required field properties after resolution raise errors
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 15: Missing required field properties after resolution raise errors


class TestMissingRequiredFieldPropertiesProperty:
    """**Validates: Requirements 7.10, 8.2**

    For any field missing canvas or type after style resolution,
    resolve_fields SHALL raise ValueError.
    """

    @given(
        field_type=st.sampled_from(["text", "multiline", "line", "rectangle"]),
    )
    @settings(max_examples=100)
    def test_missing_canvas_raises_value_error(self, field_type: str) -> None:
        """Field without canvas after style resolution raises ValueError."""
        field = FieldEntry(
            name="test_field",
            type=field_type,
            left=10, right=90, top=5, bottom=50,
        )

        with pytest.raises(ValueError, match="no effective 'canvas'"):
            resolve_fields(
                [field], {}, _make_canvases(),
                DetectionResult(), "603:783",
            )

    @given(
        canvas_name=st.just("main"),
    )
    @settings(max_examples=100)
    def test_missing_type_raises_value_error(self, canvas_name: str) -> None:
        """Field without type after style resolution raises ValueError."""
        field = FieldEntry(
            name="test_field",
            canvas=canvas_name,
            left=10, right=90, top=5, bottom=50,
        )

        with pytest.raises(ValueError, match="no effective 'type'"):
            resolve_fields(
                [field], {}, _make_canvases(),
                DetectionResult(), "603:783",
            )

    @given(
        fontsize=_fontsize,
    )
    @settings(max_examples=100)
    def test_missing_top_without_bottom_raises_value_error(
        self, fontsize: float,
    ) -> None:
        """Field omitting top without bottom raises ValueError."""
        field = FieldEntry(
            name="test_field",
            canvas="main",
            type="text",
            fontsize=fontsize,
            left=10, right=90,
        )

        with pytest.raises(ValueError, match="omits 'top' but lacks"):
            resolve_fields(
                [field], {}, _make_canvases(),
                DetectionResult(), "603:783",
            )

    @given(
        bottom_value=_percentage,
    )
    @settings(max_examples=100)
    def test_missing_top_without_fontsize_raises_value_error(
        self, bottom_value: float,
    ) -> None:
        """Field omitting top without fontsize raises ValueError."""
        field = FieldEntry(
            name="test_field",
            canvas="main",
            type="text",
            left=10, right=90,
            bottom=bottom_value,
        )

        with pytest.raises(ValueError, match="omits 'top' but lacks"):
            resolve_fields(
                [field], {}, _make_canvases(),
                DetectionResult(), "603:783",
            )
