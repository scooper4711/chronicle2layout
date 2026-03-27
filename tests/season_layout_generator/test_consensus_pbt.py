"""Property-based tests for consensus computation and variant grouping.

Uses hypothesis to verify universal properties of compute_consensus,
exceeds_divergence, and group_variants across randomly generated inputs.
"""

from __future__ import annotations

import statistics

from hypothesis import given, settings
from hypothesis import strategies as st

from season_layout_generator.consensus import (
    DIVERGENCE_THRESHOLD,
    compute_consensus,
    exceeds_divergence,
    group_variants,
)
from season_layout_generator.models import (
    CanvasCoordinates,
    PageRegions,
    PdfAnalysisResult,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


def canvas_coordinates_strategy(
    min_val: float = 0.0,
    max_val: float = 100.0,
) -> st.SearchStrategy[CanvasCoordinates]:
    """Generate valid CanvasCoordinates with x < x2 and y < y2."""
    return st.builds(
        _make_canvas_coordinates,
        x1=st.floats(min_value=min_val, max_value=max_val - 1, allow_nan=False, allow_infinity=False),
        x2_offset=st.floats(min_value=0.1, max_value=max_val, allow_nan=False, allow_infinity=False),
        y1=st.floats(min_value=min_val, max_value=max_val - 1, allow_nan=False, allow_infinity=False),
        y2_offset=st.floats(min_value=0.1, max_value=max_val, allow_nan=False, allow_infinity=False),
    )


def _make_canvas_coordinates(
    x1: float, x2_offset: float, y1: float, y2_offset: float,
) -> CanvasCoordinates:
    """Build CanvasCoordinates ensuring x < x2, y < y2, all in [0, 100]."""
    x = max(0.0, min(x1, 99.9))
    x2 = min(100.0, x + x2_offset)
    if x2 <= x:
        x2 = min(100.0, x + 0.1)
    y = max(0.0, min(y1, 99.9))
    y2 = min(100.0, y + y2_offset)
    if y2 <= y:
        y2 = min(100.0, y + 0.1)
    return CanvasCoordinates(x=x, y=y, x2=x2, y2=y2)


def optional_canvas_strategy() -> st.SearchStrategy[CanvasCoordinates | None]:
    """Generate either a valid CanvasCoordinates or None."""
    return st.one_of(st.none(), canvas_coordinates_strategy())


def page_regions_strategy() -> st.SearchStrategy[PageRegions]:
    """Generate a PageRegions with random optional coordinates."""
    return st.builds(
        PageRegions,
        main=optional_canvas_strategy(),
        player_info=optional_canvas_strategy(),
        summary=optional_canvas_strategy(),
        rewards=optional_canvas_strategy(),
        items=optional_canvas_strategy(),
        notes=optional_canvas_strategy(),
        boons=optional_canvas_strategy(),
        reputation=optional_canvas_strategy(),
        session_info=optional_canvas_strategy(),
    )


def page_regions_with_at_least_one_strategy() -> st.SearchStrategy[PageRegions]:
    """Generate PageRegions with at least the main region present."""
    return st.builds(
        PageRegions,
        main=canvas_coordinates_strategy(),
        player_info=optional_canvas_strategy(),
        summary=optional_canvas_strategy(),
        rewards=optional_canvas_strategy(),
        items=optional_canvas_strategy(),
        notes=optional_canvas_strategy(),
        boons=optional_canvas_strategy(),
        reputation=optional_canvas_strategy(),
        session_info=optional_canvas_strategy(),
    )


def pdf_analysis_result_strategy() -> st.SearchStrategy[PdfAnalysisResult]:
    """Generate a PdfAnalysisResult with a plausible filename."""
    return st.builds(
        PdfAnalysisResult,
        filename=st.from_regex(r"\d-\d{2}-[A-Za-z]+Chronicle\.pdf", fullmatch=True),
        regions=page_regions_with_at_least_one_strategy(),
    )


# ---------------------------------------------------------------------------
# Property 4: Canvas coordinates are in valid percentage range
# ---------------------------------------------------------------------------


# Feature: season-layout-generator, Property 4: Canvas coordinates are in valid percentage range
@given(regions=page_regions_strategy())
def test_coordinates_in_valid_range(regions: PageRegions) -> None:
    """For any PageRegions, every non-None CanvasCoordinates field has
    x, y in [0, 100] and x < x2, y < y2.

    Validates: Requirements 4.2, 5.2, 6.2, 7.2, 8.2, 9.2, 10.2, 11.2, 12.2
    """
    region_fields = [
        "main", "player_info", "summary", "rewards",
        "items", "notes", "boons", "reputation", "session_info",
    ]
    for field_name in region_fields:
        coords: CanvasCoordinates | None = getattr(regions, field_name)
        if coords is None:
            continue
        assert 0.0 <= coords.x <= 100.0, f"{field_name}.x out of range: {coords.x}"
        assert 0.0 <= coords.y <= 100.0, f"{field_name}.y out of range: {coords.y}"
        assert 0.0 <= coords.x2 <= 100.0, f"{field_name}.x2 out of range: {coords.x2}"
        assert 0.0 <= coords.y2 <= 100.0, f"{field_name}.y2 out of range: {coords.y2}"
        assert coords.x < coords.x2, f"{field_name}: x ({coords.x}) >= x2 ({coords.x2})"
        assert coords.y < coords.y2, f"{field_name}: y ({coords.y}) >= y2 ({coords.y2})"


# ---------------------------------------------------------------------------
# Property 5: Median consensus computation
# ---------------------------------------------------------------------------


# Feature: season-layout-generator, Property 5: Median consensus computation
@given(
    regions_list=st.lists(
        page_regions_with_at_least_one_strategy(),
        min_size=1,
        max_size=20,
    )
)
def test_median_consensus(regions_list: list[PageRegions]) -> None:
    """For any list of PageRegions (length >= 1), compute_consensus returns
    a PageRegions where each coordinate equals the statistical median of
    the corresponding coordinates across all inputs that have that region.

    Validates: Requirements 13.2
    """
    consensus = compute_consensus(regions_list)

    region_fields = [
        "main", "player_info", "summary", "rewards",
        "items", "notes", "boons", "reputation", "session_info",
    ]
    coord_fields = ("x", "y", "x2", "y2")

    for field_name in region_fields:
        # Collect all non-None values for this region
        present_coords = [
            getattr(r, field_name)
            for r in regions_list
            if getattr(r, field_name) is not None
        ]

        consensus_coords = getattr(consensus, field_name)

        if not present_coords:
            assert consensus_coords is None, (
                f"{field_name} should be None when no inputs have it"
            )
            continue

        assert consensus_coords is not None, (
            f"{field_name} should not be None when {len(present_coords)} inputs have it"
        )

        for coord_name in coord_fields:
            values = [getattr(c, coord_name) for c in present_coords]
            expected_median = statistics.median(values)
            actual = getattr(consensus_coords, coord_name)
            assert actual == expected_median, (
                f"{field_name}.{coord_name}: expected median {expected_median}, "
                f"got {actual}"
            )


# ---------------------------------------------------------------------------
# Property 6: Variant grouping splits at divergence points
# ---------------------------------------------------------------------------


def _make_divergent_regions(
    base: CanvasCoordinates, offset: float,
) -> PageRegions:
    """Create PageRegions with main shifted by offset from base."""
    return PageRegions(
        main=CanvasCoordinates(
            x=max(0.0, min(100.0, base.x + offset)),
            y=max(0.0, min(100.0, base.y + offset)),
            x2=max(0.0, min(100.0, base.x2 + offset)),
            y2=max(0.0, min(100.0, base.y2 + offset)),
        )
    )


# Feature: season-layout-generator, Property 6: Variant grouping splits at divergence points
@given(
    base_x=st.floats(min_value=10.0, max_value=40.0, allow_nan=False, allow_infinity=False),
    base_y=st.floats(min_value=10.0, max_value=40.0, allow_nan=False, allow_infinity=False),
    group1_size=st.integers(min_value=1, max_value=5),
    group2_size=st.integers(min_value=1, max_value=5),
    small_jitter=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_variant_grouping_splits_at_divergence(
    base_x: float,
    base_y: float,
    group1_size: int,
    group2_size: int,
    small_jitter: float,
) -> None:
    """For any ordered sequence of PageRegions with a known divergence
    point, group_variants produces groups where within-group coordinates
    are within threshold and the first PDF of a new group exceeds the
    threshold from the previous group's consensus.

    Validates: Requirements 14.1, 14.2
    """
    threshold = DIVERGENCE_THRESHOLD
    base = CanvasCoordinates(x=base_x, y=base_y, x2=base_x + 20, y2=base_y + 20)

    # Group 1: all close to base (small jitter within threshold)
    group1_results = [
        PdfAnalysisResult(
            filename=f"1-{i:02d}-TestChronicle.pdf",
            regions=_make_divergent_regions(base, small_jitter * 0.5),
        )
        for i in range(group1_size)
    ]

    # Group 2: shifted well beyond threshold
    large_offset = threshold + 10.0
    group2_results = [
        PdfAnalysisResult(
            filename=f"1-{group1_size + i:02d}-TestChronicle.pdf",
            regions=_make_divergent_regions(base, large_offset),
        )
        for i in range(group2_size)
    ]

    all_results = group1_results + group2_results
    groups = group_variants(all_results, threshold)

    # Should produce exactly 2 groups
    assert len(groups) == 2, (
        f"Expected 2 groups, got {len(groups)}"
    )
    assert len(groups[0].results) == group1_size
    assert len(groups[1].results) == group2_size
