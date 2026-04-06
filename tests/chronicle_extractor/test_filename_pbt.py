"""Property-based tests for chronicle_extractor.filename.

Uses hypothesis to verify universal properties of filename sanitization
and output path construction across randomly generated inputs.
"""

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from chronicle_extractor.filename import (
    UNSAFE_CHARACTERS,
    build_output_path,
    sanitize_name,
)
from chronicle_extractor.parser import ScenarioInfo

_UNSAFE_SET = set(UNSAFE_CHARACTERS)


# Feature: chronicle-extractor, Property 5: Sanitized name contains no unsafe characters or spaces
@given(name=st.text(min_size=0, max_size=100))
def test_sanitized_no_unsafe_chars(name: str) -> None:
    """sanitize_name output contains no spaces and no UNSAFE_CHARACTERS.

    Validates: Requirements 5.2, 5.3
    """
    result = sanitize_name(name)
    for ch in result:
        assert ch != " ", f"Space found in sanitized name: {result!r}"
        assert ch not in _UNSAFE_SET, (
            f"Unsafe character {ch!r} found in sanitized name: {result!r}"
        )


# Feature: chronicle-extractor, Property 6: Sanitized name preserves letter casing
@given(name=st.text(min_size=0, max_size=100))
def test_sanitized_preserves_casing(name: str) -> None:
    """Every alphabetic character in sanitize_name output appears in the input
    with the same casing and in the same relative order (subsequence).

    Validates: Requirements 5.4
    """
    result = sanitize_name(name)
    input_alphas = [ch for ch in name if ch.isalpha()]
    output_alphas = [ch for ch in result if ch.isalpha()]

    # Output letters must be a subsequence of input letters with same casing
    it = iter(input_alphas)
    for out_ch in output_alphas:
        found = False
        for in_ch in it:
            if in_ch == out_ch:
                found = True
                break
        assert found, (
            f"Character {out_ch!r} in output not found as subsequence in input. "
            f"Input alphas: {input_alphas}, Output alphas: {output_alphas}"
        )


# Strategies for valid ScenarioInfo instances
_season = st.integers(min_value=1, max_value=99)
_scenario_number = st.integers(min_value=0, max_value=99).map(lambda n: f"{n:02d}")
_scenario_name = st.text(
    st.characters(whitelist_categories=("L", "N", "P", "S", "Zs")),
    min_size=1,
    max_size=60,
)


# Feature: chronicle-extractor, Property 7: Output filename format
@given(
    output_dir=st.just(Path("/output")),
    season=_season,
    scenario=_scenario_number,
    name=_scenario_name,
)
def test_output_filename_format(
    output_dir: Path, season: int, scenario: str, name: str
) -> None:
    """build_output_path produces a path matching the expected format.

    The path should be: output_dir/season{season}/{season}-{scenario}-{sanitized}Chronicle.pdf

    Validates: Requirements 4.2, 5.1
    """
    info = ScenarioInfo(season=season, scenario=scenario, name=name)
    result = build_output_path(output_dir, info)

    sanitized = sanitize_name(name)
    expected_filename = f"{season}-{scenario}-{sanitized}Chronicle.pdf"
    expected_parent = f"season{season}"

    assert result.name == expected_filename, (
        f"Filename mismatch: {result.name!r} != {expected_filename!r}"
    )
    assert result.parent.name == expected_parent, (
        f"Parent dir mismatch: {result.parent.name!r} != {expected_parent!r}"
    )
    assert result.parent.parent == output_dir, (
        f"Output dir mismatch: {result.parent.parent!r} != {output_dir!r}"
    )
