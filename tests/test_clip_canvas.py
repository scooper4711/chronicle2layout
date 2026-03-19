"""Unit tests for clip_canvas.main().

Tests the CLI entry point for clipping a canvas region from a PDF.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from clip_canvas import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LETTER_WIDTH = 612
LETTER_HEIGHT = 792
CHECKBOX_FONT = fitz.Font("cour")

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


def create_test_pdf(tmp_path: Path, filename: str = "test.pdf") -> str:
    """Create a single-page PDF."""
    pdf_path = str(tmp_path / filename)
    doc = fitz.open()
    page = doc.new_page(width=LETTER_WIDTH, height=LETTER_HEIGHT)
    tw = fitz.TextWriter(page.rect)
    tw.append((100, 400), "Test content", font=CHECKBOX_FONT, fontsize=12)
    tw.write_text(page)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def create_layout_file(tmp_path: Path, parent_id: str = "pfs2") -> Path:
    """Create a layout JSON file with canvas definitions."""
    parts = parent_id.split(".")
    if len(parts) == 1:
        layout_dir = tmp_path / "layouts" / parts[0]
        layout_dir.mkdir(parents=True)
        layout_file = layout_dir / f"{parts[0]}.json"
    else:
        layout_dir = tmp_path / "layouts" / parts[0]
        layout_dir.mkdir(parents=True)
        layout_file = layout_dir / f"{parts[0]}.json"

    layout_data = {
        "canvas": {
            "items": {"x": 10, "y": 20, "x2": 90, "y2": 80},
            "summary": {"x": 0, "y": 0, "x2": 100, "y2": 20},
        }
    }
    layout_file.write_text(json.dumps(layout_data))
    return tmp_path / "layouts"


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------

class TestClipCanvasMain:
    """Unit tests for clip_canvas.main()."""

    def test_clips_and_saves_png(self, tmp_path: Path, capsys) -> None:
        """main() clips a canvas region and saves a PNG file."""
        pdf_path = create_test_pdf(tmp_path)
        layout_dir = create_layout_file(tmp_path)
        output_path = tmp_path / "output" / "clipped.png"

        test_args = [
            "clip_canvas.py",
            "--pdf", pdf_path,
            "--layout-dir", str(layout_dir),
            "--parent", "pfs2",
            "--canvas", "items",
            "--output", str(output_path),
        ]
        with patch("sys.argv", test_args):
            main()

        assert output_path.exists()
        captured = capsys.readouterr()
        assert "Wrote" in captured.out

    def test_missing_layout_file_raises(self, tmp_path: Path) -> None:
        """main() raises ValueError when layout file is not found."""
        pdf_path = create_test_pdf(tmp_path)
        output_path = tmp_path / "output.png"

        test_args = [
            "clip_canvas.py",
            "--pdf", pdf_path,
            "--layout-dir", str(tmp_path / "nonexistent"),
            "--parent", "pfs2",
            "--output", str(output_path),
        ]
        with patch("sys.argv", test_args):
            with pytest.raises(ValueError, match="Layout file not found"):
                main()

    def test_zero_page_pdf_exits(self, tmp_path: Path) -> None:
        """main() exits with error when PDF has no pages."""
        pdf_path = str(tmp_path / "empty.pdf")
        with open(pdf_path, "wb") as f:
            f.write(_ZERO_PAGE_PDF)

        layout_dir = create_layout_file(tmp_path)
        output_path = tmp_path / "output.png"

        test_args = [
            "clip_canvas.py",
            "--pdf", pdf_path,
            "--layout-dir", str(layout_dir),
            "--parent", "pfs2",
            "--canvas", "items",
            "--output", str(output_path),
        ]
        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit, match="no pages"):
                main()

    def test_default_canvas_is_items(self, tmp_path: Path) -> None:
        """main() defaults to 'items' canvas when --canvas is not specified."""
        pdf_path = create_test_pdf(tmp_path)
        layout_dir = create_layout_file(tmp_path)
        output_path = tmp_path / "output.png"

        test_args = [
            "clip_canvas.py",
            "--pdf", pdf_path,
            "--layout-dir", str(layout_dir),
            "--parent", "pfs2",
            "--output", str(output_path),
        ]
        with patch("sys.argv", test_args):
            main()

        assert output_path.exists()

    def test_creates_output_parent_dirs(self, tmp_path: Path) -> None:
        """main() creates parent directories for the output path."""
        pdf_path = create_test_pdf(tmp_path)
        layout_dir = create_layout_file(tmp_path)
        output_path = tmp_path / "deep" / "nested" / "dir" / "output.png"

        test_args = [
            "clip_canvas.py",
            "--pdf", pdf_path,
            "--layout-dir", str(layout_dir),
            "--parent", "pfs2",
            "--canvas", "items",
            "--output", str(output_path),
        ]
        with patch("sys.argv", test_args):
            main()

        assert output_path.exists()
