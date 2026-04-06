"""CLI integration tests for blueprint2layout.__main__.

Tests error handling for missing arguments and missing input files.
Requirements: 13.1–13.5
"""

import json

import pytest

from blueprint2layout.__main__ import main


def test_missing_arguments_exits_nonzero():
    """Calling main with no arguments should exit non-zero via argparse."""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code != 0


def test_too_few_arguments_exits_nonzero():
    """Calling main with only --blueprints-dir should exit non-zero."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--blueprints-dir", "/tmp"])
    assert exc_info.value.code != 0


def test_missing_blueprint_file_exits_nonzero(tmp_path):
    """Calling main with a nonexistent blueprints directory should return exit code 1."""
    exit_code = main([
        "--blueprints-dir", str(tmp_path / "nonexistent"),
        "--blueprint-id", "test.bp",
    ])
    assert exit_code == 1


def test_missing_pdf_file_exits_nonzero(tmp_path):
    """Calling main with a valid blueprints dir but no matching id should return exit code 1."""
    blueprints_dir = tmp_path / "blueprints"
    blueprints_dir.mkdir()

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
    blueprint_file = blueprints_dir / "test.bp.blueprint.json"
    blueprint_file.write_text(json.dumps(blueprint_data))

    exit_code = main([
        "--blueprints-dir", str(blueprints_dir),
        "--blueprint-id", "nonexistent.bp",
    ])
    assert exit_code == 1
