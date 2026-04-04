# Implementation Plan: Chronicle Blueprints (blueprint2layout)

## Overview

Incremental implementation of the `blueprint2layout` Python CLI tool and library. Each task builds on the previous, starting with data models, then layering in detection logic, Blueprint parsing/inheritance, edge resolution, coordinate conversion, layout assembly, and CLI wiring. The pipeline converts Blueprint JSON files + chronicle PDFs into layout.json files by detecting structural elements via pixel analysis and resolving declarative canvas edge references.

## Tasks

- [x] 1. Set up project structure and data models
  - [x] 1.1 Create package and module stubs
    - Create `blueprint2layout/__init__.py`, `__main__.py`, `pdf_preparation.py`, `detection.py`, `blueprint.py`, `resolver.py`, `converter.py`, `output.py`, `models.py` as modules with module-level docstrings
    - Create `tests/blueprint2layout/` directory with empty `conftest.py`
    - _Requirements: 13.1_

  - [x] 1.2 Implement data models in `models.py`
    - Define frozen dataclasses: `HorizontalLine`, `VerticalLine`, `GreyBox`, `DetectionResult`, `CanvasEntry`, `ResolvedCanvas`, `Blueprint` per the design
    - Include type hints and Google-style docstrings
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 2. Implement PDF page preparation
  - [x] 2.1 Implement `prepare_page` in `pdf_preparation.py`
    - Open last page of PDF using PyMuPDF
    - Redact all text blocks and embedded images
    - Render cleaned page at 150 DPI
    - Return grayscale and RGB numpy arrays
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 2.2 Write unit tests for PDF page preparation
    - Create `tests/blueprint2layout/test_pdf_preparation.py`
    - Test with a real chronicle PDF from `Chronicles/` directory
    - Verify returned arrays have correct shapes and dtypes (grayscale 2D, RGB 3D with 3 channels)
    - Test `FileNotFoundError` for missing PDF path
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3. Implement horizontal black line detection
  - [x] 3.1 Implement `detect_horizontal_black_lines` in `detection.py`
    - Define detection constants: `BLACK_PIXEL_THRESHOLD`, `THIN_LINE_MAX_THICKNESS`, `HORIZONTAL_MIN_WIDTH_RATIO`, `LINE_GROUPING_TOLERANCE`
    - Scan rows for black pixel runs > 5% page width
    - Group consecutive qualifying rows within 5px tolerance
    - Classify as thin (≤ 5px) or bar (> 5px)
    - Return sorted `(h_thin, h_bar)` lists
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 3.2 Write unit tests for horizontal black line detection
    - Create `tests/blueprint2layout/test_detection.py`
    - Test with synthetic grayscale images containing known horizontal lines
    - Verify thin/bar classification by thickness threshold
    - Verify sorting by y ascending
    - Verify percentage coordinate computation
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4. Implement vertical black line detection and grey detection
  - [x] 4.1 Implement `detect_vertical_black_lines` in `detection.py`
    - Define `VERTICAL_MIN_HEIGHT_RATIO` constant
    - Scan columns for black pixel runs > 3% page height
    - Group and classify as thin/bar, sorted by x ascending
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 4.2 Implement `detect_grey_rules` in `detection.py`
    - Define `GREY_RULE_GROUPING_TOLERANCE`, `GREY_RULE_MIN_VALUE`, `GREY_RULE_MAX_VALUE`, `GREY_RULE_DEDUP_TOLERANCE` constants
    - Scan rows for medium-grey pixel runs (grayscale 50–200) > 5% page width
    - Group within 3px tolerance
    - Deduplicate against h_thin and h_bar (discard if y within 0.5% of any black line)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 4.3 Implement `detect_grey_boxes` in `detection.py`
    - Define `GREY_BOX_MIN_CHANNEL`, `GREY_BOX_MAX_CHANNEL`, `GREY_BOX_CHANNEL_DIFF_LIMIT`, `GREY_BOX_BLOCK_SIZE`, `GREY_BOX_BLOCK_FILL_THRESHOLD`, `GREY_BOX_MIN_BLOCKS`, `GREY_BOX_MIN_AREA` constants
    - Identify structural grey pixels (RGB 220–240, channel diff < 8)
    - Grid-based flood fill on 10×10 blocks, filter by min blocks and min area
    - Refine bounding boxes at pixel level
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 4.4 Implement `detect_structures` orchestrator in `detection.py`
    - Call all four detection functions and assemble `DetectionResult`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 4.5 Write unit tests for vertical and grey detection
    - Add tests to `tests/blueprint2layout/test_detection.py`
    - Test vertical detection with synthetic images
    - Test grey rule detection with deduplication against black lines
    - Test grey box detection with synthetic RGB images containing grey rectangles
    - Test `detect_structures` assembles all six arrays correctly
    - _Requirements: 3.1–3.6, 4.1–4.5, 5.1–5.7, 6.1–6.6_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Blueprint parsing and inheritance
  - [x] 6.1 Implement `parse_blueprint` in `blueprint.py`
    - Validate required fields (`id`, `canvases`)
    - Convert each canvas entry dict into `CanvasEntry` dataclass
    - Validate edge values are numeric or string
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 6.2 Implement `build_blueprint_index` in `blueprint.py`
    - Scan directory recursively for `.json` files
    - Parse `id` field from each and build id-to-path map
    - _Requirements: 8.3_

  - [x] 6.3 Implement `load_blueprint_with_inheritance` in `blueprint.py`
    - Recursively load parent Blueprints via id lookup
    - Detect circular references
    - Validate no duplicate canvas names across inheritance chain
    - Return target Blueprint + ordered inherited canvases (root-first)
    - _Requirements: 7.4, 7.5, 7.6, 8.1, 8.2, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

  - [x] 6.4 Write unit tests for Blueprint parsing and inheritance
    - Create `tests/blueprint2layout/test_blueprint.py`
    - Test `parse_blueprint` with valid and invalid JSON dicts
    - Test `build_blueprint_index` with temp directory of Blueprint files
    - Test `load_blueprint_with_inheritance`: single Blueprint (no parent), parent-child chain, circular reference error, duplicate canvas name error, unknown parent id error
    - _Requirements: 7.1–7.6, 8.1–8.9_

- [x] 7. Implement edge value resolution
  - [x] 7.1 Implement `resolve_edge_value` in `resolver.py`
    - Define `LINE_REFERENCE_PATTERN` and `CANVAS_REFERENCE_PATTERN` regex constants
    - Handle numeric literals (return as float)
    - Handle line references: parse category and index, look up primary-axis value
    - Handle canvas references: parse canvas name and edge, look up resolved value
    - Raise descriptive errors for unknown categories, out-of-bounds indices, unresolved canvases
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 7.2 Implement `resolve_canvases` in `resolver.py`
    - Process inherited canvases first, then target canvases in array order
    - Resolve each canvas's four edges via `resolve_edge_value`
    - Enforce backward-only canvas references
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 7.3 Write unit tests for edge value resolution
    - Create `tests/blueprint2layout/test_resolver.py`
    - Test `resolve_edge_value` with numeric, line reference, and canvas reference inputs
    - Test error cases: unknown category, out-of-bounds index, forward reference
    - Test `resolve_canvases` with inherited + target canvases, verify backward-only enforcement
    - _Requirements: 9.1–9.6, 10.1–10.4_

- [x] 8. Implement parent-relative coordinate conversion
  - [x] 8.1 Implement `convert_to_parent_relative` in `converter.py`
    - Compute x, y, x2, y2 relative to parent canvas bounds
    - Use absolute percentages directly for canvases without a parent
    - Round all values to 1 decimal place
    - Raise error for unknown parent canvas name
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

  - [x] 8.2 Write unit tests for coordinate conversion
    - Create `tests/blueprint2layout/test_converter.py`
    - Test conversion with parent: verify formula produces correct relative percentages
    - Test conversion without parent: verify absolute percentages pass through
    - Test rounding to 1 decimal place
    - Test unknown parent name raises error
    - _Requirements: 11.1–11.8_

- [x] 9. Implement layout assembly and output
  - [x] 9.1 Implement `assemble_layout` in `output.py`
    - Build layout dict with `id`, optional `parent`, and `canvas` section
    - Include only target Blueprint's own canvases (not inherited)
    - Convert each canvas to parent-relative percentages via `convert_to_parent_relative`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 9.2 Implement `write_layout` in `output.py`
    - Write layout dict to JSON file with 2-space indentation
    - _Requirements: 12.6, 12.7, 12.8_

  - [x] 9.3 Write unit tests for layout assembly and output
    - Create `tests/blueprint2layout/test_output.py`
    - Test `assemble_layout` includes only target canvases, not inherited
    - Test `assemble_layout` includes parent id when Blueprint has parent
    - Test `write_layout` produces valid JSON with 2-space indent
    - Test round-trip: serialize and deserialize produces equal dict
    - _Requirements: 12.1–12.8, 14.1, 14.2, 14.3_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement public API and CLI entry point
  - [x] 11.1 Implement `generate_layout` in `__init__.py`
    - Wire the full pipeline: prepare_page → detect_structures → load_blueprint_with_inheritance → resolve_canvases → convert_to_parent_relative → assemble_layout
    - Accept blueprint_path, pdf_path, optional blueprints_dir
    - Default blueprints_dir to the directory containing blueprint_path
    - Raise `FileNotFoundError` for missing files, `ValueError` for invalid PDF/Blueprint
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 11.2 Implement `parse_args` and `main` in `__main__.py`
    - `parse_args`: three positional args (blueprint, pdf, output) + optional `--blueprints-dir`
    - `main`: validate args, call `generate_layout`, call `write_layout`, handle errors to stderr, return exit code
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [x] 11.3 Write CLI integration tests
    - Create `tests/blueprint2layout/test_cli.py`
    - Test missing arguments prints usage and exits non-zero
    - Test missing Blueprint file exits non-zero with error message
    - Test missing PDF file exits non-zero with error message
    - _Requirements: 13.1–13.5_

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Remove season_layout_generator package
  - [x] 13.1 Remove old package and related files
    - Delete `season_layout_generator/` package directory and all modules
    - Delete `tests/season_layout_generator/` test directory and all test modules
    - Delete `clip_canvases.py` script
    - Delete `.kiro/specs/season-layout-generator/` spec directory
    - Remove or update any imports from `season_layout_generator` in other files
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All unit test tasks are mandatory
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- The design uses Python explicitly — all code uses Python with type hints and Google-style docstrings
- Detection logic (tasks 3–4) uses numpy for pixel analysis; PIL handles image loading
- Task 13 (remove season_layout_generator) should be a separate commit per Requirement 16
- All dataclasses are frozen for immutability
- Detection constants are defined as module-level named constants in `detection.py`
