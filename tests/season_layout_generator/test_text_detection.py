"""Unit tests for text-based region detection.

Tests extract_text_regions against real chronicle PDFs from the
Chronicles/ directory. Verifies that expected canvas regions are
detected (non-None) and that returned coordinates are valid
percentage-based values.

Requirements: season-layout-generator 17.1, 17.2, 17.3, 17.4,
    17.5, 17.6, 17.7, 17.8
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from season_layout_generator.models import CanvasCoordinates
from season_layout_generator.text_detection import extract_text_regions

# Base path for chronicle PDFs, relative to the project root.
_CHRONICLES_DIR = Path("Chronicles/pfs")

# Regions expected on all Season 5+ chronicles.
_SEASON5_EXPECTED_REGIONS: list[str] = [
    "player_info",
    "summary",
    "rewards",
    "session_info",
    "notes",
    "items",
    "boons",
    "reputation",
]

# Regions expected on all chronicles regardless of season.
_UNIVERSAL_REGIONS: list[str] = [
    "player_info",
    "summary",
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
    """Verify extract_text_regions returns the expected dict structure."""

    @pytest.fixture()
    def season5_regions(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = _CHRONICLES_DIR / "Season 5" / "5-08-ProtectingtheFirelightChronicle.pdf"
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_text_regions(page)
        finally:
            doc.close()

    def test_returns_dict(self, season5_regions: dict[str, CanvasCoordinates | None]) -> None:
        assert isinstance(season5_regions, dict)

    def test_contains_all_region_keys(
        self, season5_regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        expected_keys = {
            "player_info", "summary", "rewards", "session_info",
            "notes", "items", "boons", "reputation",
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
    """Verify text detection on Season 5 chronicles (modern layout).

    Season 5+ chronicles use a consistent template where all eight
    regions should be detectable via text labels.
    """

    @pytest.fixture()
    def regions_5_08(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = _CHRONICLES_DIR / "Season 5" / "5-08-ProtectingtheFirelightChronicle.pdf"
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_text_regions(page)
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
            return extract_text_regions(page)
        finally:
            doc.close()

    @pytest.mark.parametrize("region", _SEASON5_EXPECTED_REGIONS)
    def test_all_regions_detected_5_08(
        self,
        regions_5_08: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        assert regions_5_08[region] is not None, (
            f"Region '{region}' not detected in 5-08"
        )

    @pytest.mark.parametrize("region", _SEASON5_EXPECTED_REGIONS)
    def test_all_regions_detected_5_01(
        self,
        regions_5_01: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        assert regions_5_01[region] is not None, (
            f"Region '{region}' not detected in 5-01"
        )

    @pytest.mark.parametrize("region", _SEASON5_EXPECTED_REGIONS)
    def test_coordinates_valid_5_08(
        self,
        regions_5_08: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        coords = regions_5_08[region]
        assert coords is not None
        _assert_valid_coordinates(coords)


class TestSeason6Detection:
    """Verify text detection on Season 6 chronicles."""

    @pytest.fixture()
    def regions_6_01(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 6"
            / "6-01-YearofImmortalInfluenceChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_text_regions(page)
        finally:
            doc.close()

    @pytest.mark.parametrize("region", _SEASON5_EXPECTED_REGIONS)
    def test_all_regions_detected(
        self,
        regions_6_01: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        assert regions_6_01[region] is not None, (
            f"Region '{region}' not detected in 6-01"
        )

    @pytest.mark.parametrize("region", _SEASON5_EXPECTED_REGIONS)
    def test_coordinates_valid(
        self,
        regions_6_01: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        coords = regions_6_01[region]
        assert coords is not None
        _assert_valid_coordinates(coords)


class TestSeason1Detection:
    """Verify text detection on Season 1 chronicles (older layout).

    Season 1 uses an earlier template. Universal regions (player_info,
    summary, rewards, session_info) should still be detected.
    """

    @pytest.fixture()
    def regions_1_01(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = (
            _CHRONICLES_DIR / "Season 1"
            / "1-01-TheAbsalomInitiationChronicle.pdf"
        )
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_text_regions(page)
        finally:
            doc.close()

    @pytest.mark.parametrize("region", _UNIVERSAL_REGIONS)
    def test_universal_regions_detected(
        self,
        regions_1_01: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        assert regions_1_01[region] is not None, (
            f"Region '{region}' not detected in 1-01"
        )

    @pytest.mark.parametrize("region", _UNIVERSAL_REGIONS)
    def test_coordinates_valid(
        self,
        regions_1_01: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        coords = regions_1_01[region]
        assert coords is not None
        _assert_valid_coordinates(coords)


class TestBountyDetection:
    """Verify text detection on Bounty chronicles.

    Bounties may lack boons but should have other standard regions.
    """

    @pytest.fixture()
    def regions_b1(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = _CHRONICLES_DIR / "Bounties" / "B1-TheWhitefangWyrmChronicle.pdf"
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_text_regions(page)
        finally:
            doc.close()

    @pytest.mark.parametrize("region", _UNIVERSAL_REGIONS)
    def test_universal_regions_detected(
        self,
        regions_b1: dict[str, CanvasCoordinates | None],
        region: str,
    ) -> None:
        assert regions_b1[region] is not None, (
            f"Region '{region}' not detected in B1"
        )

    def test_boons_absent(
        self, regions_b1: dict[str, CanvasCoordinates | None],
    ) -> None:
        """Bounty B1 has no boons section."""
        assert regions_b1["boons"] is None


class TestCoordinateRanges:
    """Verify detected coordinates are spatially reasonable.

    Checks that regions occupy expected relative positions on the page
    (e.g., player_info near the top, session_info near the bottom).
    """

    @pytest.fixture()
    def regions(self) -> dict[str, CanvasCoordinates | None]:
        pdf_path = _CHRONICLES_DIR / "Season 5" / "5-08-ProtectingtheFirelightChronicle.pdf"
        page, doc = _open_first_page(pdf_path)
        try:
            return extract_text_regions(page)
        finally:
            doc.close()

    def test_player_info_near_top(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        coords = regions["player_info"]
        assert coords is not None
        assert coords.y < 25.0, "player_info should be in the top quarter"

    def test_session_info_near_bottom(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        coords = regions["session_info"]
        assert coords is not None
        assert coords.y > 75.0, "session_info should be in the bottom quarter"

    def test_summary_below_player_info(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        player = regions["player_info"]
        summary = regions["summary"]
        assert player is not None and summary is not None
        assert summary.y > player.y, "summary should be below player_info"

    def test_rewards_on_right_side(
        self, regions: dict[str, CanvasCoordinates | None],
    ) -> None:
        coords = regions["rewards"]
        assert coords is not None
        assert coords.x > 50.0, "rewards should be on the right half of the page"


class TestConsistencyAcrossSeason:
    """Verify that two PDFs from the same season produce similar regions.

    Text detection should find the same set of regions for chronicles
    within the same season, since they share a template.
    """

    def test_same_regions_detected(self) -> None:
        pdf_a = _CHRONICLES_DIR / "Season 5" / "5-08-ProtectingtheFirelightChronicle.pdf"
        pdf_b = (
            _CHRONICLES_DIR / "Season 5"
            / "5-01-IntroYearofUnfetteredExplorationChronicle.pdf"
        )

        page_a, doc_a = _open_first_page(pdf_a)
        page_b, doc_b = _open_first_page(pdf_b)
        try:
            regions_a = extract_text_regions(page_a)
            regions_b = extract_text_regions(page_b)
        finally:
            doc_a.close()
            doc_b.close()

        detected_a = {k for k, v in regions_a.items() if v is not None}
        detected_b = {k for k, v in regions_b.items() if v is not None}
        assert detected_a == detected_b, (
            f"Detected regions differ: {detected_a} vs {detected_b}"
        )
