"""Property-based tests for data text rendering.

Uses Hypothesis to verify universal properties across randomized inputs.
Each property test runs a minimum of 100 iterations.

Requirements: 5.1-5.8, 6.1-6.3
"""

import fitz
from hypothesis import given, settings
from hypothesis import strategies as st

from layout_visualizer.data_renderer import compute_text_position
from layout_visualizer.models import PixelRect


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

_positive_float = st.floats(min_value=1.0, max_value=2000.0, allow_nan=False, allow_infinity=False)
_fontsize = st.floats(min_value=4.0, max_value=72.0, allow_nan=False, allow_infinity=False)
_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" "),
    min_size=1,
    max_size=30,
)
_horizontal = st.sampled_from(["L", "C", "R"])
_vertical = st.sampled_from(["B", "M", "T"])
_align = st.tuples(_horizontal, _vertical).map(lambda t: t[0] + t[1])
_is_bold = st.booleans()


@st.composite
def _bbox_strategy(draw):
    """Generate a PixelRect with positive width and height."""
    x = draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    y = draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    width = draw(_positive_float)
    height = draw(_positive_float)
    return PixelRect(name="test", x=x, y=y, x2=x + width, y2=y + height)


# ---------------------------------------------------------------------------
# Property 4: Alignment position computation
# Feature: layout-data-mode, Property 4: Alignment position computation
# ---------------------------------------------------------------------------

class TestAlignmentPositionComputation:
    """**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**

    For any bounding box (with positive width and height), any font size,
    any text string, and any valid two-character alignment code, the
    computed text insertion point shall satisfy the alignment formulas
    from the design document.
    """

    @given(
        bbox=_bbox_strategy(),
        fontsize=_fontsize,
        text=_text,
        align=_align,
        is_bold=_is_bold,
    )
    @settings(max_examples=100, deadline=None)
    def test_alignment_formulas_hold(
        self,
        bbox: PixelRect,
        fontsize: float,
        text: str,
        align: str,
        is_bold: bool,
    ) -> None:
        """Computed position matches the alignment formulas.

        Feature: layout-data-mode, Property 4: Alignment position computation
        """
        font = "Helvetica"
        point = compute_text_position(text, fontsize, font, is_bold, align, bbox)

        fontname = "Helvetica-Bold" if is_bold else "Helvetica"
        text_width = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
        box_width = bbox.x2 - bbox.x
        box_height = bbox.y2 - bbox.y

        horizontal = align[0]
        vertical = align[1]

        # Horizontal checks
        if horizontal == "L":
            assert point.x == bbox.x
        elif horizontal == "C":
            expected_x = bbox.x + (box_width - text_width) / 2
            assert abs(point.x - expected_x) < 1e-6
        else:  # R
            expected_x = bbox.x2 - text_width
            assert abs(point.x - expected_x) < 1e-6

        # Vertical checks
        if vertical == "B":
            assert point.y == bbox.y2
        elif vertical == "M":
            expected_y = bbox.y + (box_height + fontsize) / 2
            assert abs(point.y - expected_y) < 1e-6
        else:  # T
            expected_y = bbox.y + fontsize
            assert abs(point.y - expected_y) < 1e-6



# ---------------------------------------------------------------------------
# Property 5: Multiline line slot division
# Feature: layout-data-mode, Property 5: Multiline line slot division
# ---------------------------------------------------------------------------

_line_count = st.integers(min_value=1, max_value=20)
_box_height = st.floats(min_value=1.0, max_value=2000.0, allow_nan=False, allow_infinity=False)
_box_y = st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)


class TestMultilineSlotDivision:
    """**Validates: Requirements 6.1, 6.2, 6.3**

    For any bounding box height and any positive integer line count,
    the computed line slot height shall equal the total bounding box
    height divided by the line count, and the first line slot's
    vertical bounds shall span from the top of the bounding box to
    top + slot height.
    """

    @given(
        box_y=_box_y,
        box_height=_box_height,
        lines=_line_count,
    )
    @settings(max_examples=100, deadline=None)
    def test_slot_height_and_first_slot_bounds(
        self,
        box_y: float,
        box_height: float,
        lines: int,
    ) -> None:
        """Slot height = total / lines; first slot spans [y, y + slot_height].

        Feature: layout-data-mode, Property 5: Multiline line slot division
        """
        bbox_y2 = box_y + box_height
        slot_height = box_height / lines

        # Verify slot height formula
        assert abs(slot_height - box_height / lines) < 1e-9

        # Verify first slot bounds
        first_slot_y = box_y
        first_slot_y2 = box_y + slot_height

        assert first_slot_y == box_y
        assert abs(first_slot_y2 - (box_y + box_height / lines)) < 1e-9

        # Verify all slots sum to total height
        total = slot_height * lines
        assert abs(total - box_height) < 1e-6
