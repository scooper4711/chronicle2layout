"""Unit tests for image-based region detection.

Tests extract_image_regions against real chronicle PDFs from the
Chronicles/ directory. Verifies that black bar detection finds
Summary and Items top edges, that grey background detection finds
the Session Info region, and that thick border detection finds the
Rewards boundaries.

Requirements: season-layout-generator 16.1, 16.2, 16.3, 16.4, 16.5
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from season_layout_generator.image_detection import extract_image_regions
from season_layout_generator.models import CanvasCoordinates

# Base path for chronicle PDFs, relative to the project root.
_CHRONICLES_DIR = Path("Chronicles/pfs")

# Regions that image detection should find on Season 5+ chronicles.
_SEASON5_IMAGE_REGIONS: list[str] = [
    "summary",
    "items",
    "rewards",
    "session_info",
]


def _open_first_page(pdf_path: Path) -> tuple[fitz.Page, fitz.Document]:
    """Open a PDF and return its first page and document handle."""
    doc = fitz.open(str(pdf_path))
    return doc[0], doc


def _assert_valid_coordinates(coords: CanvasCoordinates) -> None:
    """Assert that coordinates are valid percentages with x < x2, y < y2."""
    assert 0.0 <= coords.x <= 100.0, f"x={coords.x} out of range"
    assert 0.0 <= coords.y <= 100.0, f"y={coords.y} out of range"
    assert 0.0 <= coords.x2 <= 100.0, f"x2={coords.x2} out of range"
    assert 0.0 <= coords.y2 <= 100.0, f"y2={coords.y2} out of range"
    assert coords.x < coords.x2, f"x={coords.x} >= x2={coords.x2}"
    assert coords.y < coords.y2, f"y={coords.y} >= y2={coords.y2}"


class TestReturnStructure:
    """Verify extract_image_regions returns the expected dict structure."""

    @pytest.fixture()
    def season5_regions(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 5"
            / "5-08-ProtectingtheFirelightChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    def test_returns_dict(
        self, season5_regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        assert isinstance(season5_regions, dict)

    def test_contains_expected_keys(
        self, season5_regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        expected_keys = {
            "summary", "items", "rewards", "session_info", "notes",
        }
        assert set(season5_regions.keys()) == expected_keys

    def test_detected_values_are_canvas_coordinates(
        self, season5_regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        for name, coords in season5_regions.items():
            if coords is not None:
                assert isinstance(coords, CanvasCoordinates), (
                    f"{name} should be CanvasCoordinates, got {type(coords)}"
                )


class TestSeason5Detection:
    """Verify image detection on Season 5 chronicles.

    Season 5 chronicles have a consistent layout with black bars
    for summary and items, a vertical border for rewards, and a
    grey background for session info.
    """

    @pytest.fixture()
    def regions_5_08(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 5"
            / "5-08-ProtectingtheFirelightChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    @pytest.fixture()
    def regions_5_01(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 5"
            / "5-01-IntroYearofUnfetteredExplorationChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    @pytest.mark.parametrize("region", _SEASON5_IMAGE_REGIONS)
    def test_all_regions_detected_5_08(
        self,
        regions_5_08: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        assert regions_5_08[region] is not None, (
            f"Region '{region}' not detected in 5-08"
        )

    @pytest.mark.parametrize("region", _SEASON5_IMAGE_REGIONS)
    def test_all_regions_detected_5_01(
        self,
        regions_5_01: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        assert regions_5_01[region] is not None, (
            f"Region '{region}' not detected in 5-01"
        )

    @pytest.mark.parametrize("region", _SEASON5_IMAGE_REGIONS)
    def test_coordinates_valid_5_08(
        self,
        regions_5_08: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        coords = regions_5_08[region]
        assert coords is not None
        _assert_valid_coordinates(coords)


class TestSeason6Detection:
    """Verify image detection on Season 6 chronicles."""

    @pytest.fixture()
    def regions_6_01(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 6"
            / "6-01-YearofImmortalInfluenceChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    @pytest.mark.parametrize("region", _SEASON5_IMAGE_REGIONS)
    def test_all_regions_detected(
        self,
        regions_6_01: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        assert regions_6_01[region] is not None, (
            f"Region '{region}' not detected in 6-01"
        )

    @pytest.mark.parametrize("region", _SEASON5_IMAGE_REGIONS)
    def test_coordinates_valid(
        self,
        regions_6_01: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        coords = regions_6_01[region]
        assert coords is not None
        _assert_valid_coordinates(coords)


class TestSeason1Detection:
    """Verify image detection on Season 1 chronicles (older layout).

    Season 1 uses an earlier template but still has black bars and
    a grey session info region. The rewards box should also be
    detected via vertical borders.
    """

    @pytest.fixture()
    def regions_1_01(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 1"
            / "1-01-TheAbsalomInitiationChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    def test_summary_detected(
        self, regions_1_01: dict[str, CanvasCoordinates | None],
    ) -> None:
        assert regions_1_01["summary"] is not None

    def test_session_info_detected(
        self, regions_1_01: dict[str, CanvasCoordinates | None],
    ) -> None:
        assert regions_1_01["session_info"] is not None

    def test_rewards_detected(
        self, regions_1_01: dict[str, CanvasCoordinates | None],
    ) -> None:
        assert regions_1_01["rewards"] is not None

    def test_items_detected(
        self, regions_1_01: dict[str, CanvasCoordinates | None],
    ) -> None:
        assert regions_1_01["items"] is not None

    def test_coordinates_valid(
        self, regions_1_01: dict[str, CanvasCoordinates | None],
    ) -> None:
        for name, coords in regions_1_01.items():
            if coords is not None:
                _assert_valid_coordinates(coords)


class TestBountyDetection:
    """Verify image detection on Bounty chronicles.

    Bounties have a different layout — they may lack a separate
    items bar but should still detect summary and session info.
    """

    @pytest.fixture()
    def regions_b1(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Bounties"
            / "B1-TheWhitefangWyrmChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    def test_summary_detected(
        self, regions_b1: dict[str, CanvasCoordinates | None],
    ) -> None:
        assert regions_b1["summary"] is not None

    def test_session_info_detected(
        self, regions_b1: dict[str, CanvasCoordinates | None],
    ) -> None:
        assert regions_b1["session_info"] is not None

    def test_coordinates_valid(
        self, regions_b1: dict[str, CanvasCoordinates | None],
    ) -> None:
        for name, coords in regions_b1.items():
            if coords is not None:
                _assert_valid_coordinates(coords)


class TestBlackBarDetection:
    """Verify that black bar detection finds Summary and Items top edges.

    Requirements: season-layout-generator 16.2, 16.3
    """

    @pytest.fixture()
    def regions(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 5"
            / "5-08-ProtectingtheFirelightChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    def test_summary_top_in_upper_quarter(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Summary bar should be in the upper portion of the page."""
        summary = regions["summary"]
        assert summary is not None
        assert summary.y < 25.0, (
            f"Summary top at {summary.y}% is too low"
        )

    def test_items_top_in_middle(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Items bar should be roughly in the middle of the page."""
        items = regions["items"]
        assert items is not None
        assert 40.0 < items.y < 65.0, (
            f"Items top at {items.y}% is not in the expected range"
        )

    def test_summary_above_items(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Summary region should be above the items region."""
        summary = regions["summary"]
        items = regions["items"]
        assert summary is not None and items is not None
        assert summary.y < items.y

    def test_items_right_edge_at_rewards_border(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Items right edge should align with the notes left edge or rewards."""
        items = regions["items"]
        notes = regions["notes"]
        assert items is not None and notes is not None
        assert abs(items.x2 - notes.x) < 2.0, (
            f"Items x2={items.x2:.1f} should be near notes x={notes.x:.1f}"
        )


class TestGreyBackgroundDetection:
    """Verify that grey background detection finds Session Info.

    Requirements: season-layout-generator 16.4
    """

    @pytest.fixture()
    def regions(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 5"
            / "5-08-ProtectingtheFirelightChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    def test_session_info_in_bottom_portion(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Session info grey region should be near the bottom."""
        session = regions["session_info"]
        assert session is not None
        assert session.y > 85.0, (
            f"Session info top at {session.y}% is too high"
        )

    def test_session_info_spans_page_width(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Session info should span most of the page width."""
        session = regions["session_info"]
        assert session is not None
        width = session.x2 - session.x
        assert width > 80.0, (
            f"Session info width {width:.1f}% is too narrow"
        )


class TestRewardsBorderDetection:
    """Verify that thick border detection finds Rewards boundaries.

    Requirements: season-layout-generator 16.3
    """

    @pytest.fixture()
    def regions(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 5"
            / "5-08-ProtectingtheFirelightChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_image_regions(page)
        finally:
            doc.close()

    def test_rewards_on_right_side(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Rewards box should be on the right side of the page."""
        rewards = regions["rewards"]
        assert rewards is not None
        assert rewards.x > 50.0, (
            f"Rewards left edge at {rewards.x}% is not on the right"
        )

    def test_rewards_right_edge_near_page_edge(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Rewards right edge should be near the right page margin."""
        rewards = regions["rewards"]
        assert rewards is not None
        assert rewards.x2 > 85.0, (
            f"Rewards right edge at {rewards.x2}% is too far from edge"
        )

    def test_rewards_spans_vertically(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Rewards box should have significant vertical extent."""
        rewards = regions["rewards"]
        assert rewards is not None
        height = rewards.y2 - rewards.y
        assert height > 20.0, (
            f"Rewards height {height:.1f}% is too short"
        )


class TestConsistencyAcrossSeason:
    """Verify that two PDFs from the same season produce similar regions."""

    def test_same_regions_detected(self) -> None:
        pdf_a = (
            _CHRONICLES_DIR / "Season 5"
            / "5-08-ProtectingtheFirelightChronicle.pdf"
        )
        pdf_b = (
            _CHRONICLES_DIR / "Season 5"
            / "5-01-IntroYearofUnfetteredExplorationChronicle.pdf"
        )

        page_a, doc_a = _open_first_page(pdf_a)
        page_b, doc_b = _open_first_page(pdf_b)
        try:
            regions_a = extract_image_regions(page_a)
            regions_b = extract_image_regions(page_b)
        finally:
            doc_a.close()
            doc_b.close()

        detected_a = {k for k, v in regions_a.items() if v is not None}
        detected_b = {k for k, v in regions_b.items() if v is not None}
        assert detected_a == detected_b, (
            f"Detected regions differ: {detected_a} vs {detected_b}"
        )

    def test_coordinates_close_within_season(self) -> None:
        """Coordinates should be very similar for PDFs in the same season."""
        pdf_a = (
            _CHRONICLES_DIR / "Season 5"
            / "5-08-ProtectingtheFirelightChronicle.pdf"
        )
        pdf_b = (
            _CHRONICLES_DIR / "Season 5"
            / "5-03-HeidmarchHeistChronicle.pdf"
        )

        page_a, doc_a = _open_first_page(pdf_a)
        page_b, doc_b = _open_first_page(pdf_b)
        try:
            regions_a = extract_image_regions(page_a)
            regions_b = extract_image_regions(page_b)
        finally:
            doc_a.close()
            doc_b.close()

        tolerance = 2.0  # percentage points
        for name in _SEASON5_IMAGE_REGIONS:
            coords_a = regions_a[name]
            coords_b = regions_b[name]
            assert coords_a is not None and coords_b is not None, (
                f"Region '{name}' missing in one PDF"
            )
            assert abs(coords_a.x - coords_b.x) < tolerance, (
                f"{name}.x differs: {coords_a.x:.1f} vs {coords_b.x:.1f}"
            )
            assert abs(coords_a.y - coords_b.y) < tolerance, (
                f"{name}.y differs: {coords_a.y:.1f} vs {coords_b.y:.1f}"
            )
            assert abs(coords_a.x2 - coords_b.x2) < tolerance, (
                f"{name}.x2 differs: {coords_a.x2:.1f} vs {coords_b.x2:.1f}"
            )
            assert abs(coords_a.y2 - coords_b.y2) < tolerance, (
                f"{name}.y2 differs: {coords_a.y2:.1f} vs {coords_b.y2:.1f}"
            )

