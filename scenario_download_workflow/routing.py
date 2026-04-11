"""Directory routing for scenario download workflow.

Computes all output directory paths and IDs for a single scenario
based on its game system and parsed metadata. Handles season
subdirectories, quest routing (season=0), and bounty routing
(season=-1).
"""

from dataclasses import dataclass
from pathlib import Path

from chronicle_extractor.parser import ScenarioInfo, _BOUNTY_SEASON
from scenario_download_workflow.detection import GameSystem, system_prefix

_CHRONICLES_RELATIVE = Path("modules/pfs-chronicle-generator/assets/chronicles")
_LAYOUTS_RELATIVE = Path("modules/pfs-chronicle-generator/assets/layouts")
_BLUEPRINTS_RELATIVE = Path("Blueprints")
_SCENARIOS_RELATIVE = Path("Scenarios")

_DISPLAY_NAMES = {
    GameSystem.PFS: "PFS",
    GameSystem.SFS: "SFS",
}


@dataclass(frozen=True)
class RoutingPaths:
    """All output directory paths for a single scenario."""

    scenarios_dir: Path
    chronicles_dir: Path
    layouts_dir: Path
    layouts_system_dir: Path
    blueprints_dir: Path
    blueprint_id: str
    layout_id: str
    system_prefix: str


def compute_routing_paths(
    project_root: Path,
    system: GameSystem,
    info: ScenarioInfo,
) -> RoutingPaths:
    """Compute all output paths for a scenario based on game system and metadata.

    Handles season subdirectories, quest (season=0) routing to quests/,
    and bounty (season=-1) routing to bounties/.

    Args:
        project_root: The PFS Tools project root directory.
        system: The detected game system (PFS or SFS).
        info: Parsed scenario metadata (season, scenario number, name).

    Returns:
        A RoutingPaths with all computed directories and IDs.
    """
    prefix = system_prefix(system)
    display = _DISPLAY_NAMES[system]

    if info.season == _BOUNTY_SEASON:
        season_subdir = "Bounties"
        chronicles_subdir = "bounties"
        scenario_id = f"{prefix}.b{info.scenario}"
    elif info.season == 0:
        season_subdir = "Quests"
        chronicles_subdir = "quests"
        scenario_id = f"{prefix}.q{info.scenario}"
    else:
        season_subdir = f"Season {info.season}"
        chronicles_subdir = f"season{info.season}"
        scenario_id = f"{prefix}.s{info.season}-{info.scenario}"

    layouts_dir = project_root / _LAYOUTS_RELATIVE

    return RoutingPaths(
        scenarios_dir=project_root / _SCENARIOS_RELATIVE / display / season_subdir,
        chronicles_dir=project_root / _CHRONICLES_RELATIVE / prefix / chronicles_subdir,
        layouts_dir=layouts_dir,
        layouts_system_dir=layouts_dir / prefix,
        blueprints_dir=project_root / _BLUEPRINTS_RELATIVE,
        blueprint_id=scenario_id,
        layout_id=scenario_id,
        system_prefix=prefix,
    )
