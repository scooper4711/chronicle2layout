# Feature: scenario-download-workflow, Property 6: Exit code reflects processing outcomes
"""Property-based tests for exit code logic.

Generates random (success_count, fail_count, skip_count) tuples and
verifies the exit code is 0 when success_count > 0, 1 otherwise.

Validates: Requirements 1.6, 14.5
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from scenario_download_workflow.__main__ import compute_exit_code


@given(
    success_count=st.integers(min_value=1, max_value=1000),
    fail_count=st.integers(min_value=0, max_value=1000),
    skip_count=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=200)
def test_exit_code_zero_when_any_success(
    success_count: int,
    fail_count: int,
    skip_count: int,
) -> None:
    """When at least one PDF is processed successfully, exit code is 0.

    skip_count is generated but not passed to compute_exit_code because
    skipped PDFs do not affect the exit code.

    **Validates: Requirements 1.6, 14.5**
    """
    assert compute_exit_code(success_count, fail_count) == 0


@given(
    fail_count=st.integers(min_value=0, max_value=1000),
    skip_count=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=200)
def test_exit_code_one_when_no_success(
    fail_count: int,
    skip_count: int,
) -> None:
    """When no PDFs are processed successfully, exit code is 1.

    skip_count is generated but not passed to compute_exit_code because
    skipped PDFs do not affect the exit code.

    **Validates: Requirements 1.6, 14.5**
    """
    assert compute_exit_code(0, fail_count) == 1
