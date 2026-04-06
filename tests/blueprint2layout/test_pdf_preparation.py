"""Unit tests for PDF page preparation.

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from blueprint2layout.pdf_preparation import prepare_page

REAL_PDF = "Chronicles/pfs2/season5/5-01-IntroYearofUnfetteredExplorationChronicle.pdf"


@pytest.fixture
def chronicle_pdf_path() -> str:
    """Return path to a real chronicle PDF for integration tests."""
    path = REAL_PDF
    if not Path(path).exists():
        pytest.skip(f"Chronicle PDF not found: {path}")
    return path


def test_prepare_page_returns_correct_shapes(chronicle_pdf_path: str) -> None:
    """Grayscale is 2D uint8, RGB is 3D with 3 channels and uint8.

    Validates: Requirements 1.1, 1.4, 1.5
    """
    grayscale, rgb = prepare_page(chronicle_pdf_path)

    assert isinstance(grayscale, np.ndarray)
    assert grayscale.ndim == 2
    assert grayscale.dtype == np.uint8

    assert isinstance(rgb, np.ndarray)
    assert rgb.ndim == 3
    assert rgb.shape[2] == 3
    assert rgb.dtype == np.uint8

    assert grayscale.shape[0] == rgb.shape[0]
    assert grayscale.shape[1] == rgb.shape[1]


def test_prepare_page_missing_file() -> None:
    """FileNotFoundError raised for a nonexistent PDF path.

    Validates: Requirement 1.1
    """
    with pytest.raises(FileNotFoundError):
        prepare_page("/nonexistent/path/to/chronicle.pdf")


def test_prepare_page_invalid_pdf() -> None:
    """ValueError raised for a file that is not a valid PDF.

    Validates: Requirement 1.1
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(b"This is not a PDF file at all.")
        tmp.flush()
        tmp_path = tmp.name

    with pytest.raises(ValueError):
        prepare_page(tmp_path)


def test_prepare_page_grayscale_values_in_range(chronicle_pdf_path: str) -> None:
    """All grayscale pixel values are in the 0-255 range.

    Validates: Requirements 1.4, 1.5
    """
    grayscale, _ = prepare_page(chronicle_pdf_path)

    assert grayscale.min() >= 0
    assert grayscale.max() <= 255


def test_prepare_page_rgb_values_in_range(chronicle_pdf_path: str) -> None:
    """All RGB pixel values are in the 0-255 range.

    Validates: Requirements 1.4, 1.5
    """
    _, rgb = prepare_page(chronicle_pdf_path)

    assert rgb.min() >= 0
    assert rgb.max() <= 255
