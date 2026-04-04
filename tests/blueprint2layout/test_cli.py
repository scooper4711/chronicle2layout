"""CLI integration tests for blueprint2layout.__main__.

Tests error handling for missing arguments and missing input files.
Requirements: 13.1–13.5
"""

import json

from blueprint2layout.__main__ import main


def test_missing_arguments_exits_nonzero():
    """Calling main with no arguments should return a non-zero exit code."""
    exit_code = main([])
    assert exit_code != 0


def test_too_few_arguments_exits_nonzero():
    """Calling main with only one argument should return a non-zero exit code."""
    exit_code = main(["only_one_arg"])
    assert exit_code != 0


def test_missing_blueprint_file_exits_nonzero(tmp_path):
    """Calling main with a nonexistent Blueprint file should return exit code 1."""
    exit_code = main([
        str(tmp_path / "nonexistent.json"),
        str(tmp_path / "some.pdf"),
        str(tmp_path / "output.json"),
    ])
    assert exit_code == 1


def test_missing_pdf_file_exits_nonzero(tmp_path):
    """Calling main with a valid Blueprint but nonexistent PDF should return exit code 1."""
    blueprint_data = {
        "id": "test.bp",
        "canvases": [
            {
                "name": "page",
                "left": 0,
                "right": 100,
                "top": 0,
                "bottom": 100,
            }
        ],
    }
    blueprint_file = tmp_path / "valid_blueprint.json"
    blueprint_file.write_text(json.dumps(blueprint_data))

    exit_code = main([
        str(blueprint_file),
        str(tmp_path / "nonexistent.pdf"),
        str(tmp_path / "output.json"),
    ])
    assert exit_code == 1
