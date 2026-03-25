"""CLI entry point for the chronicle extractor utility.

Provides parse_args for command-line argument parsing and main as the
entry point that validates inputs, creates output directories, and
delegates to the processing pipeline.
"""

import argparse
import sys
from pathlib import Path

from chronicle_extractor.extractor import process_directory


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and validate command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with input_dir and output_dir as Path objects.

    Requirements: chronicle-extractor 1.1, 1.2
    """
    parser = argparse.ArgumentParser(
        description="Extract chronicle pages from PFS scenario PDFs.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing scenario PDFs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Base directory for saving extracted chronicle PDFs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the chronicle extractor CLI.

    Parses arguments, validates input directory, creates output
    directory, and delegates to process_directory.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for errors.

    Requirements: chronicle-extractor 1.3, 1.4
    """
    args = parse_args(argv)

    if not args.input_dir.exists():
        print(
            f"Error: input directory does not exist: {args.input_dir}",
            file=sys.stderr,
        )
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    process_directory(args.input_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
