"""Property-based tests for scenario_download_workflow.detection.

Uses hypothesis to verify universal properties of game system detection
across randomly generated text inputs.
"""

from hypothesis import given
from hypothesis import strategies as st

from scenario_download_workflow.detection import (
    GameSystem,
    detect_game_system,
)

_PATHFINDER = "Pathfinder Society"
_STARFINDER = "Starfinder Society"


@st.composite
def text_with_optional_society_strings(draw: st.DrawFn) -> tuple[str, bool, bool]:
    """Generate random text optionally containing society strings.

    Returns:
        Tuple of (text, has_pathfinder, has_starfinder).
    """
    base = draw(
        st.text(
            st.characters(
                whitelist_categories=("L", "N", "P", "Z"),
                min_codepoint=32,
                max_codepoint=126,
            ),
            min_size=0,
            max_size=100,
        )
    )

    # Filter out base text that accidentally contains society strings
    lowered_base = base.lower()
    if "pathfinder society" in lowered_base or "starfinder society" in lowered_base:
        base = "Some neutral filler text for testing"

    inject_pathfinder = draw(st.booleans())
    inject_starfinder = draw(st.booleans())

    # Apply random case variation to injected strings
    case_fn = draw(st.sampled_from([str.lower, str.upper, str.title]))

    parts = [base]
    if inject_pathfinder:
        parts.append(case_fn(_PATHFINDER))
    if inject_starfinder:
        parts.append(case_fn(_STARFINDER))

    draw(st.randoms()).shuffle(parts)
    text = " ".join(parts)

    return text, inject_pathfinder, inject_starfinder


# Feature: scenario-download-workflow, Property 4: Game system detection is consistent with society string presence
@given(data=text_with_optional_society_strings())
def test_detection_consistent_with_society_string_presence(
    data: tuple[str, bool, bool],
) -> None:
    """For any text, detect_game_system returns PFS if 'Pathfinder Society'
    is present, SFS if only 'Starfinder Society' is present, and None
    if neither is present. Pathfinder takes precedence when both exist.

    Validates: Requirements 4.2, 4.3, 4.4
    """
    text, has_pathfinder, has_starfinder = data
    result = detect_game_system(text)

    if has_pathfinder:
        assert result == GameSystem.PFS, (
            f"Expected PFS for text containing Pathfinder Society, got {result}"
        )
    elif has_starfinder:
        assert result == GameSystem.SFS, (
            f"Expected SFS for text containing only Starfinder Society, got {result}"
        )
    else:
        assert result is None, (
            f"Expected None for text without society strings, got {result}"
        )
