# Feature: scenario-download-workflow, Property 3: User response classification is case-insensitive
"""Property-based tests for user response classification.

Generates random case variations of known response strings and verifies
correct action classification regardless of casing.

Validates: Requirements 3.2, 3.3, 3.4
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from scenario_download_workflow.__main__ import classify_response

_ACCEPT_WORDS = ("y", "yes")
_SKIP_WORDS = ("n", "no")
_QUIT_WORDS = ("q", "quit")


@st.composite
def random_case_variation(draw: st.DrawFn, word: str) -> str:
    """Generate a random case variation of a word.

    Each character is independently upper- or lower-cased.
    """
    chars = []
    for char in word:
        make_upper = draw(st.booleans())
        chars.append(char.upper() if make_upper else char.lower())
    return "".join(chars)


@st.composite
def accept_response(draw: st.DrawFn) -> str:
    """Generate a random case variation of an accept response."""
    word = draw(st.sampled_from(_ACCEPT_WORDS))
    return draw(random_case_variation(word))


@st.composite
def skip_response(draw: st.DrawFn) -> str:
    """Generate a random case variation of a skip response."""
    word = draw(st.sampled_from(_SKIP_WORDS))
    return draw(random_case_variation(word))


@st.composite
def quit_response(draw: st.DrawFn) -> str:
    """Generate a random case variation of a quit response."""
    word = draw(st.sampled_from(_QUIT_WORDS))
    return draw(random_case_variation(word))


@given(response=accept_response())
@settings(max_examples=200)
def test_accept_responses_classified_correctly(response: str) -> None:
    """Any case variation of 'y' or 'yes' is classified as 'accept'.

    **Validates: Requirements 3.2**
    """
    assert classify_response(response) == "accept"


@given(response=skip_response())
@settings(max_examples=200)
def test_skip_responses_classified_correctly(response: str) -> None:
    """Any case variation of 'n' or 'no' is classified as 'skip'.

    **Validates: Requirements 3.3**
    """
    assert classify_response(response) == "skip"


@given(response=quit_response())
@settings(max_examples=200)
def test_quit_responses_classified_correctly(response: str) -> None:
    """Any case variation of 'q' or 'quit' is classified as 'quit'.

    **Validates: Requirements 3.4**
    """
    assert classify_response(response) == "quit"
