"""Orchestrator for scenario file processing.

Coordinates the two-pass processing strategy: scanning and classifying
files, processing scenario PDFs to build the lookup table, then
processing scenario images using the lookup table. Handles file
copying and error reporting.

Key public functions:
    scan_and_classify: Recursively scan and classify files.
    process_scenario_pdf: Extract info, copy, and populate lookup.
    process_scenario_image: Parse filename, lookup, and copy.
    copy_as_is: Copy a file preserving relative path.
    process_directory: Orchestrate full two-pass processing.
"""

import shutil
import sys
from pathlib import Path

import fitz

from chronicle_extractor.filename import sanitize_name
from chronicle_extractor.parser import ScenarioInfo, extract_scenario_info

from scenario_renamer.classifier import classify_file
from scenario_renamer.filename import (
    build_image_filename,
    build_scenario_filename,
    sanitize_image_suffix,
    subdirectory_for_season,
)
from scenario_renamer.image_parser import extract_image_scenario_id

# Type alias for the scenario lookup table
ScenarioLookup = dict[tuple[int, str], str]


def scan_and_classify(
    input_dir: Path,
) -> tuple[list[Path], list[Path], list[Path]]:
    """Recursively scan the input directory and classify files.

    Walks the directory tree and classifies each regular file as
    a scenario PDF, scenario image, or as-is file. Prints skip
    messages to stderr for files with 'skip' classification.

    Args:
        input_dir: Root directory to scan.

    Returns:
        A tuple of (scenario_pdfs, scenario_images, as_is_files) where
        each is a sorted list of absolute file paths.

    Requirements: scenario-renamer 7.1, 7.2, 15.2, 8.3
    """
    scenario_pdfs: list[Path] = []
    scenario_images: list[Path] = []
    as_is_files: list[Path] = []

    for path in input_dir.rglob("*"):
        if not path.is_file():
            continue

        classification, rel = classify_file(path, input_dir)

        if classification == "scenario_pdf":
            scenario_pdfs.append(path)
        elif classification == "scenario_image":
            scenario_images.append(path)
        elif classification == "as_is":
            as_is_files.append(path)
        else:
            print(f"Skipping {rel}: unsupported file type", file=sys.stderr)

    return sorted(scenario_pdfs), sorted(scenario_images), sorted(as_is_files)


def copy_as_is(
    file_path: Path,
    input_dir: Path,
    output_dir: Path,
) -> Path:
    """Copy a file to the output directory preserving its relative path.

    Args:
        file_path: Absolute path to the source file.
        input_dir: Root input directory.
        output_dir: Base output directory.

    Returns:
        The output path where the file was copied.

    Requirements: scenario-renamer 16.1, 16.2, 16.3, 16.4, 16.5
    """
    output_path = output_dir / file_path.relative_to(input_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, output_path)
    return output_path


def process_scenario_pdf(
    pdf_path: Path,
    input_dir: Path,
    output_dir: Path,
    lookup: ScenarioLookup,
) -> None:
    """Process a single scenario PDF: extract info, copy, populate lookup.

    Opens the PDF with PyMuPDF, extracts scenario info, copies the
    file to the appropriate output location, and adds the entry to
    the lookup table.

    If extraction fails, copies the file as-is preserving relative path.

    Args:
        pdf_path: Path to the scenario PDF.
        input_dir: Root input directory (for relative path computation).
        output_dir: Base output directory.
        lookup: The scenario lookup table to populate (mutated in place).

    Requirements: scenario-renamer 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 12.2, 12.3
    """
    rel = pdf_path.relative_to(input_dir)

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        print(f"Error reading {rel}: {exc}", file=sys.stderr)
        return

    try:
        first_page_text = doc[0].get_text() if len(doc) > 0 else ""
        page3_text = doc[2].get_text() if len(doc) > 2 else None
        page4_text = doc[3].get_text() if len(doc) > 3 else None
        page5_text = doc[4].get_text() if len(doc) > 4 else None
        last_page_text = doc[-1].get_text() if len(doc) > 1 else None

        info = extract_scenario_info(
            first_page_text, page3_text, page4_text, page5_text, last_page_text
        )
    except Exception as exc:
        print(f"Error reading {rel}: {exc}", file=sys.stderr)
        return
    finally:
        doc.close()

    if info is None:
        as_is_path = copy_as_is(pdf_path, input_dir, output_dir)
        print(
            f"Warning: no scenario info in {rel}, copied as-is to {as_is_path}",
            file=sys.stderr,
        )
        return

    filename = build_scenario_filename(info)
    subdir = subdirectory_for_season(info.season)
    output_path = output_dir / subdir / filename

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, output_path)
    except OSError as exc:
        print(f"Error copying {rel}: {exc}", file=sys.stderr)
        return

    lookup[(info.season, info.scenario)] = sanitize_name(info.name)
    print(output_path)


def process_scenario_image(
    image_path: Path,
    input_dir: Path,
    output_dir: Path,
    lookup: ScenarioLookup,
) -> None:
    """Process a single scenario image: parse filename, lookup, copy.

    Extracts the scenario identifier and suffix from the filename,
    looks up the (season, scenario) pair in the lookup table, and
    copies with the constructed filename including the sanitized suffix.

    If no pattern matches or lookup fails, copies as-is preserving
    relative path.

    Args:
        image_path: Path to the scenario image file.
        input_dir: Root input directory (for relative path computation).
        output_dir: Base output directory.
        lookup: The populated scenario lookup table.

    Requirements: scenario-renamer 13.8, 14.1, 14.4, 14.5, 8.2, 8.5
    """
    rel = image_path.relative_to(input_dir)

    result = extract_image_scenario_id(image_path.stem)
    if result is None:
        as_is_path = copy_as_is(image_path, input_dir, output_dir)
        print(
            f"Warning: no scenario pattern in {rel}, copied as-is to {as_is_path}",
            file=sys.stderr,
        )
        return

    sanitized_name = lookup.get((result.season, result.scenario))
    if sanitized_name is None:
        as_is_path = copy_as_is(image_path, input_dir, output_dir)
        print(
            f"Warning: unresolved scenario {result.season}-{result.scenario} "
            f"for {rel}, copied as-is to {as_is_path}",
            file=sys.stderr,
        )
        return

    sanitized_suffix = sanitize_image_suffix(result.suffix)
    extension = image_path.suffix.lstrip(".").lower()
    filename = build_image_filename(
        result.season, result.scenario, sanitized_name, sanitized_suffix, extension
    )
    subdir = subdirectory_for_season(result.season)
    output_path = output_dir / subdir / filename

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(image_path, output_path)
    except OSError as exc:
        print(f"Error copying {rel}: {exc}", file=sys.stderr)
        return

    print(output_path)


def process_directory(input_dir: Path, output_dir: Path) -> None:
    """Process all files in the input directory tree.

    Executes the two-pass strategy:
    1. Scan and classify all files.
    2. Process scenario PDFs (building lookup table).
    3. Process scenario images (using lookup table).
    4. Copy as-is files.

    Args:
        input_dir: Root input directory.
        output_dir: Base output directory.

    Requirements: scenario-renamer 15.1, 15.2, 15.3, 12.1, 8.6
    """
    scenario_pdfs, scenario_images, as_is_files = scan_and_classify(input_dir)
    lookup: ScenarioLookup = {}

    for pdf_path in scenario_pdfs:
        process_scenario_pdf(pdf_path, input_dir, output_dir, lookup)

    for image_path in scenario_images:
        process_scenario_image(image_path, input_dir, output_dir, lookup)

    for file_path in as_is_files:
        as_is_path = copy_as_is(file_path, input_dir, output_dir)
        rel = file_path.relative_to(input_dir)
        print(
            f"Warning: unclassified file {rel}, copied as-is to {as_is_path}",
            file=sys.stderr,
        )
