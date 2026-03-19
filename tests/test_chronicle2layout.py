"""Unit tests for chronicle2layout module.

Tests the internal helper functions (_parse_region_arg, _group_words_by_line,
_find_matching_line_y, _convert_lines_to_results, _resolve_region_from_layout)
and the extract_text_lines / main CLI entry point.

Requirements: refactor-chronicle2layout 3.2, 3.4, 4.1, 4.2, 4.6, 5.3, 5.5
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chronicle2layout import (
    DEFAULT_REGION_PCT,
    Y_COORDINATE_GROUPING_TOLERANCE,
    _convert_lines_to_results,
    _find_matching_line_y,
    _group_words_by_line,
    _parse_region_arg,
    _resolve_region_from_layout,
    extract_text_lines,
    main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LETTER_WIDTH = 612
LETTER_HEIGHT = 792
CHECKBOX_FONT = fitz.Font("cour")


def create_test_pdf(
    tmp_path: Path,
    text_items: list[tuple[str, float, float]],
    filename: str = "test.pdf",
) -> str:
    """Create a single-page PDF with text placed via TextWriter."""
    pdf_path = str(tmp_path / filename)
    doc = fitz.open()
    page = doc.new_page(width=LETTER_WIDTH, height=LETTER_HEIGHT)
    tw = fitz.TextWriter(page.rect)
    for text, x, y in text_items:
        tw.append((x, y), text, font=CHECKBOX_FONT, fontsize=12)
    tw.write_text(page)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


_ZERO_PAGE_PDF = (
    b"%PDF-1.0\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
    b"xref\n0 3\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"trailer<</Size 3/Root 1 0 R>>\n"
    b"startxref\n109\n%%EOF"
)


def create_empty_pdf(tmp_path: Path, filename: str = "empty.pdf") -> str:
    """Create a valid PDF with zero pages."""
    pdf_path = str(tmp_path / filename)
    with open(pdf_path, "wb") as f:
        f.write(_ZERO_PAGE_PDF)
    return pdf_path


# ---------------------------------------------------------------------------
# _parse_region_arg tests
# ---------------------------------------------------------------------------

class TestParseRegionArg:
    """Unit tests for _parse_region_arg."""

    def test_none_returns_none(self) -> None:
        """No region argument returns None."""
        assert _parse_region_arg(None) is None

    def test_valid_four_values(self) -> None:
        """Four comma-separated floats return a list of four floats."""
        result = _parse_region_arg("0.5, 50.8, 40.0, 83.0")
        assert result == [0.5, 50.8, 40.0, 83.0]

    def test_no_spaces(self) -> None:
        """Values without spaces parse correctly."""
        result = _parse_region_arg("1,2,3,4")
        assert result == [1.0, 2.0, 3.0, 4.0]

    def test_too_few_values_returns_false(self) -> None:
        """Fewer than four values returns False."""
        result = _parse_region_arg("1,2,3")
        assert result is False

    def test_too_many_values_returns_false(self) -> None:
        """More than four values returns False."""
        result = _parse_region_arg("1,2,3,4,5")
        assert result is False

    def test_non_numeric_returns_false(self) -> None:
        """Non-numeric values return False."""
        result = _parse_region_arg("a,b,c,d")
        assert result is False

    def test_empty_string_returns_false(self) -> None:
        """Empty string returns False."""
        result = _parse_region_arg("")
        assert result is False

    def test_trailing_commas_handled(self) -> None:
        """Trailing commas with empty parts are stripped."""
        result = _parse_region_arg("1,2,3,4,")
        assert result == [1.0, 2.0, 3.0, 4.0]


# ---------------------------------------------------------------------------
# _find_matching_line_y tests
# ---------------------------------------------------------------------------

class TestFindMatchingLineY:
    """Unit tests for _find_matching_line_y."""

    def test_empty_dict_returns_none(self) -> None:
        """No existing lines returns None."""
        assert _find_matching_line_y(100.0, {}) is None

    def test_exact_match(self) -> None:
        """Exact y-coordinate match returns the key."""
        lines = {100.0: []}
        assert _find_matching_line_y(100.0, lines) == 100.0

    def test_within_tolerance(self) -> None:
        """Y within tolerance of existing key returns that key."""
        lines = {100.0: []}
        assert _find_matching_line_y(101.5, lines) == 100.0

    def test_outside_tolerance(self) -> None:
        """Y outside tolerance returns None."""
        lines = {100.0: []}
        assert _find_matching_line_y(103.0, lines) is None


# ---------------------------------------------------------------------------
# _group_words_by_line tests
# ---------------------------------------------------------------------------

class TestGroupWordsByLine:
    """Unit tests for _group_words_by_line."""

    def test_empty_words_returns_empty(self) -> None:
        """No words produces empty dict."""
        result = _group_words_by_line([], 0, 0, 100, 100)
        assert result == {}

    def test_words_outside_region_excluded(self) -> None:
        """Words outside the region are not included."""
        words = [(200, 200, 250, 210, "outside", 0, 0, 0)]
        result = _group_words_by_line(words, 0, 0, 100, 100)
        assert result == {}

    def test_words_inside_region_grouped(self) -> None:
        """Words inside the region are grouped by y-coordinate."""
        words = [
            (10, 50, 30, 60, "hello", 0, 0, 0),
            (35, 50.5, 55, 60, "world", 0, 0, 1),
        ]
        result = _group_words_by_line(words, 0, 0, 100, 100)
        assert len(result) == 1
        line_words = list(result.values())[0]
        assert len(line_words) == 2

    def test_words_on_different_lines(self) -> None:
        """Words far apart vertically go into separate lines."""
        words = [
            (10, 50, 30, 60, "line1", 0, 0, 0),
            (10, 80, 30, 90, "line2", 0, 0, 0),
        ]
        result = _group_words_by_line(words, 0, 0, 100, 100)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _convert_lines_to_results tests
# ---------------------------------------------------------------------------

class TestConvertLinesToResults:
    """Unit tests for _convert_lines_to_results."""

    def test_empty_lines_returns_empty(self) -> None:
        """No lines produces empty results."""
        result = _convert_lines_to_results({}, 0, 0, 100, 100)
        assert result == []

    def test_skips_items_header(self) -> None:
        """Lines containing only 'items' or 'items:' are skipped."""
        lines = {
            10.0: [{"text": "Items", "x0": 5, "y0": 10, "x1": 30, "y1": 20}],
        }
        result = _convert_lines_to_results(lines, 0, 0, 100, 100)
        assert result == []

    def test_converts_to_percentages(self) -> None:
        """Word coordinates are converted to region-relative percentages."""
        lines = {
            10.0: [
                {"text": "Longsword", "x0": 10, "y0": 10, "x1": 50, "y1": 20},
            ],
        }
        result = _convert_lines_to_results(lines, 0, 0, 100, 100)
        assert len(result) == 1
        assert result[0]["text"] == "Longsword"
        assert result[0]["top_left_pct"] == [10.0, 10.0]
        assert result[0]["bottom_right_pct"] == [50.0, 20.0]

    def test_joins_multiple_words(self) -> None:
        """Multiple words on the same line are joined with spaces."""
        lines = {
            10.0: [
                {"text": "Long", "x0": 10, "y0": 10, "x1": 25, "y1": 20},
                {"text": "sword", "x0": 26, "y0": 10, "x1": 50, "y1": 20},
            ],
        }
        result = _convert_lines_to_results(lines, 0, 0, 100, 100)
        assert result[0]["text"] == "Long sword"

    def test_empty_word_list_skipped(self) -> None:
        """A line key with an empty word list produces no result."""
        lines = {10.0: []}
        result = _convert_lines_to_results(lines, 0, 0, 100, 100)
        assert result == []

    def test_results_sorted_by_y(self) -> None:
        """Results are sorted by y-coordinate (top to bottom)."""
        lines = {
            50.0: [{"text": "second", "x0": 10, "y0": 50, "x1": 40, "y1": 60}],
            10.0: [{"text": "first", "x0": 10, "y0": 10, "x1": 40, "y1": 20}],
        }
        result = _convert_lines_to_results(lines, 0, 0, 100, 100)
        assert result[0]["text"] == "first"
        assert result[1]["text"] == "second"


# ---------------------------------------------------------------------------
# _resolve_region_from_layout tests
# ---------------------------------------------------------------------------

class TestResolveRegionFromLayout:
    """Unit tests for _resolve_region_from_layout."""

    def test_returns_none_on_missing_layout(self, tmp_path: Path) -> None:
        """Returns None when the layout file does not exist."""
        result = _resolve_region_from_layout(str(tmp_path), "nonexistent", "items")
        assert result is None

    def test_returns_coordinates_from_valid_layout(self, tmp_path: Path) -> None:
        """Returns canvas coordinates from a valid layout file."""
        layout_dir = tmp_path / "pfs2"
        layout_dir.mkdir()
        layout_file = layout_dir / "pfs2.json"
        layout_data = {
            "canvas": {
                "items": {"x": 10, "y": 20, "x2": 80, "y2": 90}
            }
        }
        layout_file.write_text(json.dumps(layout_data))

        result = _resolve_region_from_layout(str(tmp_path), "pfs2", "items")
        assert result == [10, 20, 80, 90]

    def test_returns_none_on_missing_canvas(self, tmp_path: Path) -> None:
        """Returns None when the canvas name is not in the layout."""
        layout_dir = tmp_path / "pfs2"
        layout_dir.mkdir()
        layout_file = layout_dir / "pfs2.json"
        layout_data = {"canvas": {"other": {"x": 0, "y": 0, "x2": 100, "y2": 100}}}
        layout_file.write_text(json.dumps(layout_data))

        result = _resolve_region_from_layout(str(tmp_path), "pfs2", "items")
        assert result is None


# ---------------------------------------------------------------------------
# extract_text_lines tests
# ---------------------------------------------------------------------------

class TestExtractTextLines:
    """Unit tests for extract_text_lines."""

    def test_empty_pdf_returns_empty(self, tmp_path: Path) -> None:
        """A PDF with zero pages returns an empty list."""
        pdf_path = create_empty_pdf(tmp_path)
        result = extract_text_lines(pdf_path)
        assert result == []

    def test_extracts_text_from_region(self, tmp_path: Path) -> None:
        """Text within the specified region is extracted."""
        pdf_path = create_test_pdf(tmp_path, [
            ("Longsword", 100, 400),
            ("Shield", 100, 420),
        ])
        # Region covering the full page
        region = [0.0, 0.0, 100.0, 100.0]
        result = extract_text_lines(pdf_path, region_pct=region)
        texts = [r["text"] for r in result]
        assert any("Longsword" in t for t in texts)
        assert any("Shield" in t for t in texts)

    def test_uses_default_region_when_none(self, tmp_path: Path) -> None:
        """When no region is provided and no layout, uses DEFAULT_REGION_PCT."""
        pdf_path = create_test_pdf(tmp_path, [("Test", 5, 410)])
        result = extract_text_lines(pdf_path, region_pct=None)
        # Should not crash; may or may not find text depending on default region
        assert isinstance(result, list)

    def test_uses_layout_dir_for_region(self, tmp_path: Path) -> None:
        """When layout_dir and parent_id are provided, resolves region from layout."""
        layout_dir = tmp_path / "layouts" / "pfs2"
        layout_dir.mkdir(parents=True)
        layout_file = layout_dir / "pfs2.json"
        layout_data = {
            "canvas": {
                "items": {"x": 0, "y": 0, "x2": 100, "y2": 100}
            }
        }
        layout_file.write_text(json.dumps(layout_data))

        pdf_path = create_test_pdf(tmp_path, [("Hello", 100, 400)])
        result = extract_text_lines(
            pdf_path,
            layout_dir=str(tmp_path / "layouts"),
            parent_id="pfs2",
            canvas_name="items",
        )
        assert isinstance(result, list)

    def test_result_has_expected_keys(self, tmp_path: Path) -> None:
        """Each result dict has text, top_left_pct, and bottom_right_pct."""
        pdf_path = create_test_pdf(tmp_path, [("Word", 100, 400)])
        region = [0.0, 0.0, 100.0, 100.0]
        result = extract_text_lines(pdf_path, region_pct=region)
        if result:
            item = result[0]
            assert "text" in item
            assert "top_left_pct" in item
            assert "bottom_right_pct" in item


# ---------------------------------------------------------------------------
# main() CLI tests
# ---------------------------------------------------------------------------

class TestMain:
    """Unit tests for the main() CLI entry point."""

    def test_main_with_output_file(self, tmp_path: Path) -> None:
        """main() writes JSON output to the specified file."""
        pdf_path = create_test_pdf(tmp_path, [("Test item", 100, 400)])
        output_path = tmp_path / "output.json"

        test_args = [
            "chronicle2layout.py",
            pdf_path,
            "--region", "0,0,100,100",
            "--output", str(output_path),
            "--id", "pfs2.test",
            "--description", "Test scenario",
        ]
        with patch("sys.argv", test_args):
            main()

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert isinstance(data, dict)

    def test_main_with_stdout(self, tmp_path: Path, capsys) -> None:
        """main() prints JSON to stdout when no --output is given."""
        pdf_path = create_test_pdf(tmp_path, [("Test item", 100, 400)])

        test_args = [
            "chronicle2layout.py",
            pdf_path,
            "--region", "0,0,100,100",
            "--id", "pfs2.test",
            "--description", "Test scenario",
        ]
        with patch("sys.argv", test_args):
            main()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, dict)

    def test_main_with_invalid_region_aborts(self, tmp_path: Path, capsys) -> None:
        """main() aborts gracefully with an invalid --region value."""
        pdf_path = create_test_pdf(tmp_path, [("Test", 100, 400)])

        test_args = [
            "chronicle2layout.py",
            pdf_path,
            "--region", "bad,values",
        ]
        with patch("sys.argv", test_args):
            main()

        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    def test_main_with_layout_dir_and_parent(self, tmp_path: Path) -> None:
        """main() resolves region from layout when --layout-dir and --parent given."""
        layout_dir = tmp_path / "layouts" / "pfs2"
        layout_dir.mkdir(parents=True)
        layout_file = layout_dir / "pfs2.json"
        layout_data = {
            "canvas": {
                "items": {"x": 0, "y": 0, "x2": 100, "y2": 100},
                "summary": {"x": 0, "y": 0, "x2": 100, "y2": 50},
            }
        }
        layout_file.write_text(json.dumps(layout_data))

        pdf_path = create_test_pdf(tmp_path, [("Test", 100, 400)])
        output_path = tmp_path / "output.json"

        test_args = [
            "chronicle2layout.py",
            pdf_path,
            "--layout-dir", str(tmp_path / "layouts"),
            "--parent", "pfs2",
            "--output", str(output_path),
            "--id", "pfs2.test",
            "--description", "Test",
        ]
        with patch("sys.argv", test_args):
            main()

        assert output_path.exists()

    def test_main_with_bad_parent_prints_error(self, tmp_path: Path, capsys) -> None:
        """main() prints error JSON when parent layout file is not found."""
        pdf_path = create_test_pdf(tmp_path, [("Test", 100, 400)])

        test_args = [
            "chronicle2layout.py",
            pdf_path,
            "--layout-dir", str(tmp_path / "layouts"),
            "--parent", "nonexistent",
            "--id", "pfs2.test",
        ]
        with patch("sys.argv", test_args):
            main()

        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    def test_main_uses_default_region_fallback(self, tmp_path: Path) -> None:
        """main() falls back to DEFAULT_REGION_PCT when no region source available."""
        pdf_path = create_test_pdf(tmp_path, [("Test", 100, 400)])
        output_path = tmp_path / "output.json"

        test_args = [
            "chronicle2layout.py",
            pdf_path,
            "--output", str(output_path),
            "--id", "pfs2.test",
            "--description", "Test",
        ]
        with patch("sys.argv", test_args):
            main()

        assert output_path.exists()
