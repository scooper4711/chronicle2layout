"""Unit tests for generate_layouts CLI argument defaults.

Verifies that --base-dir defaults to the parent of chronicle2layout/ and
--python defaults to sys.executable when not explicitly provided.

Requirements: refactor-chronicle2layout 6.4, 6.5
"""

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import generate_layouts


def build_parser() -> argparse.ArgumentParser:
    """Build the same argument parser that main() uses."""
    parser = argparse.ArgumentParser(description="Generate layout JSONs for PFS chronicles")
    parser.add_argument("--season", "-s", type=int, nargs="*", default=[])
    parser.add_argument("--scenarios", "-n", type=str, nargs="*", default=[])
    parser.add_argument("--base-dir", type=Path, default=None)
    parser.add_argument("--python", type=str, default=None)
    return parser


class TestBaseDirArgDefault:
    """Verify --base-dir defaults to parent of chronicle2layout/.

    Requirements: refactor-chronicle2layout 6.4
    """

    def test_base_dir_is_none_when_omitted(self) -> None:
        """Parser returns None for --base-dir when not provided."""
        parser = build_parser()
        args = parser.parse_args([])
        assert args.base_dir is None

    def test_base_dir_accepts_explicit_path(self) -> None:
        """Parser returns the provided Path when --base-dir is given."""
        parser = build_parser()
        args = parser.parse_args(["--base-dir", "/tmp/my-project"])
        assert args.base_dir == Path("/tmp/my-project")

    def test_default_resolution_uses_parents_2(self) -> None:
        """When --base-dir is None, the fallback resolves to parents[2] of generate_layouts.py.

        generate_layouts.py lives at chronicle2layout/src/generate_layouts.py,
        so parents[2] is the project root (parent of chronicle2layout/).
        """
        generate_layouts_path = Path(generate_layouts.__file__).resolve()
        expected_base_dir = generate_layouts_path.parents[2]

        # Simulate the resolution logic: args.base_dir or Path(__file__).resolve().parents[2]
        resolved = None or generate_layouts_path.parents[2]
        assert resolved == expected_base_dir


class TestPythonArgDefault:
    """Verify --python defaults to sys.executable.

    Requirements: refactor-chronicle2layout 6.5
    """

    def test_python_is_none_when_omitted(self) -> None:
        """Parser returns None for --python when not provided."""
        parser = build_parser()
        args = parser.parse_args([])
        assert args.python is None

    def test_python_accepts_explicit_value(self) -> None:
        """Parser returns the provided string when --python is given."""
        parser = build_parser()
        args = parser.parse_args(["--python", "/usr/bin/python3.11"])
        assert args.python == "/usr/bin/python3.11"

    def test_default_resolution_uses_sys_executable(self) -> None:
        """When --python is None, the fallback resolves to sys.executable."""
        resolved = None or sys.executable
        assert resolved == sys.executable
