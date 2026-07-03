"""Path validation utilities to prevent path injection attacks.

Provides path normalization and control character rejection for CLI
arguments. These utilities make paths unambiguous (resolving ``~``,
``..``, symlinks) and reject characters that have no legitimate use
in filesystem paths but could be used for injection in agentic
workflows.

Design decision (accept-by-design):
    These CLI tools are local utilities where the operator (or calling
    agent) explicitly chooses input/output directories. There is no
    meaningful sandbox root to confine to. Instead we normalize paths
    so the resolved target is unambiguous, and reject control characters
    that could be used for injection. The orchestration layer (IDE,
    MCP sandbox, agent permission system) is responsible for restricting
    which directories the agent may target.

References:
    - OWASP Input Validation Cheat Sheet
    - SonarQube rule pythonsecurity:S8707
"""

from __future__ import annotations

from pathlib import Path


def reject_control_chars(value: str, label: str = "path") -> None:
    """Reject NUL bytes, newlines, and other control characters.

    Control characters (U+0000–U+001F, U+007F) have no legitimate use
    in filesystem paths and can be used to inject secondary commands
    in shell expansions, config file formats, or log entries.

    Args:
        value: The string to validate.
        label: Human-readable label for error messages.

    Raises:
        ValueError: If the value contains control characters.
    """
    for char in value:
        code = ord(char)
        if code <= 0x1F or code == 0x7F:
            raise ValueError(
                f"Invalid {label}: contains control character "
                f"U+{code:04X} — possible injection attempt"
            )


def user_path(raw: Path) -> Path:
    """Normalize a CLI-provided path for safe, unambiguous use.

    Performs the following steps:
    1. Rejects control characters (NUL, newline, etc.)
    2. Expands ``~`` to the user's home directory
    3. Resolves to an absolute canonical path (collapses ``..``,
       resolves symlinks)

    The result is a deterministic, absolute path that makes the
    actual filesystem target unambiguous. This does NOT sandbox
    the path to a specific directory — that is accept-by-design
    for local CLI tools.

    Args:
        raw: The path from CLI input to normalize.

    Returns:
        The resolved, absolute Path.

    Raises:
        ValueError: If the path contains control characters.
    """
    reject_control_chars(str(raw), label="path")
    return Path(raw).expanduser().resolve()
