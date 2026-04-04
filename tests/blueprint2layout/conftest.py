"""Shared fixtures and Hypothesis strategies for blueprint2layout tests.

Provides canonical, reusable Hypothesis strategies that can be imported
by any PBT test file in this package. Strategies are exported as
module-level functions for use with ``@given`` decorators.
"""

from __future__ import annotations

from hypothesis import strategies as st

from blueprint2layout.models import (
    DetectionResult,
    FieldEntry,
    GreyBox,
    HorizontalLine,
    VerticalLine,
)

# ---------------------------------------------------------------------------
# Primitive building blocks
# ---------------------------------------------------------------------------

_percentage = st.floats(
    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False,
)
_thickness = st.integers(min_value=1, max_value=20)

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

_grey_box = st.builds(
    GreyBox,
    x=_percentage,
    y=_percentage,
    x2=_percentage,
    y2=_percentage,
)

_HORIZONTAL_CATEGORIES = ("h_thin", "h_bar", "h_rule")
_VERTICAL_CATEGORIES = ("v_thin", "v_bar")

_VALID_FIELD_TYPES = ("text", "multiline", "line", "rectangle")
_KNOWN_CANVASES = ("page", "main", "sidebar", "header")

_simple_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=15,
)


# ---------------------------------------------------------------------------
# 1. parameter_groups — dict-of-dicts matching the parameter schema
# ---------------------------------------------------------------------------

_param_definition = st.fixed_dictionaries(
    {"type": st.just("text")},
    optional={"description": st.text(min_size=1, max_size=30)},
)

_param_group = st.dictionaries(
    keys=_simple_name,
    values=_param_definition,
    min_size=1,
    max_size=5,
)


@st.composite
def parameter_groups(draw):
    """Generate a valid parameters dict (dict of parameter groups)."""
    return draw(
        st.dictionaries(
            keys=_simple_name,
            values=_param_group,
            min_size=1,
            max_size=4,
        ),
    )


# ---------------------------------------------------------------------------
# 2. field_style_dicts — valid field_styles with no circular references
# ---------------------------------------------------------------------------

_style_property_bundle = st.fixed_dictionaries(
    {},
    optional={
        "font": st.sampled_from(["Helvetica", "Arial", "Courier", "Times"]),
        "fontsize": st.integers(min_value=6, max_value=72),
        "fontweight": st.sampled_from(["bold", "normal"]),
        "align": st.sampled_from(["CM", "LB", "LM", "RB"]),
        "color": st.text(min_size=1, max_size=10),
    },
)


@st.composite
def field_style_dicts(draw):
    """Generate a valid field_styles dict with no circular references.

    Style names are simple alphanumeric strings. Each style definition
    is a flat property bundle (no ``styles`` key referencing other
    styles), which guarantees no circular references.
    """
    return draw(
        st.dictionaries(
            keys=_simple_name,
            values=_style_property_bundle,
            min_size=1,
            max_size=5,
        ),
    )


# ---------------------------------------------------------------------------
# 3. field_entries — valid FieldEntry instances
# ---------------------------------------------------------------------------


@st.composite
def field_entries(draw):
    """Generate a valid FieldEntry with consistent canvas/type/edge values."""
    canvas = draw(st.sampled_from(_KNOWN_CANVASES))
    field_type = draw(st.sampled_from(_VALID_FIELD_TYPES))
    name = draw(_simple_name)

    left = draw(_percentage)
    right = draw(_percentage)
    top = draw(_percentage)
    bottom = draw(_percentage)

    return FieldEntry(
        name=name,
        canvas=canvas,
        type=field_type,
        left=left,
        right=right,
        top=top,
        bottom=bottom,
    )


# ---------------------------------------------------------------------------
# 4. detection_results_with_elements — at least one element per category
# ---------------------------------------------------------------------------


@st.composite
def detection_results_with_elements(draw):
    """Generate a DetectionResult with at least one element per category."""
    return DetectionResult(
        h_thin=draw(st.lists(_horizontal_line, min_size=1, max_size=5)),
        h_bar=draw(st.lists(_horizontal_line, min_size=1, max_size=5)),
        h_rule=draw(st.lists(_horizontal_line, min_size=1, max_size=5)),
        v_thin=draw(st.lists(_vertical_line, min_size=1, max_size=5)),
        v_bar=draw(st.lists(_vertical_line, min_size=1, max_size=5)),
        grey_box=draw(st.lists(_grey_box, min_size=1, max_size=5)),
    )


# ---------------------------------------------------------------------------
# 5. aspectratio_strings — valid "width:height" strings
# ---------------------------------------------------------------------------


@st.composite
def aspectratio_strings(draw):
    """Generate a valid aspectratio string like ``'603:783'``."""
    width = draw(st.integers(min_value=100, max_value=2000))
    height = draw(st.integers(min_value=100, max_value=2000))
    return f"{width}:{height}"


# ---------------------------------------------------------------------------
# 6. em_offset_expressions — valid em offset expression strings
# ---------------------------------------------------------------------------


@st.composite
def em_offset_expressions(draw):
    """Generate a valid em offset expression like ``'h_thin[0] + 1.5em'``.

    The base reference is a line reference drawn from a known set of
    categories and a small index range.
    """
    category = draw(st.sampled_from(
        ["h_thin", "h_bar", "h_rule", "v_thin", "v_bar"],
    ))
    index = draw(st.integers(min_value=0, max_value=4))
    operator = draw(st.sampled_from(["+", "-"]))
    em_count = draw(
        st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    return f"{category}[{index}] {operator} {em_count}em"
