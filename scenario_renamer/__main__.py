"""CLI entry point for the scenario renamer utility.

Parses command-line arguments for input and output directories,
validates the input directory exists, creates the output directory
if needed, and delegates to the processor orchestrator.

Usage:
    python -m scenario_renamer --input-dir <path> --output-dir <path>
"""

import argparse
import sys
from pathlib import Path

from scenario_renamer.processor import process_directory


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and validate command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with input_dir and output_dir as Path objects.

    Requirements: scenario-renamer 1.1, 1.2
    """
    parser = argparse.ArgumentParser(
        description="Copy and rename PFS scenario PDFs and images",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing scenario PDFs and images.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Base directory for saving renamed scenario files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the scenario renamer CLI.

    Parses arguments, validates input directory, creates output
    directory, and delegates to process_directory.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for errors.

    Requirements: scenario-renamer 1.3, 1.4
    """
    try:
        args = parse_args(argv)

        if not args.input_dir.is_dir():
            print(
                f"Error: input directory does not exist: {args.input_dir}",
                file=sys.stderr,
            )
            return 1

        args.output_dir.mkdir(parents=True, exist_ok=True)
        process_directory(args.input_dir, args.output_dir)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
