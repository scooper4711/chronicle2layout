"""Property-based tests for scenario_download_workflow.routing.

Uses hypothesis to verify universal properties of directory routing
across randomly generated game systems and scenario metadata.
"""

import re
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from chronicle_extractor.parser import ScenarioInfo
from scenario_download_workflow.detection import GameSystem, system_prefix
from scenario_download_workflow.routing import compute_routing_paths

_ROOT = Path("/project")


@st.composite
def game_system_and_scenario_info(draw: st.DrawFn) -> tuple[GameSystem, ScenarioInfo]:
    """Generate a random GameSystem and ScenarioInfo.

    Season is drawn from three categories:
    - positive (1-20): regular season scenario
    - 0: quest
    - -1: bounty
    """
    system = draw(st.sampled_from(list(GameSystem)))
    season = draw(st.sampled_from([-1, 0]) | st.integers(min_value=1, max_value=20))
    scenario = draw(
        st.from_regex(r"[0-9]{1,3}", fullmatch=True).filter(lambda s: len(s) > 0)
    )
    name = draw(
        st.text(
            st.characters(min_codepoint=65, max_codepoint=122),
            min_size=1,
            max_size=40,
        )
    )
    return system, ScenarioInfo(season=season, scenario=scenario, name=name)


# Feature: scenario-download-workflow, Property 5: Directory routing uses correct system prefixes and season subdirectories
@given(data=game_system_and_scenario_info())
@settings(max_examples=200)
def test_routing_uses_correct_prefixes_and_subdirectories(
    data: tuple[GameSystem, ScenarioInfo],
) -> None:
    """For any game system and valid ScenarioInfo, compute_routing_paths
    produces paths where the scenarios dir uses the display name (PFS/SFS),
    the chronicles dir uses the system prefix (pfs2/sfs2), and IDs follow
    the correct pattern.

    Validates: Requirements 4.5, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
    """
    system, info = data
    routes = compute_routing_paths(_ROOT, system, info)

    prefix = system_prefix(system)
    display = "PFS" if system == GameSystem.PFS else "SFS"

    # System prefix is correct
    assert routes.system_prefix == prefix

    # Scenarios dir contains the display name
    scenarios_parts = routes.scenarios_dir.parts
    assert display in scenarios_parts, (
        f"Expected '{display}' in scenarios_dir parts: {scenarios_parts}"
    )

    # Chronicles dir contains the system prefix
    assert prefix in routes.chronicles_dir.parts, (
        f"Expected '{prefix}' in chronicles_dir parts: {routes.chronicles_dir.parts}"
    )

    # Season-specific subdirectory and ID pattern
    if info.season > 0:
        assert scenarios_parts[-1] == f"Season {info.season}"
        assert routes.chronicles_dir.name == f"season{info.season}"
        assert routes.blueprint_id == f"{prefix}.s{info.season}-{info.scenario}"
        assert routes.layout_id == f"{prefix}.s{info.season}-{info.scenario}"
    elif info.season == 0:
        assert scenarios_parts[-1] == "Quests"
        assert routes.chronicles_dir.name == "quests"
        assert routes.blueprint_id == f"{prefix}.q{info.scenario}"
        assert routes.layout_id == f"{prefix}.q{info.scenario}"
    else:
        assert scenarios_parts[-1] == "Bounties"
        assert routes.chronicles_dir.name == "bounties"
        assert routes.blueprint_id == f"{prefix}.b{info.scenario}"
        assert routes.layout_id == f"{prefix}.b{info.scenario}"

    # Blueprint and layout IDs always match
    assert routes.blueprint_id == routes.layout_id

    # Layouts dir is the root (not system-specific)
    assert routes.layouts_dir.name == "layouts"

    # Layouts system dir is layouts_dir / prefix
    assert routes.layouts_system_dir == routes.layouts_dir / prefix

    # Blueprints dir is always project_root / Blueprints
    assert routes.blueprints_dir == _ROOT / "Blueprints"
