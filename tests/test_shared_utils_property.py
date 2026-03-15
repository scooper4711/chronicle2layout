"""Property-based tests for shared_utils.find_layout_file.

Uses Hypothesis to generate valid layout ID strings matching known patterns
and verifies that find_layout_file resolves each to the expected filesystem Path.

**Validates: Requirements 1.9**
"""

import shutil
import sys
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# Allow imports from the src/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from shared_utils import find_layout_file


# ---------------------------------------------------------------------------
# Hypothesis strategies for generating valid layout IDs
# ---------------------------------------------------------------------------

SYSTEMS = ["pfs2", "sf", "pfs1e"]
SEASON_NUMBERS = list(range(1, 10))
VARIANTS = ["a", "b", "c", "d"]
SCENARIO_NUMBERS = [f"{n:02d}" for n in range(1, 30)]


# ---------------------------------------------------------------------------
# Helpers to create the expected file on disk for each pattern
# ---------------------------------------------------------------------------

def _create_expected_file(path: Path) -> Path:
    """Create a file at the given path, including parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

class TestFindLayoutFileProperty:
    """Property 1: Layout file resolution equivalence.

    For any valid layout ID string, find_layout_file returns the expected Path.

    **Validates: Requirements 1.9**
    """

    @given(system=st.sampled_from(SYSTEMS))
    @settings(max_examples=100)
    def test_single_part_resolves_to_system_json(self, system: str) -> None:
        """Single-part IDs resolve to ``<layout_dir>/<system>/<system>.json``."""
        layout_dir = Path(tempfile.mkdtemp())
        try:
            expected = _create_expected_file(layout_dir / system / f"{system}.json")
            result = find_layout_file(str(layout_dir), system)
            assert result == expected
        finally:
            shutil.rmtree(layout_dir)

    @given(
        data=st.tuples(st.sampled_from(SYSTEMS), st.sampled_from(SEASON_NUMBERS))
    )
    @settings(max_examples=100)
    def test_season_parent_resolves_to_season_json(
        self, data: tuple[str, int]
    ) -> None:
        """Season parent IDs resolve to ``<layout_dir>/<sys>/s<N>/Season <N>.json``."""
        system, season_num = data
        layout_id = f"{system}.season{season_num}"
        layout_dir = Path(tempfile.mkdtemp())
        try:
            expected = _create_expected_file(
                layout_dir / system / f"s{season_num}" / f"Season {season_num}.json"
            )
            result = find_layout_file(str(layout_dir), layout_id)
            assert result == expected
        finally:
            shutil.rmtree(layout_dir)

    @given(
        data=st.tuples(
            st.sampled_from(SYSTEMS),
            st.sampled_from(SEASON_NUMBERS),
            st.sampled_from(VARIANTS),
        )
    )
    @settings(max_examples=100)
    def test_season_variant_resolves_to_variant_json(
        self, data: tuple[str, int, str]
    ) -> None:
        """Season variant IDs resolve to ``<layout_dir>/<sys>/s<N>/Season<N><v>.json``."""
        system, season_num, variant = data
        layout_id = f"{system}.season{season_num}{variant}"
        layout_dir = Path(tempfile.mkdtemp())
        try:
            expected = _create_expected_file(
                layout_dir / system / f"s{season_num}" / f"Season{season_num}{variant}.json"
            )
            result = find_layout_file(str(layout_dir), layout_id)
            assert result == expected
        finally:
            shutil.rmtree(layout_dir)

    @given(
        data=st.tuples(
            st.sampled_from(SYSTEMS),
            st.sampled_from(SEASON_NUMBERS),
            st.sampled_from(VARIANTS),
        )
    )
    @settings(max_examples=100)
    def test_season_variant_prefers_generated_json(
        self, data: tuple[str, int, str]
    ) -> None:
        """When ``.generated.json`` exists, season variant IDs prefer it over ``.json``."""
        system, season_num, variant = data
        layout_id = f"{system}.season{season_num}{variant}"
        layout_dir = Path(tempfile.mkdtemp())
        try:
            # Create both the regular and generated files
            _create_expected_file(
                layout_dir / system / f"s{season_num}" / f"Season{season_num}{variant}.json"
            )
            generated = _create_expected_file(
                layout_dir / system / f"s{season_num}"
                / f"Season{season_num}{variant}.generated.json"
            )
            result = find_layout_file(str(layout_dir), layout_id)
            assert result == generated
        finally:
            shutil.rmtree(layout_dir)

    @given(
        data=st.tuples(
            st.sampled_from(SYSTEMS),
            st.sampled_from(SEASON_NUMBERS),
            st.sampled_from(SCENARIO_NUMBERS),
        )
    )
    @settings(max_examples=100)
    def test_scenario_resolves_to_scenario_json(
        self, data: tuple[str, int, str]
    ) -> None:
        """Scenario IDs resolve to ``<layout_dir>/<sys>/s<N>/s<N>-<NN>.json``."""
        system, season_num, scenario_num = data
        layout_id = f"{system}.s{season_num}-{scenario_num}"
        layout_dir = Path(tempfile.mkdtemp())
        try:
            expected = _create_expected_file(
                layout_dir / system / f"s{season_num}" / f"s{season_num}-{scenario_num}.json"
            )
            result = find_layout_file(str(layout_dir), layout_id)
            assert result == expected
        finally:
            shutil.rmtree(layout_dir)
