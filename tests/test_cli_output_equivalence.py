"""Property 2: CLI output equivalence after refactoring.

Verifies that the refactored code produces identical JSON output to the
original implementation by comparing against golden fixture files generated
from the pre-refactor code.

Each fixture covers a different season and layout variant:
  - s5-07: Season 5 scenario with items + checkboxes
  - s6-06: Season 6 scenario with items + checkboxes
  - s7-03: Season 7 scenario with no items (empty chronicle)
  - s7-04: Season 7 scenario with items only (no checkboxes)

Validates: Requirements 2.6
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from layout_generator import generate_layout_json
from shared_utils import find_layout_file, transform_canvas_coordinates

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LAYOUTS_DIR = str(PROJECT_ROOT / "layouts")


def _resolve_regions(
    parent_id: str,
    item_canvas: str = "items",
    checkbox_canvas: str = "summary",
) -> tuple[Optional[list[float]], Optional[list[float]]]:
    """Resolve item and checkbox regions from a parent layout file."""
    try:
        layout_path = find_layout_file(LAYOUTS_DIR, parent_id)
        with open(layout_path) as f:
            layout = json.load(f)
        region_pct = transform_canvas_coordinates(layout, item_canvas)
        checkbox_region_pct = transform_canvas_coordinates(layout, checkbox_canvas)
        return region_pct, checkbox_region_pct
    except (ValueError, KeyError):
        return None, None


# Each entry mirrors the CLI arguments that generate_layouts.py would use.
FIXTURE_CASES = [
    {
        "id": "s5-07",
        "pdf": "modules/pf2e-pfs05-year-of-unfettered-exploration/assets/chronicles-1/5-07-SewerDragonCrisisChronicle.pdf",
        "parent_id": "pfs2.season5",
        "scenario_id": "pfs2.s5-07",
        "description": "5-07 Sewer Dragon Crisis",
        "parent": "pfs2.season5",
        "default_chronicle": "modules/pf2e-pfs05-year-of-unfettered-exploration/assets/chronicles-1/5-07-SewerDragonCrisisChronicle.pdf",
    },
    {
        "id": "s6-06",
        "pdf": "modules/pf2e-pfs06-year-of-immortal-influence/assets/chronicles-1/6-06-RottenApples.pdf",
        "parent_id": "pfs2.season6",
        "scenario_id": "pfs2.s6-06",
        "description": "6-06 Rotten Apples",
        "parent": "pfs2.season6",
        "default_chronicle": "modules/pf2e-pfs06-year-of-immortal-influence/assets/chronicles-1/6-06-RottenApples.pdf",
    },
    {
        "id": "s7-03",
        "pdf": "modules/pf2e-pfs07-year-of-battles-spark/assets/chronicles-1/703-chronicle-AFootInTheDoor.pdf",
        "parent_id": "pfs2.season7",
        "scenario_id": "pfs2.s7-03",
        "description": "7-03 A Foot In The Door",
        "parent": "pfs2.season7",
        "default_chronicle": "modules/pf2e-pfs07-year-of-battles-spark/assets/chronicles-1/703-chronicle-AFootInTheDoor.pdf",
    },
    {
        "id": "s7-04",
        "pdf": "modules/pf2e-pfs07-year-of-battles-spark/assets/chronicles-1/704-chronicle-SulfuricNegotiations.pdf",
        "parent_id": "pfs2.season7",
        "scenario_id": "pfs2.s7-04",
        "description": "7-04 Sulfuric Negotiations",
        "parent": "pfs2.season7",
        "default_chronicle": "modules/pf2e-pfs07-year-of-battles-spark/assets/chronicles-1/704-chronicle-SulfuricNegotiations.pdf",
    },
]


class TestCLIOutputEquivalence:
    """Property 2: CLI output equivalence after refactoring.

    For each fixture PDF, the refactored generate_layout_json must produce
    JSON identical to the golden output captured from the original code.

    Requirements: refactor-chronicle2layout 2.6
    """

    @pytest.mark.parametrize(
        "case",
        FIXTURE_CASES,
        ids=[c["id"] for c in FIXTURE_CASES],
    )
    def test_output_matches_golden(self, case: dict) -> None:
        pdf_path = str(PROJECT_ROOT / case["pdf"])
        golden_path = GOLDEN_DIR / f"{case['id']}.json"

        if not Path(pdf_path).exists():
            pytest.skip(f"Fixture PDF not available: {case['pdf']}")
        if not golden_path.exists():
            pytest.skip(f"Golden file not available: {golden_path.name}")

        region_pct, checkbox_region_pct = _resolve_regions(case["parent_id"])

        result = generate_layout_json(
            pdf_path,
            region_pct=region_pct,
            layout_dir=LAYOUTS_DIR,
            parent_id=case["parent_id"],
            scenario_id=case["scenario_id"],
            description=case["description"],
            parent=case["parent"],
            checkbox_region_pct=checkbox_region_pct,
            default_chronicle_location=case["default_chronicle"],
        )

        with open(golden_path) as f:
            golden = json.load(f)

        assert result == golden, (
            f"Output for {case['id']} differs from golden file.\n"
            f"Got:\n{json.dumps(result, indent=2)[:500]}\n"
            f"Expected:\n{json.dumps(golden, indent=2)[:500]}"
        )
