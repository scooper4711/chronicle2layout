"""PDF page rendering via PyMuPDF.

Renders the first page of a chronicle PDF as an RGB pixmap at a
configurable DPI for use as the visualization background.
"""

from pathlib import Path

import fitz


def render_pdf_page(pdf_path: Path, dpi: int = 150) -> fitz.Pixmap:
    """Render the first page of a PDF as a pixmap.

    Opens the PDF, renders page 0 at the specified DPI,
    and returns an RGB pixmap.

    Args:
        pdf_path: Path to the chronicle PDF file.
        dpi: Resolution for rendering (default 150).

    Returns:
        An RGB fitz.Pixmap of the rendered page.

    Raises:
        FileNotFoundError: If pdf_path does not exist.
        ValueError: If the file is not a valid PDF.

    Requirements: layout-visualizer 3.1, 3.2, 3.3
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise ValueError(f"Not a valid PDF: {pdf_path}") from exc

    if doc.page_count == 0:
        doc.close()
        raise ValueError(f"PDF has no pages: {pdf_path}")

    page = doc[0]
    pixmap = page.get_pixmap(dpi=dpi)

    if pixmap.alpha:
        pixmap = fitz.Pixmap(fitz.csRGB, pixmap)

    doc.close()
    return pixmap
