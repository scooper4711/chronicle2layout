"""Unit tests for scenario_download_workflow.routing.

Tests concrete examples and edge cases for compute_routing_paths
across both game systems and all season types (positive, quest, bounty).
"""

from pathlib import Path

from chronicle_extractor.parser import ScenarioInfo
from scenario_download_workflow.detection import GameSystem
from scenario_download_workflow.routing import RoutingPaths, compute_routing_paths

_ROOT = Path("/project")
_CHRONICLES_BASE = _ROOT / "modules/pfs-chronicle-generator/assets/chronicles"
_LAYOUTS_BASE = _ROOT / "modules/pfs-chronicle-generator/assets/layouts"


class TestPfsSeasonScenario:
    """PFS season 7 scenario routing."""

    def test_scenarios_dir(self) -> None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.scenarios_dir == _ROOT / "Scenarios/PFS/Season 7"

    def test_chronicles_dir(self) -> None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.chronicles_dir == _CHRONICLES_BASE / "pfs2/season7"

    def test_layouts_dir(self) -> None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.layouts_dir == _LAYOUTS_BASE

    def test_layouts_system_dir(self) -> None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.layouts_system_dir == _LAYOUTS_BASE / "pfs2"

    def test_blueprints_dir(self) -> None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.blueprints_dir == _ROOT / "Blueprints"

    def test_blueprint_id(self) -> None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.blueprint_id == "pfs2.s7-06"

    def test_layout_id(self) -> None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.layout_id == "pfs2.s7-06"

    def test_system_prefix(self) -> None:
        info = ScenarioInfo(season=7, scenario="06", name="Siege of Gallowspire")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.system_prefix == "pfs2"


class TestSfsSeasonScenario:
    """SFS season 1 scenario routing."""

    def test_scenarios_dir(self) -> None:
        info = ScenarioInfo(season=1, scenario="01", name="The Commencement")
        routes = compute_routing_paths(_ROOT, GameSystem.SFS, info)
        assert routes.scenarios_dir == _ROOT / "Scenarios/SFS/Season 1"

    def test_chronicles_dir(self) -> None:
        info = ScenarioInfo(season=1, scenario="01", name="The Commencement")
        routes = compute_routing_paths(_ROOT, GameSystem.SFS, info)
        assert routes.chronicles_dir == _CHRONICLES_BASE / "sfs2/season1"

    def test_ids(self) -> None:
        info = ScenarioInfo(season=1, scenario="01", name="The Commencement")
        routes = compute_routing_paths(_ROOT, GameSystem.SFS, info)
        assert routes.blueprint_id == "sfs2.s1-01"
        assert routes.layout_id == "sfs2.s1-01"

    def test_system_prefix(self) -> None:
        info = ScenarioInfo(season=1, scenario="01", name="The Commencement")
        routes = compute_routing_paths(_ROOT, GameSystem.SFS, info)
        assert routes.system_prefix == "sfs2"

    def test_layouts_system_dir(self) -> None:
        info = ScenarioInfo(season=1, scenario="01", name="The Commencement")
        routes = compute_routing_paths(_ROOT, GameSystem.SFS, info)
        assert routes.layouts_system_dir == _LAYOUTS_BASE / "sfs2"


class TestQuestRouting:
    """Quest (season=0) routing."""

    def test_scenarios_dir(self) -> None:
        info = ScenarioInfo(season=0, scenario="14", name="The Silverhex Chronicles")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.scenarios_dir == _ROOT / "Scenarios/PFS/Quests"

    def test_chronicles_dir(self) -> None:
        info = ScenarioInfo(season=0, scenario="14", name="The Silverhex Chronicles")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.chronicles_dir == _CHRONICLES_BASE / "pfs2/quests"

    def test_ids(self) -> None:
        info = ScenarioInfo(season=0, scenario="14", name="The Silverhex Chronicles")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.blueprint_id == "pfs2.q14"
        assert routes.layout_id == "pfs2.q14"


class TestBountyRouting:
    """Bounty (season=-1) routing."""

    def test_scenarios_dir(self) -> None:
        info = ScenarioInfo(season=-1, scenario="13", name="Blood of the Beautiful")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.scenarios_dir == _ROOT / "Scenarios/PFS/Bounties"

    def test_chronicles_dir(self) -> None:
        info = ScenarioInfo(season=-1, scenario="13", name="Blood of the Beautiful")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.chronicles_dir == _CHRONICLES_BASE / "pfs2/bounties"

    def test_ids(self) -> None:
        info = ScenarioInfo(season=-1, scenario="13", name="Blood of the Beautiful")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        assert routes.blueprint_id == "pfs2.b13"
        assert routes.layout_id == "pfs2.b13"


class TestRoutingPathsFrozen:
    """Verify RoutingPaths is immutable."""

    def test_frozen(self) -> None:
        info = ScenarioInfo(season=1, scenario="01", name="Test")
        routes = compute_routing_paths(_ROOT, GameSystem.PFS, info)
        try:
            routes.system_prefix = "changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass
