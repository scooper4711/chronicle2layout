"""Core PDF processing for chronicle page extraction.

Provides extract_last_page for extracting the last page of a PDF into
a new document, and process_directory for orchestrating the extraction
workflow across all scenario PDFs in a directory.
"""

import os
import sys
from pathlib import Path

import fitz

from chronicle_extractor.filename import build_output_path
from chronicle_extractor.filters import is_scenario_pdf
from chronicle_extractor.parser import extract_scenario_info


def extract_last_page(input_path: Path, output_path: Path) -> None:
    """Extract the last page of a PDF and save it as a new PDF.

    Uses PyMuPDF to open the source PDF, copy its last page into
    a new document, and save to output_path. Creates parent
    directories if they don't exist.

    Args:
        input_path: Path to the source scenario PDF.
        output_path: Path where the single-page chronicle PDF is saved.

    Raises:
        RuntimeError: If PyMuPDF fails to open or write the PDF.

    Requirements: chronicle-extractor 4.1, 4.3
    """
    try:
        source = fitz.open(input_path)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to open PDF: {input_path}"
        ) from exc

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dest = fitz.open()
        dest.insert_pdf(source, from_page=len(source) - 1, to_page=len(source) - 1)
        dest.save(str(output_path))
        dest.close()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Failed to write chronicle PDF: {output_path}"
        ) from exc
    finally:
        source.close()

def _get_page_text(doc: fitz.Document, page_index: int) -> str | None:
    """Get text from a page by index, or None if the page doesn't exist."""
    if page_index >= len(doc):
        return None
    return doc[page_index].get_text()


def _process_single_entry(entry: os.DirEntry, output_dir: Path) -> None:
    """Process a single directory entry through the extraction pipeline.

    Opens the PDF once, reads the pages needed for extraction, then
    builds the output path and extracts the last page.

    Args:
        entry: A directory entry that has already passed is_scenario_pdf.
        output_dir: Base directory for output chronicle PDFs.

    Requirements: chronicle-extractor 6.1, 6.2, 6.3, 6.4
    """
    try:
        doc = fitz.open(entry.path)
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF: {entry.path}") from exc

    try:
        if len(doc) == 0:
            print(f"Warning: empty PDF {entry.name}", file=sys.stderr)
            return

        info = extract_scenario_info(
            first_page_text=doc[0].get_text(),
            page3_text=_get_page_text(doc, 2),
            page4_text=_get_page_text(doc, 3),
            page5_text=_get_page_text(doc, 4),
            last_page_text=doc[-1].get_text(),
        )
    finally:
        doc.close()

    if info is None:
        print(
            f"Warning: no scenario info found in {entry.name}",
            file=sys.stderr,
        )
        return

    out_path = build_output_path(output_dir, info)
    extract_last_page(Path(entry.path), out_path)
    print(out_path)


def process_directory(input_dir: Path, output_dir: Path) -> None:
    """Process all scenario PDFs in a directory.

    Iterates over immediate children of input_dir, filters for
    scenario PDFs, extracts scenario info, builds output paths,
    and extracts chronicle pages. Prints feedback to stdout/stderr.

    Args:
        input_dir: Directory containing scenario PDFs.
        output_dir: Base directory for output chronicle PDFs.

    Requirements: chronicle-extractor 6.1, 6.2, 6.3, 6.4, 7.1
    """
    with os.scandir(input_dir) as entries:
        for entry in entries:
            if not is_scenario_pdf(entry):
                print(f"Skipping: {entry.name}", file=sys.stderr)
                continue
            try:
                _process_single_entry(entry, output_dir)
            except RuntimeError as exc:
                print(
                    f"Error processing {entry.name}: {exc}",
                    file=sys.stderr,
                )

