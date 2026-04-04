"""PDF page preparation for structural element detection.

Opens a chronicle PDF, strips all text blocks and embedded images from
the last page, renders the cleaned page at 150 DPI, and returns
grayscale and RGB numpy arrays for downstream detection.
"""

import os

import fitz
import numpy as np

RENDER_DPI = 150


def prepare_page(pdf_path: str) -> tuple[np.ndarray, np.ndarray]:
    """Open a chronicle PDF, strip text and images, render to arrays.

    Opens the last page of the PDF, redacts all text blocks and
    embedded images, renders at 150 DPI, and returns grayscale
    and RGB numpy arrays.

    Args:
        pdf_path: Path to the chronicle PDF file.

    Returns:
        A tuple of (grayscale_array, rgb_array) where grayscale_array
        has shape (height, width) and rgb_array has shape (height, width, 3).

    Raises:
        FileNotFoundError: If pdf_path does not exist.
        ValueError: If the file is not a valid PDF.

    Requirements: chronicle-blueprints 1.1, 1.2, 1.3, 1.4, 1.5
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise ValueError(f"Not a valid PDF: {pdf_path}") from exc

    if doc.page_count == 0:
        doc.close()
        raise ValueError(f"PDF has no pages: {pdf_path}")

    page = doc[doc.page_count - 1]

    _redact_text_blocks(page)
    _redact_images(page)
    page.apply_redactions()

    pixmap = page.get_pixmap(dpi=RENDER_DPI)
    rgb_array = _pixmap_to_rgb_array(pixmap)
    grayscale_array = _rgb_to_grayscale(rgb_array)

    doc.close()
    return grayscale_array, rgb_array


def _redact_text_blocks(page: fitz.Page) -> None:
    """Add redaction annotations over every text block on the page."""
    text_dict = page.get_text("dict")
    for block in text_dict["blocks"]:
        if block.get("type") == 0:  # text block
            rect = fitz.Rect(block["bbox"])
            page.add_redact_annot(rect)


def _redact_images(page: fitz.Page) -> None:
    """Add redaction annotations over every embedded image on the page."""
    for img in page.get_images(full=True):
        xref = img[0]
        rects = page.get_image_rects(xref)
        for rect in rects:
            page.add_redact_annot(rect)


def _pixmap_to_rgb_array(pixmap: fitz.Pixmap) -> np.ndarray:
    """Convert a PyMuPDF Pixmap to an RGB numpy array of shape (h, w, 3)."""
    samples = np.frombuffer(pixmap.samples, dtype=np.uint8)
    if pixmap.n == 4:  # RGBA
        samples = samples.reshape(pixmap.h, pixmap.w, 4)[:, :, :3]
    else:
        samples = samples.reshape(pixmap.h, pixmap.w, pixmap.n)
    return samples


def _rgb_to_grayscale(rgb: np.ndarray) -> np.ndarray:
    """Convert an RGB array to grayscale using luminance weights.

    Uses the standard ITU-R BT.601 weights: 0.299R + 0.587G + 0.114B.
    """
    return np.dot(rgb[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
