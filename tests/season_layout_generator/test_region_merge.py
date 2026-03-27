"""Unit tests for region merging.

Tests the merge_regions function that combines text-based and
image-based region detections into final PageRegions with
coordinates relative to the main canvas.

Requirements: season-layout-generator 16.5
"""

import pytest

from season_layout_generator.models import CanvasCoordinates, PageRegions
from season_layout_generator.region_merge import (
    _clamp,
    _infer_main_canvas,
    _pick_region,
    _to_main_relative,
    merge_regions,
)

# Reusable coordinates for tests.
_TEXT_SUMMARY = CanvasCoordinates(x=10.0, y=20.0, x2=80.0, y2=35.0)
_IMAGE_SUMMARY = CanvasCoordinates(x=9.5, y=19.0, x2=81.0, y2=36.0)
_TEXT_PLAYER_INFO = CanvasCoordinates(x=10.0, y=5.0, x2=80.0, y2=15.0)
_TEXT_REWARDS = CanvasCoordinates(x=70.0, y=30.0, x2=90.0, y2=70.0)
_IMAGE_REWARDS = CanvasCoordinates(x=69.0, y=29.0, x2=91.0, y2=71.0)
_TEXT_SESSION_INFO = CanvasCoordinates(x=5.0, y=85.0, x2=95.0, y2=98.0)
_IMAGE_SESSION_INFO = CanvasCoordinates(x=4.0, y=84.0, x2=96.0, y2=99.0)
_TEXT_NOTES = CanvasCoordinates(x=10.0, y=50.0, x2=60.0, y2=80.0)
_TEXT_BOONS = CanvasCoordinates(x=10.0, y=40.0, x2=60.0, y2=48.0)
_TEXT_REPUTATION = CanvasCoordinates(x=10.0, y=82.0, x2=60.0, y2=84.0)
_TEXT_ITEMS = CanvasCoordinates(x=10.0, y=36.0, x2=60.0, y2=50.0)
_IMAGE_ITEMS = CanvasCoordinates(x=9.0, y=35.0, x2=61.0, y2=51.0)

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0


class TestPickRegion:
    """Tests for _pick_region selection logic."""

    def test_image_preferred_for_summary(self) -> None:
        text = {"summary": _TEXT_SUMMARY}
        image = {"summary": _IMAGE_SUMMARY}
        result = _pick_region("summary", text, image)
        assert result == _IMAGE_SUMMARY

    def test_image_preferred_for_rewards(self) -> None:
        text = {"rewards": _TEXT_REWARDS}
        image = {"rewards": _IMAGE_REWARDS}
        result = _pick_region("rewards", text, image)
        assert result == _IMAGE_REWARDS

    def test_image_preferred_for_items(self) -> None:
        text = {"items": _TEXT_ITEMS}
        image = {"items": _IMAGE_ITEMS}
        result = _pick_region("items", text, image)
        assert result == _IMAGE_ITEMS

    def test_image_preferred_for_session_info(self) -> None:
        text = {"session_info": _TEXT_SESSION_INFO}
        image = {"session_info": _IMAGE_SESSION_INFO}
        result = _pick_region("session_info", text, image)
        assert result == _IMAGE_SESSION_INFO

    def test_text_fallback_when_image_none(self) -> None:
        text = {"summary": _TEXT_SUMMARY}
        image = {"summary": None}
        result = _pick_region("summary", text, image)
        assert result == _TEXT_SUMMARY

    def test_text_fallback_when_image_missing(self) -> None:
        text = {"summary": _TEXT_SUMMARY}
        image: dict[str, CanvasCoordinates | None] = {}
        result = _pick_region("summary", text, image)
        assert result == _TEXT_SUMMARY

    def test_text_only_region_uses_text(self) -> None:
        text = {"player_info": _TEXT_PLAYER_INFO}
        image: dict[str, CanvasCoordinates | None] = {}
        result = _pick_region("player_info", text, image)
        assert result == _TEXT_PLAYER_INFO

    def test_text_only_region_ignores_image(self) -> None:
        """Text-only regions (player_info, notes, etc.) always use text."""
        fake_image = CanvasCoordinates(x=0, y=0, x2=50, y2=50)
        text = {"notes": _TEXT_NOTES}
        image = {"notes": fake_image}
        result = _pick_region("notes", text, image)
        assert result == _TEXT_NOTES

    def test_returns_none_when_both_missing(self) -> None:
        result = _pick_region(
            "reputation",
            {"reputation": None},
            {},
        )
        assert result is None


class TestInferMainCanvas:
    """Tests for _infer_main_canvas bounding box computation."""

    def test_single_region(self) -> None:
        text = {"player_info": _TEXT_PLAYER_INFO}
        image: dict[str, CanvasCoordinates | None] = {}
        main = _infer_main_canvas(text, image)
        assert main == _TEXT_PLAYER_INFO

    def test_multiple_regions_envelope(self) -> None:
        text = {
            "player_info": _TEXT_PLAYER_INFO,
            "session_info": _TEXT_SESSION_INFO,
        }
        image: dict[str, CanvasCoordinates | None] = {}
        main = _infer_main_canvas(text, image)
        assert main is not None
        assert main.x == pytest.approx(5.0)   # min x from session_info
        assert main.y == pytest.approx(5.0)   # min y from player_info
        assert main.x2 == pytest.approx(95.0)  # max x2 from session_info
        assert main.y2 == pytest.approx(98.0)  # max y2 from session_info

    def test_image_regions_included(self) -> None:
        text: dict[str, CanvasCoordinates | None] = {}
        image = {"summary": _IMAGE_SUMMARY}
        main = _infer_main_canvas(text, image)
        assert main == _IMAGE_SUMMARY

    def test_returns_none_when_no_regions(self) -> None:
        text: dict[str, CanvasCoordinates | None] = {}
        image: dict[str, CanvasCoordinates | None] = {}
        assert _infer_main_canvas(text, image) is None

    def test_returns_none_when_all_none(self) -> None:
        text = {"player_info": None, "notes": None}
        image = {"summary": None, "rewards": None}
        assert _infer_main_canvas(text, image) is None



class TestToMainRelative:
    """Tests for _to_main_relative coordinate conversion."""

    def test_identity_when_main_is_full_page(self) -> None:
        main = CanvasCoordinates(x=0, y=0, x2=100, y2=100)
        coords = CanvasCoordinates(x=10, y=20, x2=80, y2=90)
        result = _to_main_relative(coords, main)
        assert result == coords

    def test_scales_to_main_canvas(self) -> None:
        main = CanvasCoordinates(x=10, y=10, x2=90, y2=90)
        coords = CanvasCoordinates(x=10, y=10, x2=90, y2=90)
        result = _to_main_relative(coords, main)
        assert abs(result.x - 0.0) < 0.01
        assert abs(result.y - 0.0) < 0.01
        assert abs(result.x2 - 100.0) < 0.01
        assert abs(result.y2 - 100.0) < 0.01

    def test_midpoint_conversion(self) -> None:
        main = CanvasCoordinates(x=10, y=20, x2=90, y2=80)
        coords = CanvasCoordinates(x=50, y=50, x2=70, y2=60)
        result = _to_main_relative(coords, main)
        assert abs(result.x - 50.0) < 0.01
        assert abs(result.y - 50.0) < 0.01
        assert abs(result.x2 - 75.0) < 0.01
        assert abs(result.y2 - 66.67) < 0.01

    def test_clamps_to_valid_range(self) -> None:
        main = CanvasCoordinates(x=20, y=20, x2=80, y2=80)
        coords = CanvasCoordinates(x=10, y=10, x2=90, y2=90)
        result = _to_main_relative(coords, main)
        assert result.x == pytest.approx(0.0)
        assert result.y == pytest.approx(0.0)
        assert result.x2 == pytest.approx(100.0)
        assert result.y2 == pytest.approx(100.0)


class TestClamp:
    """Tests for _clamp helper."""

    def test_within_range(self) -> None:
        assert _clamp(50.0) == pytest.approx(50.0)

    def test_below_lower_bound(self) -> None:
        assert _clamp(-5.0) == pytest.approx(0.0)

    def test_above_upper_bound(self) -> None:
        assert _clamp(105.0) == pytest.approx(100.0)

    def test_at_boundaries(self) -> None:
        assert _clamp(0.0) == pytest.approx(0.0)
        assert _clamp(100.0) == pytest.approx(100.0)


class TestMergeRegions:
    """Tests for the main merge_regions function."""

    def test_both_sources_present(self) -> None:
        text = {
            "player_info": _TEXT_PLAYER_INFO,
            "summary": _TEXT_SUMMARY,
            "rewards": _TEXT_REWARDS,
            "session_info": _TEXT_SESSION_INFO,
            "notes": _TEXT_NOTES,
            "boons": _TEXT_BOONS,
            "reputation": _TEXT_REPUTATION,
            "items": _TEXT_ITEMS,
        }
        image = {
            "summary": _IMAGE_SUMMARY,
            "rewards": _IMAGE_REWARDS,
            "session_info": _IMAGE_SESSION_INFO,
            "items": _IMAGE_ITEMS,
        }
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)

        assert result.main is not None
        assert result.player_info is not None
        assert result.summary is not None
        assert result.rewards is not None
        assert result.items is not None
        assert result.notes is not None
        assert result.boons is not None
        assert result.reputation is not None
        assert result.session_info is not None

    def test_text_only_fallback(self) -> None:
        text = {
            "player_info": _TEXT_PLAYER_INFO,
            "summary": _TEXT_SUMMARY,
            "rewards": _TEXT_REWARDS,
            "session_info": _TEXT_SESSION_INFO,
        }
        image: dict[str, CanvasCoordinates | None] = {}
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)

        assert result.main is not None
        assert result.player_info is not None
        assert result.summary is not None
        assert result.rewards is not None
        assert result.session_info is not None

    def test_image_only_fallback(self) -> None:
        text: dict[str, CanvasCoordinates | None] = {}
        image = {
            "summary": _IMAGE_SUMMARY,
            "rewards": _IMAGE_REWARDS,
            "session_info": _IMAGE_SESSION_INFO,
            "items": _IMAGE_ITEMS,
        }
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)

        assert result.main is not None
        assert result.summary is not None
        assert result.rewards is not None
        assert result.session_info is not None
        assert result.items is not None
        # Text-only regions should be None.
        assert result.player_info is None
        assert result.notes is None
        assert result.boons is None
        assert result.reputation is None

    def test_missing_regions_are_none(self) -> None:
        text = {"player_info": _TEXT_PLAYER_INFO}
        image: dict[str, CanvasCoordinates | None] = {}
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)

        assert result.main is not None
        assert result.player_info is not None
        assert result.summary is None
        assert result.rewards is None
        assert result.notes is None

    def test_empty_inputs_return_empty_page_regions(self) -> None:
        result = merge_regions({}, {}, PAGE_WIDTH, PAGE_HEIGHT)
        assert result == PageRegions()

    def test_all_none_inputs_return_empty_page_regions(self) -> None:
        text = {"player_info": None, "summary": None}
        image = {"summary": None, "rewards": None}
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)
        assert result == PageRegions()

    def test_coordinates_within_valid_range(self) -> None:
        text = {
            "player_info": _TEXT_PLAYER_INFO,
            "summary": _TEXT_SUMMARY,
            "rewards": _TEXT_REWARDS,
            "session_info": _TEXT_SESSION_INFO,
            "notes": _TEXT_NOTES,
            "items": _TEXT_ITEMS,
        }
        image = {
            "summary": _IMAGE_SUMMARY,
            "items": _IMAGE_ITEMS,
        }
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)

        for name in (
            "player_info", "summary", "rewards",
            "items", "notes", "session_info",
        ):
            coords = getattr(result, name)
            assert coords is not None, f"{name} should be detected"
            assert 0.0 <= coords.x <= 100.0, f"{name}.x out of range"
            assert 0.0 <= coords.y <= 100.0, f"{name}.y out of range"
            assert 0.0 <= coords.x2 <= 100.0, f"{name}.x2 out of range"
            assert 0.0 <= coords.y2 <= 100.0, f"{name}.y2 out of range"
            assert coords.x < coords.x2, f"{name}: x >= x2"
            assert coords.y < coords.y2, f"{name}: y >= y2"

    def test_main_is_page_relative(self) -> None:
        """Main canvas coordinates should be in page-relative space."""
        text = {
            "player_info": _TEXT_PLAYER_INFO,
            "session_info": _TEXT_SESSION_INFO,
        }
        image: dict[str, CanvasCoordinates | None] = {}
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)

        assert result.main is not None
        # Main should envelope both regions in page space.
        assert result.main.x == pytest.approx(
            min(_TEXT_PLAYER_INFO.x, _TEXT_SESSION_INFO.x),
        )
        assert result.main.y == pytest.approx(
            min(_TEXT_PLAYER_INFO.y, _TEXT_SESSION_INFO.y),
        )
        assert result.main.x2 == pytest.approx(
            max(_TEXT_PLAYER_INFO.x2, _TEXT_SESSION_INFO.x2),
        )
        assert result.main.y2 == pytest.approx(
            max(_TEXT_PLAYER_INFO.y2, _TEXT_SESSION_INFO.y2),
        )

    def test_sub_regions_relative_to_main(self) -> None:
        """Sub-region coordinates should be relative to main canvas."""
        text = {
            "player_info": _TEXT_PLAYER_INFO,
            "session_info": _TEXT_SESSION_INFO,
        }
        image: dict[str, CanvasCoordinates | None] = {}
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)

        assert result.player_info is not None
        # Player info starts at the top of main, so y should be ~0.
        assert result.player_info.y < 1.0

        assert result.session_info is not None
        # Session info ends at the bottom of main, so y2 should be ~100.
        assert result.session_info.y2 > 99.0

    def test_reputation_absent_is_valid(self) -> None:
        """Reputation may be absent; merge should handle gracefully."""
        text = {"player_info": _TEXT_PLAYER_INFO}
        image: dict[str, CanvasCoordinates | None] = {}
        result = merge_regions(text, image, PAGE_WIDTH, PAGE_HEIGHT)
        assert result.reputation is None
