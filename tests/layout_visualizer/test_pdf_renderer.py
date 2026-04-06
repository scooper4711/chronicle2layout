"""Unit tests for PDF page rendering."""

import tempfile
from pathlib import Path

import fitz
import pytest

from layout_visualizer.pdf_renderer import render_pdf_page

REAL_PDF = Path(
    "modules/pfs-chronicle-generator/assets/chronicles"
    "/pfs2/bounties/B13-TheBlackwoodAbundanceChronicle.pdf"
)


class TestRenderPdfPage:
    """Tests for render_pdf_page."""

    def test_renders_real_pdf_as_rgb_pixmap(self):
        """Render a real chronicle PDF and verify the pixmap is RGB."""
        pixmap = render_pdf_page(REAL_PDF)

        assert isinstance(pixmap, fitz.Pixmap)
        assert pixmap.n == 3, "Pixmap should be RGB (3 channels)"
        assert not pixmap.alpha, "Pixmap should not have an alpha channel"

    def test_pixmap_dimensions_match_150_dpi(self):
        """Verify rendered pixmap dimensions are consistent with 150 DPI."""
        pixmap = render_pdf_page(REAL_PDF, dpi=150)

        # At 150 DPI a US Letter page (8.5x11 in) would be ~1275x1650.
        # Chronicle sheets vary, but dimensions should be reasonable.
        assert pixmap.width > 0
        assert pixmap.height > 0
        assert pixmap.width >= 500, "Width too small for 150 DPI"
        assert pixmap.height >= 500, "Height too small for 150 DPI"

    def test_missing_pdf_raises_file_not_found(self):
        """FileNotFoundError for a path that does not exist."""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            render_pdf_page(Path("nonexistent/fake.pdf"))

    def test_invalid_pdf_raises_value_error(self):
        """ValueError when the file exists but is not a valid PDF."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"This is not a PDF file at all.")
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(ValueError, match="Not a valid PDF"):
                render_pdf_page(tmp_path)
        finally:
            tmp_path.unlink()
