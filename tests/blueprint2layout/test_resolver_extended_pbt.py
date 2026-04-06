"""Property-based tests for extended edge value resolution.

Uses Hypothesis to verify universal correctness properties for
secondary axis references, invalid secondary edges, and unrecognized
edge value strings.

Validates: Requirements 4.1, 4.2, 4.4, 4.5, 12.1, 12.3, 12.5
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from blueprint2layout.models import (
    DetectionResult,
    GreyBox,
    HorizontalLine,
    VerticalLine,
)
from blueprint2layout.resolver import resolve_edge_value


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_percentage = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
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
_ALL_LINE_CATEGORIES = _HORIZONTAL_CATEGORIES + _VERTICAL_CATEGORIES


@st.composite
def detection_with_elements(draw):
    """Generate a DetectionResult with at least one element per category."""
    return DetectionResult(
        h_thin=draw(st.lists(_horizontal_line, min_size=1, max_size=5)),
        h_bar=draw(st.lists(_horizontal_line, min_size=1, max_size=5)),
        h_rule=draw(st.lists(_horizontal_line, min_size=1, max_size=5)),
        v_thin=draw(st.lists(_vertical_line, min_size=1, max_size=5)),
        v_bar=draw(st.lists(_vertical_line, min_size=1, max_size=5)),
        grey_box=draw(st.lists(_grey_box, min_size=1, max_size=5)),
    )


@st.composite
def valid_secondary_axis_reference(draw, detection: DetectionResult):
    """Generate a valid secondary axis reference string and expected value.

    Returns a tuple of (reference_string, expected_value).
    """
    # Choose between horizontal, vertical, or grey_box
    choice = draw(st.sampled_from(["horizontal", "vertical", "grey_box"]))

    if choice == "horizontal":
        category = draw(st.sampled_from(_HORIZONTAL_CATEGORIES))
        elements = getattr(detection, category)
        index = draw(st.integers(min_value=0, max_value=len(elements) - 1))
        edge = draw(st.sampled_from(["left", "right", "top", "bottom"]))
        element = elements[index]
        attr_map = {"left": "x", "right": "x2", "top": "y", "bottom": "y2"}
        expected = getattr(element, attr_map[edge])
    elif choice == "vertical":
        category = draw(st.sampled_from(_VERTICAL_CATEGORIES))
        elements = getattr(detection, category)
        index = draw(st.integers(min_value=0, max_value=len(elements) - 1))
        edge = draw(st.sampled_from(["top", "bottom"]))
        element = elements[index]
        expected = element.y if edge == "top" else element.y2
    else:
        category = "grey_box"
        elements = detection.grey_box
        index = draw(st.integers(min_value=0, max_value=len(elements) - 1))
        edge = draw(st.sampled_from(["left", "right", "top", "bottom"]))
        element = elements[index]
        attr_map = {"left": "x", "right": "x2", "top": "y", "bottom": "y2"}
        expected = getattr(element, attr_map[edge])

    ref_string = f"{category}[{index}].{edge}"
    return ref_string, expected


@st.composite
def invalid_secondary_axis_reference(draw):
    """Generate a secondary axis reference with a bogus edge name.

    All standard categories now support left/right/top/bottom, so
    the only invalid edges are non-standard names like 'center'.
    """
    category = draw(st.sampled_from(
        list(_HORIZONTAL_CATEGORIES) + list(_VERTICAL_CATEGORIES) + ["grey_box"],
    ))
    edge = draw(st.sampled_from(["center", "middle", "start", "end"]))
    index = draw(st.integers(min_value=0, max_value=4))
    return f"{category}[{index}].{edge}"


# Strategy for strings that don't match any recognized edge value pattern.
# Avoids: numeric-like strings, valid line refs, secondary axis refs,
# canvas refs (word.edge), and em offset expressions.
_unrecognized_edge_value = st.text(
    alphabet=st.characters(
        whitelist_categories=("L",),
        whitelist_characters="-_!@#%^&*",
    ),
    min_size=2,
    max_size=30,
).filter(
    lambda s: (
        # Not a number
        not s.replace(".", "", 1).replace("-", "", 1).lstrip().isdigit()
        # Not a valid line reference pattern (category[index])
        and "[" not in s
        # Not a canvas reference pattern (word.edge)
        and not (
            "." in s
            and s.split(".", 1)[-1] in ("left", "right", "top", "bottom")
            and s.split(".", 1)[0].replace("_", "").isalnum()
        )
        # Not an em offset expression
        and "em" not in s.lower()
    )
)


# ---------------------------------------------------------------------------
# Property 3: Secondary axis resolution matches element attributes
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 3: Secondary axis resolution matches element attributes


class TestSecondaryAxisResolutionProperty:
    """**Validates: Requirements 4.1, 4.2, 4.5, 12.1, 12.3**

    For any DetectionResult and any valid secondary axis reference,
    the resolved value SHALL equal the corresponding attribute of the
    detected element.
    """

    @given(data=st.data(), detection=detection_with_elements())
    @settings(max_examples=100)
    def test_resolved_value_matches_element_attribute(
        self, data: st.DataObject, detection: DetectionResult,
    ) -> None:
        """Resolved secondary axis value equals the element's attribute."""
        ref_string, expected = data.draw(
            valid_secondary_axis_reference(detection),
        )

        result = resolve_edge_value(ref_string, detection, {})

        assert result == expected


# ---------------------------------------------------------------------------
# Property 4: Invalid secondary edge names raise errors
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 4: Invalid secondary edge names raise errors


class TestInvalidSecondaryEdgeProperty:
    """**Validates: Requirements 4.4**

    For any secondary axis reference that uses an edge name not in
    (left, right, top, bottom), the resolver SHALL raise a ValueError.
    All standard categories now support all four edges, so only
    non-standard edge names are invalid.
    """

    @given(
        ref_string=invalid_secondary_axis_reference(),
        detection=detection_with_elements(),
    )
    @settings(max_examples=100)
    def test_invalid_edge_raises_value_error(
        self, ref_string: str, detection: DetectionResult,
    ) -> None:
        """Bogus secondary edge name raises ValueError."""
        with pytest.raises(ValueError, match="not a recognized pattern"):
            resolve_edge_value(ref_string, detection, {})


# ---------------------------------------------------------------------------
# Property 16: Unrecognized edge value strings raise errors
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 16: Unrecognized edge value strings raise errors


class TestUnrecognizedEdgeValueProperty:
    """**Validates: Requirements 12.5**

    For any edge value string that doesn't match any recognized pattern,
    the resolver SHALL raise a ValueError.
    """

    @given(bad_value=_unrecognized_edge_value)
    @settings(max_examples=100)
    def test_unrecognized_string_raises_value_error(
        self, bad_value: str,
    ) -> None:
        """Unrecognized edge value string raises ValueError."""
        empty_detection = DetectionResult()

        with pytest.raises(ValueError, match="not a recognized pattern"):
            resolve_edge_value(bad_value, empty_detection, {})
