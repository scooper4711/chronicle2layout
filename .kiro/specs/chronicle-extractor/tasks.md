# Implementation Plan: Chronicle Extractor

## Overview

Incremental implementation of the chronicle extractor CLI utility. Each task builds on the previous, starting with project scaffolding and pure functions, then layering in PDF operations and CLI wiring. Property-based tests validate correctness properties from the design; unit tests cover edge cases and integration.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create `requirements.txt` at project root listing PyMuPDF, pytest, and hypothesis
  - Create `chronicle_extractor/__init__.py` (empty package marker)
  - Create `chronicle_extractor/filters.py`, `chronicle_extractor/parser.py`, `chronicle_extractor/filename.py`, `chronicle_extractor/extractor.py`, `chronicle_extractor/__main__.py` as empty modules with module-level docstrings
  - Create `tests/` directory with empty `conftest.py`
  - Install dependencies into `.venv` via `pip install -r requirements.txt`
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 2. Implement file filtering functions
  - [x] 2.1 Implement `is_pdf_file`, `is_map_pdf`, and `is_scenario_pdf` in `chronicle_extractor/filters.py`
    - `is_pdf_file` checks `.pdf` extension case-insensitively on an `os.DirEntry`
    - `is_map_pdf` checks if a filename stem ends with "Map" or "Maps" case-insensitively
    - `is_scenario_pdf` combines both checks: is a PDF file and not a map PDF
    - _Requirements: 2.1, 2.2, 2.3_

  - [x]* 2.2 Write property test for PDF extension filtering
    - **Property 1: PDF extension filtering**
    - **Validates: Requirements 2.1**
    - Create `tests/test_filters_pbt.py`
    - Use hypothesis to generate arbitrary filename strings; assert `is_pdf_file` returns True iff extension is `.pdf` (case-insensitive)

  - [x]* 2.3 Write property test for map PDF detection
    - **Property 2: Map PDF detection**
    - **Validates: Requirements 2.2**
    - In `tests/test_filters_pbt.py`, use hypothesis to generate stems; assert `is_map_pdf` returns True iff stem ends with "Map" or "Maps" (case-insensitive)

  - [x] 2.4 Write unit tests for filters
    - Create `tests/test_filters.py`
    - Test concrete examples: `.PDF`, `.Pdf`, `PZOPFS0204E MAPS.pdf`, `PZOPFS0207 C2 The Foals of Szuriel.jpg`, directory entries, symlinks
    - _Requirements: 2.1, 2.2, 2.3_

- [ ] 3. Implement scenario info extraction
  - [x] 3.1 Implement `ScenarioInfo` dataclass and `extract_scenario_info` in `chronicle_extractor/parser.py`
    - Define frozen dataclass with `season: int`, `scenario: str`, `name: str`
    - Compile `SCENARIO_PATTERN` regex for `#X-YY` followed by scenario name
    - `extract_scenario_info` searches first-page text, returns `ScenarioInfo` or `None`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x]* 3.2 Write property test for scenario info round trip
    - **Property 3: Scenario info extraction round trip**
    - **Validates: Requirements 3.2, 3.3**
    - Create `tests/test_parser_pbt.py`
    - Generate valid season (positive int), scenario (zero-padded two-digit string), and name (non-empty, no newlines); embed as `#X-YY Name` in text; assert extracted info matches originals

  - [x]* 3.3 Write property test for no-match returns None
    - **Property 4: No-match returns None**
    - **Validates: Requirements 3.4**
    - In `tests/test_parser_pbt.py`, generate text strings that do not contain `#X-YY` pattern; assert `extract_scenario_info` returns `None`

  - [x] 3.4 Write unit tests for parser
    - Create `tests/test_parser.py`
    - Test concrete examples: real first-page text snippets, edge cases (empty string, multi-line text, `#1-07 Flooded King's Court`)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement filename construction
  - [x] 5.1 Implement `sanitize_name` and `build_output_path` in `chronicle_extractor/filename.py`
    - `sanitize_name` removes spaces and `UNSAFE_CHARACTERS` from the scenario name, preserving letter casing
    - `build_output_path` constructs `output_dir/Season {season}/{season}-{scenario}-{sanitized}Chronicle.pdf`
    - _Requirements: 4.2, 5.1, 5.2, 5.3, 5.4_

  - [x]* 5.2 Write property test for sanitized name safety
    - **Property 5: Sanitized name contains no unsafe characters or spaces**
    - **Validates: Requirements 5.2, 5.3**
    - Create `tests/test_filename_pbt.py`
    - Generate arbitrary strings; assert output of `sanitize_name` contains no spaces and no characters from `UNSAFE_CHARACTERS`

  - [x]* 5.3 Write property test for sanitized name casing preservation
    - **Property 6: Sanitized name preserves letter casing**
    - **Validates: Requirements 5.4**
    - In `tests/test_filename_pbt.py`, generate arbitrary strings; assert every alphabetic character in `sanitize_name` output appears in the input with the same casing and in the same relative order

  - [x]* 5.4 Write property test for output filename format
    - **Property 7: Output filename format**
    - **Validates: Requirements 4.2, 5.1**
    - In `tests/test_filename_pbt.py`, generate valid `ScenarioInfo` instances; assert `build_output_path` produces a path matching `Season {season}/{season}-{scenario}-{sanitized}Chronicle.pdf`

  - [x] 5.5 Write unit tests for filename construction
    - Create `tests/test_filename.py`
    - Test concrete examples: names with apostrophes, colons, question marks; empty sanitized result; multi-digit seasons
    - _Requirements: 4.2, 5.1, 5.2, 5.3, 5.4_

- [ ] 6. Implement PDF page extraction
  - [x] 6.1 Implement `extract_last_page` in `chronicle_extractor/extractor.py`
    - Use PyMuPDF to open source PDF, copy last page into new document, save to output path
    - Create parent directories if they don't exist
    - Raise `RuntimeError` on PyMuPDF failures
    - _Requirements: 4.1, 4.3_

  - [x] 6.2 Write unit tests for extract_last_page
    - Create `tests/test_extractor.py`
    - Use a programmatically created multi-page PDF fixture (via PyMuPDF) in a temp directory
    - Verify output PDF has exactly one page and its content matches the last page of the source
    - Test error handling for corrupt/missing PDFs
    - _Requirements: 4.1, 4.3_

- [ ] 7. Implement process_directory orchestrator
  - [x] 7.1 Implement `process_directory` in `chronicle_extractor/extractor.py`
    - Iterate immediate children of input_dir using `os.scandir`
    - Filter with `is_scenario_pdf`, extract info with `extract_scenario_info`, build output path, extract last page
    - Print success messages to stdout, skip/warning/error messages to stderr
    - Continue processing on per-file errors
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1_

  - [x] 7.2 Write unit tests for process_directory
    - In `tests/test_extractor.py`, create a temp directory with a mix of PDFs (valid scenario, map PDF, non-PDF file, directory entry)
    - Verify correct files are processed, skipped files produce stderr output, output files land in correct season subdirectories
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1_

- [ ] 8. Implement CLI entry point
  - [x] 8.1 Implement `parse_args` and `main` in `chronicle_extractor/__main__.py`
    - `parse_args` uses argparse with required `--input-dir` and `--output-dir` arguments, returns `Namespace` with `Path` objects
    - `main` validates input_dir exists (exit 1 if not), creates output_dir, delegates to `process_directory`, returns exit code
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 8.2 Write CLI integration tests
    - Create `tests/test_cli.py`
    - Test missing input dir exits with code 1 and stderr message
    - Test output dir creation when it doesn't exist
    - Test end-to-end run with fixture PDFs in a temp directory
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Create project documentation
  - [x] 10.1 Create `chronicle_extractor/README.md`
    - Describe purpose, CLI arguments (`--input-dir`, `--output-dir`), usage example, and dependencies
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 10.2 Create `README.md` at project root
    - Describe overall project purpose, list Chronicle Extractor as first utility with relative link to `chronicle_extractor/README.md`
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All code follows Google-style docstrings, type hints required, per project Python standards
