"""Property-based tests for chronicle_extractor.parser.

Uses hypothesis to verify universal properties of scenario info
extraction across randomly generated inputs.
"""

from hypothesis import given
from hypothesis import strategies as st

from chronicle_extractor.parser import extract_scenario_name, extract_scenario_number


_season = st.integers(min_value=1, max_value=99)
_scenario_number = st.integers(min_value=0, max_value=99).map(lambda n: f"{n:02d}")

# Scenario names: printable, no newlines, not starting with noise prefixes
_name_chars = st.characters(
    whitelist_categories=("L", "N", "P", "S"),
    blacklist_characters="\n\r",
)
_scenario_name = (
    st.text(_name_chars, min_size=1, max_size=50)
    .map(str.strip)
    .filter(lambda s: len(s) > 0)
    .filter(lambda s: not s.lower().startswith(("by ", "pathfinder society")))
)


# Feature: chronicle-extractor, Property 3: Scenario number extraction round trip
@given(season=_season, scenario=_scenario_number)
def test_scenario_number_round_trip(season: int, scenario: str) -> None:
    """Embedding #X-YY in text and extracting returns original values.

    Validates: Requirements 3.1, 3.2
    """
    text = f"PATHFINDER SOCIETY SCENARIO #{season}-{scenario}\t\n"
    result = extract_scenario_number(text)
    assert result is not None
    assert result[0] == season
    assert result[1] == scenario


# Feature: chronicle-extractor, Property 4: No-match returns None
@given(
    text=st.text(
        st.characters(blacklist_characters="#"),
        min_size=0,
        max_size=200,
    )
)
def test_no_match_returns_none(text: str) -> None:
    """Text without # yields None from extract_scenario_number.

    Validates: Requirements 3.4
    """
    assert extract_scenario_number(text) is None


# Feature: chronicle-extractor, Property 3b: Scenario name extraction round trip
@given(name=_scenario_name)
def test_scenario_name_round_trip(name: str) -> None:
    """Common header lines across two pages yield the scenario name.

    Validates: Requirements 3.3
    """
    page_a = f"3\nPathfinder Society Scenario\n{name}\nBy Author\n"
    page_b = f"4\nPathfinder Society Scenario\n{name}\nSome body text\n"
    result = extract_scenario_name(page_a, page_b)
    assert result == name
