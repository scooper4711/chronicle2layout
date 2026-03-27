"""Unit tests for scenario_renamer.filename.

Tests concrete examples and edge cases for subdirectory_for_season,
build_scenario_filename, sanitize_image_suffix, and build_image_filename.

Requirements: scenario-renamer 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 14.1, 14.2, 14.3
"""

from chronicle_extractor.parser import ScenarioInfo, _BOUNTY_SEASON

from scenario_renamer.filename import (
    build_image_filename,
    build_scenario_filename,
    sanitize_image_suffix,
    subdirectory_for_season,
)


class TestSubdirectoryForSeason:
    """Tests for subdirectory_for_season with various season numbers."""

    def test_season_1(self) -> None:
        assert subdirectory_for_season(1) == "Season 1"

    def test_season_5(self) -> None:
        assert subdirectory_for_season(5) == "Season 5"

    def test_quests(self) -> None:
        assert subdirectory_for_season(0) == "Quests"

    def test_bounties(self) -> None:
        assert subdirectory_for_season(_BOUNTY_SEASON) == "Bounties"


class TestBuildScenarioFilename:
    """Tests for build_scenario_filename with scenarios, quests, and bounties."""

    def test_season_1_scenario_01(self) -> None:
        info = ScenarioInfo(season=1, scenario="01", name="The Absalom Initiation")
        assert build_scenario_filename(info) == "1-01-TheAbsalomInitiation.pdf"

    def test_quest_14(self) -> None:
        info = ScenarioInfo(
            season=0, scenario="14", name="The Swordlord\u2019s Challenge"
        )
        assert build_scenario_filename(info) == "Q14-TheSwordlordsChallenge.pdf"

    def test_bounty_1(self) -> None:
        info = ScenarioInfo(
            season=_BOUNTY_SEASON, scenario="1", name="The Whitefang Wyrm"
        )
        assert build_scenario_filename(info) == "B1-TheWhitefangWyrm.pdf"


class TestSanitizeImageSuffix:
    """Tests for sanitize_image_suffix with various suffix strings."""

    def test_simple_word(self) -> None:
        assert sanitize_image_suffix("Maps") == "Maps"

    def test_hyphenated_with_spaces(self) -> None:
        assert sanitize_image_suffix("A-Nighttime Ambush") == "A-NighttimeAmbush"

    def test_word_with_space(self) -> None:
        assert sanitize_image_suffix("Map 1") == "Map1"

    def test_empty_string(self) -> None:
        assert sanitize_image_suffix("") == ""


class TestBuildImageFilename:
    """Tests for build_image_filename with concrete examples from the design."""

    def test_flooded_kings_court_maps(self) -> None:
        result = build_image_filename(1, "07", "FloodedKingsCourt", "Maps", "pdf")
        assert result == "1-07-FloodedKingsCourtMaps.pdf"

    def test_perilous_experiment_ambush(self) -> None:
        result = build_image_filename(
            4, "09", "PerilousExperiment", "A-NighttimeAmbush", "jpg"
        )
        assert result == "4-09-PerilousExperimentA-NighttimeAmbush.jpg"

    def test_catastrophes_spark_map(self) -> None:
        result = build_image_filename(
            2, "03", "CatastrophesSpark", "Map-1", "jpg"
        )
        assert result == "2-03-CatastrophesSparkMap-1.jpg"
