"""Unit tests for chronicle_extractor.parser.

Tests concrete examples and edge cases for ScenarioInfo dataclass,
extract_scenario_number, extract_scenario_name, and extract_scenario_info.
"""

from chronicle_extractor.parser import (
    ScenarioInfo,
    extract_scenario_info,
    extract_scenario_name,
    extract_scenario_number,
)


class TestScenarioInfo:
    """Tests for ScenarioInfo dataclass."""

    def test_frozen_dataclass(self) -> None:
        info = ScenarioInfo(season=1, scenario="07", name="Flooded King's Court")
        assert info.season == 1
        assert info.scenario == "07"
        assert info.name == "Flooded King's Court"

    def test_equality(self) -> None:
        a = ScenarioInfo(season=2, scenario="12", name="Test")
        b = ScenarioInfo(season=2, scenario="12", name="Test")
        assert a == b


class TestExtractScenarioNumber:
    """Tests for extract_scenario_number."""

    def test_standard_format(self) -> None:
        text = "PATHFINDER SOCIETY SCENARIO #1\u201307\t\n"
        result = extract_scenario_number(text)
        assert result == (1, "07")

    def test_regular_hyphen(self) -> None:
        result = extract_scenario_number("Scenario #2-03\t\n")
        assert result == (2, "03")

    def test_en_dash(self) -> None:
        result = extract_scenario_number("#1\u201307")
        assert result == (1, "07")

    def test_double_digit_season(self) -> None:
        result = extract_scenario_number("#12-01 Big Season")
        assert result == (12, "01")

    def test_no_match(self) -> None:
        assert extract_scenario_number("No scenario here") is None

    def test_empty_string(self) -> None:
        assert extract_scenario_number("") is None


class TestExtractScenarioName:
    """Tests for extract_scenario_name using common header lines."""

    def test_single_line_name(self) -> None:
        page_a = "3\nPathfinder Society Scenario\nTest Name\nBy Author\n"
        page_b = "4\nPathfinder Society Scenario\nTest Name\nSome body text\n"
        assert extract_scenario_name(page_a, page_b) == "Test Name"

    def test_multi_line_name(self) -> None:
        page_a = "3\nPathfinder Society Scenario\nBreaking the Storm:\nBastion in Embers\nWhere on Golarion?\n"
        page_b = "4\nPathfinder Society Scenario\nBreaking the Storm:\nBastion in Embers\nGetting Started\n"
        assert extract_scenario_name(page_a, page_b) == "Breaking the Storm: Bastion in Embers"

    def test_no_common_lines(self) -> None:
        page_a = "3\nPathfinder Society Scenario\nScenario Title\nWhere on Golarion?\n"
        page_b = "4\nPathfinder Society Scenario\nThe Real Name\nBody text\n"
        assert extract_scenario_name(page_a, page_b) is None

    def test_no_header_on_page(self) -> None:
        page_a = "3\nSome random text\n"
        page_b = "4\nPathfinder Society Scenario\nName\n"
        assert extract_scenario_name(page_a, page_b) is None

    def test_case_insensitive_header(self) -> None:
        page_a = "3\nPathFInder Society Scenario\nTest Name\nBy Author\n"
        page_b = "4\nPathFInder Society Scenario\nTest Name\nBody text\n"
        assert extract_scenario_name(page_a, page_b) == "Test Name"


class TestExtractScenarioInfo:
    """Tests for extract_scenario_info combining number and name."""

    def test_full_extraction(self) -> None:
        p1 = "PATHFINDER SOCIETY SCENARIO #1\u201307\t\n"
        p3 = "3\nPathfinder Society Scenario\nFlooded King's Court\nBy Author\n"
        p4 = "4\nPathfinder Society Scenario\nFlooded King's Court\nBody\n"
        result = extract_scenario_info(p1, p3, p4)
        assert result is not None
        assert result.season == 1
        assert result.scenario == "07"
        assert result.name == "Flooded King's Court"

    def test_fallback_to_pages_4_5(self) -> None:
        p1 = "Scenario #3-02\t\n"
        p3 = "3\nPathfinder Society Scenario\nScenario Title\nWhere\n"
        p4 = "4\nPathfinder Society Scenario\nThe East Hill Haunting\nVC\n"
        p5 = "5\nPathfinder Society Scenario\nThe East Hill Haunting\nEloise\n"
        result = extract_scenario_info(p1, p3, p4, p5)
        assert result is not None
        assert result.season == 3
        assert result.scenario == "02"
        assert result.name == "The East Hill Haunting"

    def test_no_scenario_number(self) -> None:
        assert extract_scenario_info("No number here") is None

    def test_no_name_pages(self) -> None:
        p1 = "#1-07 text"
        result = extract_scenario_info(p1)
        assert result is None
