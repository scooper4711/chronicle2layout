"""Unit tests for consensus computation and variant grouping.

Tests concrete examples and edge cases for compute_consensus,
exceeds_divergence, and group_variants.

Requirements: season-layout-generator 13.1, 13.2, 13.3, 14.1, 14.2,
    14.3, 14.4, 14.5
"""

from __future__ import annotations

import pytest

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

# Reusable coordinates for tests
COORDS_A = CanvasCoordinates(x=5.0, y=10.0, x2=50.0, y2=80.0)
COORDS_B = CanvasCoordinates(x=6.0, y=11.0, x2=51.0, y2=81.0)
COORDS_C = CanvasCoordinates(x=7.0, y=12.0, x2=52.0, y2=82.0)
COORDS_FAR = CanvasCoordinates(x=30.0, y=40.0, x2=80.0, y2=95.0)


class TestComputeConsensus:
    """Tests for compute_consensus."""

    def test_single_pdf(self) -> None:
        """Consensus of a single PageRegions returns the same coordinates."""
        regions = PageRegions(main=COORDS_A, player_info=COORDS_B)
        result = compute_consensus([regions])

        assert result.main == COORDS_A
        assert result.player_info == COORDS_B

    def test_all_none_regions(self) -> None:
        """Consensus of all-None PageRegions returns all-None."""
        regions = PageRegions()
        result = compute_consensus([regions, regions])

        assert result.main is None
        assert result.player_info is None
        assert result.summary is None

    def test_median_of_three(self) -> None:
        """Median of three values picks the middle one."""
        r1 = PageRegions(main=COORDS_A)
        r2 = PageRegions(main=COORDS_B)
        r3 = PageRegions(main=COORDS_C)
        result = compute_consensus([r1, r2, r3])

        assert result.main is not None
        assert result.main.x == pytest.approx(6.0)
        assert result.main.y == pytest.approx(11.0)
        assert result.main.x2 == pytest.approx(51.0)
        assert result.main.y2 == pytest.approx(81.0)

    def test_mixed_presence(self) -> None:
        """Regions present in some but not all PDFs use only present values."""
        r1 = PageRegions(main=COORDS_A, reputation=COORDS_B)
        r2 = PageRegions(main=COORDS_C, reputation=None)
        result = compute_consensus([r1, r2])

        # main: median of A and C
        assert result.main is not None
        assert result.main.x == pytest.approx((5.0 + 7.0) / 2)
        # reputation: only one value, so it's that value
        assert result.reputation == COORDS_B

    def test_median_of_even_count(self) -> None:
        """Median of two values returns their average."""
        r1 = PageRegions(main=CanvasCoordinates(x=10.0, y=20.0, x2=60.0, y2=90.0))
        r2 = PageRegions(main=CanvasCoordinates(x=20.0, y=30.0, x2=70.0, y2=80.0))
        result = compute_consensus([r1, r2])

        assert result.main is not None
        assert result.main.x == pytest.approx(15.0)
        assert result.main.y == pytest.approx(25.0)
        assert result.main.x2 == pytest.approx(65.0)
        assert result.main.y2 == pytest.approx(85.0)

    def test_empty_list(self) -> None:
        """Consensus of empty list returns all-None PageRegions."""
        result = compute_consensus([])

        assert result.main is None
        assert result.player_info is None


class TestExceedsDivergence:
    """Tests for exceeds_divergence."""

    def test_identical_regions(self) -> None:
        """Identical regions do not exceed divergence."""
        regions = PageRegions(main=COORDS_A)
        consensus = PageRegions(main=COORDS_A)
        assert not exceeds_divergence(regions, consensus)

    def test_within_threshold(self) -> None:
        """Regions within threshold do not diverge."""
        regions = PageRegions(main=COORDS_A)
        close = CanvasCoordinates(
            x=COORDS_A.x + 2.0,
            y=COORDS_A.y + 2.0,
            x2=COORDS_A.x2 + 2.0,
            y2=COORDS_A.y2 + 2.0,
        )
        consensus = PageRegions(main=close)
        assert not exceeds_divergence(regions, consensus)

    def test_exceeds_threshold(self) -> None:
        """Regions beyond threshold diverge."""
        regions = PageRegions(main=COORDS_A)
        consensus = PageRegions(main=COORDS_FAR)
        assert exceeds_divergence(regions, consensus)

    def test_boundary_at_threshold(self) -> None:
        """Exactly at threshold does not diverge (uses strict >)."""
        regions = PageRegions(main=COORDS_A)
        at_threshold = CanvasCoordinates(
            x=COORDS_A.x + DIVERGENCE_THRESHOLD,
            y=COORDS_A.y,
            x2=COORDS_A.x2,
            y2=COORDS_A.y2,
        )
        consensus = PageRegions(main=at_threshold)
        assert not exceeds_divergence(regions, consensus)

    def test_just_over_threshold(self) -> None:
        """Just over threshold diverges."""
        regions = PageRegions(main=COORDS_A)
        over = CanvasCoordinates(
            x=COORDS_A.x + DIVERGENCE_THRESHOLD + 0.01,
            y=COORDS_A.y,
            x2=COORDS_A.x2,
            y2=COORDS_A.y2,
        )
        consensus = PageRegions(main=over)
        assert exceeds_divergence(regions, consensus)

    def test_both_none_skipped(self) -> None:
        """When both sides are None for a region, no divergence."""
        regions = PageRegions(main=None)
        consensus = PageRegions(main=None)
        assert not exceeds_divergence(regions, consensus)

    def test_one_none_skipped(self) -> None:
        """When one side is None for a region, that region is skipped."""
        regions = PageRegions(main=COORDS_A, reputation=None)
        consensus = PageRegions(main=COORDS_A, reputation=COORDS_FAR)
        assert not exceeds_divergence(regions, consensus)


def _make_result(
    filename: str, main: CanvasCoordinates,
) -> PdfAnalysisResult:
    """Helper to create a PdfAnalysisResult with only main region."""
    return PdfAnalysisResult(filename=filename, regions=PageRegions(main=main))


class TestGroupVariants:
    """Tests for group_variants."""

    def test_empty_results(self) -> None:
        """Empty input produces empty output."""
        assert group_variants([]) == []

    def test_single_variant_no_splits(self) -> None:
        """All similar PDFs stay in one group."""
        results = [
            _make_result("5-01-AChronicle.pdf", COORDS_A),
            _make_result("5-02-BChronicle.pdf", COORDS_B),
            _make_result("5-03-CChronicle.pdf", COORDS_C),
        ]
        groups = group_variants(results)

        assert len(groups) == 1
        assert len(groups[0].results) == 3
        assert groups[0].first_scenario == "5-01"

    def test_two_variants(self) -> None:
        """PDFs with large coordinate differences split into two groups."""
        results = [
            _make_result("4-01-AChronicle.pdf", COORDS_A),
            _make_result("4-02-BChronicle.pdf", COORDS_B),
            _make_result("4-09-CChronicle.pdf", COORDS_FAR),
            _make_result("4-10-DChronicle.pdf", COORDS_FAR),
        ]
        groups = group_variants(results)

        assert len(groups) == 2
        assert len(groups[0].results) == 2
        assert len(groups[1].results) == 2
        assert groups[0].first_scenario == "4-01"
        assert groups[1].first_scenario == "4-09"

    def test_single_pdf(self) -> None:
        """Single PDF produces one group."""
        results = [_make_result("5-01-TestChronicle.pdf", COORDS_A)]
        groups = group_variants(results)

        assert len(groups) == 1
        assert len(groups[0].results) == 1
        assert groups[0].consensus.main == COORDS_A

    def test_three_variants(self) -> None:
        """Three distinct layout groups are detected."""
        far2 = CanvasCoordinates(x=60.0, y=70.0, x2=90.0, y2=99.0)
        results = [
            _make_result("4-01-A.pdf", COORDS_A),
            _make_result("4-05-B.pdf", COORDS_FAR),
            _make_result("4-10-C.pdf", far2),
        ]
        groups = group_variants(results)

        assert len(groups) == 3

    def test_consensus_computed_per_group(self) -> None:
        """Each group has its own consensus, not the global one."""
        results = [
            _make_result("4-01-A.pdf", COORDS_A),
            _make_result("4-02-B.pdf", COORDS_B),
            _make_result("4-09-C.pdf", COORDS_FAR),
        ]
        groups = group_variants(results)

        assert len(groups) == 2
        # Group 1 consensus should be median of A and B
        g1_consensus = groups[0].consensus.main
        assert g1_consensus is not None
        assert g1_consensus.x == pytest.approx((COORDS_A.x + COORDS_B.x) / 2)
        # Group 2 consensus should be COORDS_FAR itself
        assert groups[1].consensus.main == COORDS_FAR

    def test_custom_threshold(self) -> None:
        """Custom threshold changes split behavior."""
        # With a very large threshold, everything stays in one group
        results = [
            _make_result("4-01-A.pdf", COORDS_A),
            _make_result("4-09-B.pdf", COORDS_FAR),
        ]
        groups = group_variants(results, threshold=100.0)
        assert len(groups) == 1

        # With a tiny threshold, each PDF is its own group
        groups = group_variants(results, threshold=0.1)
        assert len(groups) == 2

    def test_scenario_id_extraction_quest(self) -> None:
        """Quest filenames extract Q-prefixed scenario IDs."""
        results = [
            _make_result("Q14-TheSwordlordChronicle.pdf", COORDS_A),
        ]
        groups = group_variants(results)
        assert groups[0].first_scenario == "Q14"
