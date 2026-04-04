"""CLI entry point for the blueprint2layout tool.

Provides parse_args for command-line argument parsing and main as the
entry point that validates inputs, runs the full pipeline via
generate_layout, and writes the output layout JSON file.
"""

import argparse
import sys
from pathlib import Path

from blueprint2layout import generate_layout
from blueprint2layout.output import write_layout


def parse_args(argv=None):
    """Parse command-line arguments for blueprint2layout.

    Accepts three positional arguments: blueprint path, chronicle PDF
    path, and output JSON path. Optional --blueprints-dir flag.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with blueprint, pdf, output as Paths,
        and blueprints_dir as Path or None.

    Requirements: chronicle-blueprints 13.1, 13.2
    """
    parser = argparse.ArgumentParser(
        prog="blueprint2layout",
        description="Convert a Blueprint JSON + chronicle PDF into a layout.json file.",
    )
    parser.add_argument("blueprint", type=Path, help="Path to the Blueprint JSON file")
    parser.add_argument("pdf", type=Path, help="Path to the chronicle PDF file")
    parser.add_argument("output", type=Path, help="Path for the output layout.json file")
    parser.add_argument(
        "--blueprints-dir",
        type=Path,
        default=None,
        help="Directory to scan for Blueprint files (default: blueprint's directory)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Entry point for the blueprint2layout CLI.

    Parses arguments, runs the full pipeline via generate_layout,
    and writes the output. Prints errors to stderr.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for errors.

    Requirements: chronicle-blueprints 13.3, 13.4, 13.5
    """
    try:
        args = parse_args(argv)
    except SystemExit as exc:
        return exc.code if exc.code is not None else 1

    try:
        layout = generate_layout(args.blueprint, args.pdf, args.blueprints_dir)
        write_layout(layout, args.output)
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
