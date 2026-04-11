"""Parse human-readable duration strings into timedelta objects.

Supports the format '<positive_integer><suffix>' where suffix is
'm' (minutes), 'h' (hours), or 'd' (days).
"""

import re
from datetime import timedelta

_DURATION_PATTERN = re.compile(r"^(\d+)([mhd])$")

_SUFFIX_TO_KWARG = {
    "m": "minutes",
    "h": "hours",
    "d": "days",
}


def parse_duration(value: str) -> timedelta:
    """Parse a human-readable duration string into a timedelta.

    Supported suffixes: 'm' (minutes), 'h' (hours), 'd' (days).
    The numeric part must be a positive integer (no zero, no negatives).

    Args:
        value: Duration string like '1h', '30m', '2d'.

    Returns:
        Equivalent timedelta.

    Raises:
        ValueError: If the string cannot be parsed or the number is not positive.
    """
    if not value:
        raise ValueError(f"Invalid duration: {value!r} (empty string)")

    match = _DURATION_PATTERN.match(value)
    if not match:
        raise ValueError(
            f"Invalid duration: {value!r}. "
            "Expected format: <positive_int><m|h|d>"
        )

    amount = int(match.group(1))
    suffix = match.group(2)

    if amount <= 0:
        raise ValueError(
            f"Invalid duration: {value!r}. Amount must be positive, got {amount}"
        )

    return timedelta(**{_SUFFIX_TO_KWARG[suffix]: amount})
