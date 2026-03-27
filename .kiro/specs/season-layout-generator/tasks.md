# Implementation Plan: Season Layout Generator

## Overview

Incremental implementation of the season layout generator CLI utility. Each task builds on the previous, starting with data models and pure functions (collection name extraction, consensus computation, layout JSON construction), then layering in PDF text and image detection, region merging, the pipeline orchestrator, and CLI wiring. Property-based tests validate correctness properties from the design; unit tests cover edge cases and integration with real chronicle PDFs.

## Tasks

- [x] 1. Set up project structure and data models
  - [x] 1.1 Create package and module stubs
    - Create `season_layout_generator/__init__.py` (empty package marker)
    - Create `season_layout_generator/__main__.py`, `pipeline.py`, `collection.py`, `text_detection.py`, `image_detection.py`, `region_merge.py`, `consensus.py`, `layout_builder.py`, `models.py` as modules with module-level docstrings
    - Create `tests/season_layout_generator/` directory with empty `conftest.py`
    - _Requirements: 22.1_

  - [x] 1.2 Implement data models in `models.py`
    - Define `CanvasCoordinates`, `PageRegions`, `PdfAnalysisResult`, and `VariantGroup` frozen dataclasses per the design
    - Include type hints and Google-style docstrings
    - _Requirements: 4.2, 5.2, 6.2, 7.2, 8.2, 9.2, 10.2, 11.2, 12.2_

- [x] 2. Implement collection name extraction
  - [x] 2.1 Implement `extract_collection_name` in `collection.py`
    - Define `SEASON_PATTERN` regex constant
    - Handle `Season X`, `Quests` (case-insensitive), `Bounties` (case-insensitive)
    - Raise `ValueError` for unrecognized directory names
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.2 Write property test for season number round trip
    - **Property 1: Season number extraction round trip**
    - **Validates: Requirements 2.1**
    - Create `tests/season_layout_generator/test_collection_pbt.py`
    - Generate positive integers; assert `extract_collection_name(f"Season {X}")` returns `(str(X), X)`

  - [x] 2.3 Write property test for invalid directory names
    - **Property 2: Invalid directory names are rejected**
    - **Validates: Requirements 2.4**
    - In `tests/season_layout_generator/test_collection_pbt.py`, generate strings not matching known patterns; assert `ValueError` is raised

  - [x] 2.4 Write unit tests for collection name extraction
    - Create `tests/season_layout_generator/test_collection.py`
    - Test concrete examples: "Season 5", "Season 1", "Quests", "BOUNTIES", "quests", "Invalid", "Season", "Season -1"
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Implement consensus computation and variant grouping
  - [x] 3.1 Implement `compute_consensus` and `exceeds_divergence` in `consensus.py`
    - Define `DIVERGENCE_THRESHOLD` constant
    - `compute_consensus` takes list of `PageRegions`, returns median coordinates per region
    - `exceeds_divergence` checks if any coordinate exceeds threshold from consensus
    - _Requirements: 13.1, 13.2, 14.1, 14.2_

  - [x] 3.2 Implement `group_variants` in `consensus.py`
    - Process sorted `PdfAnalysisResult` list, split into `VariantGroup` instances when divergence exceeds threshold
    - First variant has no suffix; subsequent variants get alphabetical suffixes
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [x] 3.3 Write property test for valid coordinate ranges
    - **Property 4: Canvas coordinates are in valid percentage range**
    - **Validates: Requirements 4.2, 5.2, 6.2, 7.2, 8.2, 9.2, 10.2, 11.2, 12.2**
    - Create `tests/season_layout_generator/test_consensus_pbt.py`
    - Generate `PageRegions` with valid coordinates; assert all non-None fields have x/y in [0,100] and x < x2, y < y2

  - [x] 3.4 Write property test for median consensus
    - **Property 5: Median consensus computation**
    - **Validates: Requirements 13.2**
    - In `tests/season_layout_generator/test_consensus_pbt.py`, generate lists of `PageRegions`; assert consensus coordinates equal statistical median

  - [x] 3.5 Write property test for variant grouping splits
    - **Property 6: Variant grouping splits at divergence points**
    - **Validates: Requirements 14.1, 14.2**
    - In `tests/season_layout_generator/test_consensus_pbt.py`, generate ordered sequences of `PageRegions` with known divergence points; assert groups split correctly

  - [x] 3.6 Write unit tests for consensus and variant grouping
    - Create `tests/season_layout_generator/test_consensus.py`
    - Test: single PDF consensus, all-None regions, mixed presence, single variant (no splits), multiple variants, threshold boundary cases
    - _Requirements: 13.1, 13.2, 13.3, 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 4. Implement layout JSON construction
  - [x] 4.1 Implement `build_layout_json` in `layout_builder.py`
    - Construct JSON dict with `id`, `description`, `parent`, and `canvas` fields
    - Handle season numbers, Quests, Bounties collection names
    - Handle variant index 0 (no suffix) vs subsequent variants (alphabetical suffix)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8_

  - [x] 4.2 Implement `build_output_path` in `layout_builder.py`
    - Construct output file path based on collection name, season number, and variant index
    - Handle seasons (`Season X/SeasonX.json`) and Quests/Bounties paths
    - _Requirements: 15.9, 15.10, 15.11_

  - [ ]* 4.3 Write property test for variant suffix assignment
    - **Property 7: Variant suffix assignment**
    - **Validates: Requirements 14.3**
    - Create `tests/season_layout_generator/test_layout_builder_pbt.py`
    - Generate variant counts 1-26; assert first has no suffix, subsequent get a, b, c, ...

  - [ ]* 4.4 Write property test for layout JSON metadata
    - **Property 8: Layout JSON metadata construction**
    - **Validates: Requirements 15.1, 15.2, 15.5, 15.6**
    - In `tests/season_layout_generator/test_layout_builder_pbt.py`, generate season numbers and variant indices; assert `id`, `parent`, `description` fields are correct

  - [ ]* 4.5 Write property test for layout JSON canvas structure
    - **Property 9: Layout JSON canvas structure**
    - **Validates: Requirements 15.8**
    - In `tests/season_layout_generator/test_layout_builder_pbt.py`, generate `PageRegions` with at least `main`; assert `canvas` contains `page` at (0,0,100,100), `main`, and all non-None regions

  - [ ]* 4.6 Write property test for output path construction
    - **Property 10: Output path construction for seasons**
    - **Validates: Requirements 15.9**
    - In `tests/season_layout_generator/test_layout_builder_pbt.py`, generate season numbers and variant indices; assert path format matches expected pattern

  - [x] 4.7 Write unit tests for layout builder
    - Create `tests/season_layout_generator/test_layout_builder.py`
    - Test: season layout JSON for Season 5 (variant 0), Season 4 variant (variant 1+), Quests layout, Bounties layout, output paths with and without suffixes, JSON includes 4-space indentation
    - _Requirements: 15.1-15.12_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [-] 6. Implement text-based region detection
  - [x] 6.1 Implement `extract_text_regions` in `text_detection.py`
    - Use `page.get_text("dict")` to extract text blocks with bounding boxes
    - Search for characteristic labels: "Character Name", "Organized Play #", "Adventure Summary", "XP", "GP", "Event", "Date", "GM", "Notes", "Reputation"
    - Return dict mapping region names to `CanvasCoordinates` (percentage-based relative to page dimensions)
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8_

  - [x] 6.2 Write unit tests for text detection
    - Create `tests/season_layout_generator/test_text_detection.py`
    - Test with real chronicle PDFs from `Chronicles/` directory (at least one from Season 5+)
    - Verify detected regions are non-None for expected canvases
    - _Requirements: 17.1-17.8_

- [x] 7. Implement image-based region detection
  - [x] 7.1 Implement `extract_image_regions` in `image_detection.py`
    - Define constants: `BLACK_PIXEL_THRESHOLD`, `BLACK_BAR_MIN_FRACTION`, `GREY_LOWER_BOUND`, `GREY_UPPER_BOUND`, `MIN_REGION_HEIGHT_FRACTION`
    - Convert page to raster image via `page.get_pixmap()`, analyze with numpy
    - Detect black horizontal bars (Summary, Items top edges), thick black borders (Rewards, Items boundaries), grey backgrounds (Session Info)
    - Return dict mapping region names to `CanvasCoordinates`
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

  - [x] 7.2 Write unit tests for image detection
    - Create `tests/season_layout_generator/test_image_detection.py`
    - Test with real chronicle PDFs from `Chronicles/` directory
    - Verify black bar detection finds Summary and Items top edges
    - Verify grey background detection finds Session Info region
    - _Requirements: 16.1-16.5_

- [x] 8. Implement region merging
  - [x] 8.1 Implement `merge_regions` in `region_merge.py`
    - Combine text-based and image-based region detections
    - Prefer image-based boundaries for edge positions; use text-based for identity confirmation and fallback
    - Convert coordinates to percentage-based values relative to main canvas
    - _Requirements: 16.5, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2, 7.1, 7.2, 8.1, 8.2, 9.1, 9.2, 10.1, 10.2, 11.1, 11.2, 11.3, 12.1, 12.2_

  - [x] 8.2 Write unit tests for region merging
    - Create `tests/season_layout_generator/test_region_merge.py`
    - Test merging with both sources present, text-only fallback, image-only fallback, missing regions
    - Verify output coordinates are percentage-based and within [0, 100]
    - _Requirements: 16.5_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement pipeline orchestrator
  - [ ] 10.1 Implement `discover_pdfs` and `extract_scenario_id` in `pipeline.py`
    - `discover_pdfs` scans input directory for `.pdf` files (case-insensitive), skips non-files, returns sorted list
    - `extract_scenario_id` extracts scenario identifier (e.g., "5-08", "Q14") from filename
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 10.2 Write property test for PDF discovery filtering
    - **Property 3: PDF discovery filters by extension**
    - **Validates: Requirements 3.1**
    - Create `tests/season_layout_generator/test_pipeline_pbt.py`
    - Generate sets of filenames with mixed extensions in a temp directory; assert `discover_pdfs` returns exactly the `.pdf` files, sorted

  - [ ] 10.3 Implement `run_pipeline` in `pipeline.py`
    - Orchestrate: validate input dir → extract collection name → discover PDFs → analyze each PDF → group variants → compute consensus → build JSON → write output
    - Accept optional `debug_dir: Path | None` parameter; when provided, call `save_debug_images` for each PDF in each variant group after consensus is computed
    - Print progress to stdout (filename + detected regions per PDF, variant count, detection counts)
    - Print warnings to stderr (undetected regions, low detection counts)
    - Handle per-file errors gracefully (log to stderr, continue processing)
    - Create output directories as needed
    - _Requirements: 1.3, 1.4, 1.5, 13.1, 13.3, 13.4, 18.1, 18.2, 18.3, 18.4, 23.2, 23.4, 23.6_

  - [ ] 10.4 Write unit tests for pipeline
    - Create `tests/season_layout_generator/test_pipeline.py`
    - Test `discover_pdfs` with mixed file types in temp directory
    - Test `extract_scenario_id` with various filename patterns
    - Test `run_pipeline` error paths: missing input dir, empty directory, invalid directory name
    - _Requirements: 1.3, 1.4, 3.1, 3.2, 3.3_

- [ ] 11. Implement CLI entry point
  - [ ] 11.1 Implement `parse_args` and `main` in `__main__.py`
    - `parse_args` uses argparse with required `--input-dir` and `--output-dir` arguments, plus optional `--debug-dir` argument; returns `Namespace` with `Path` objects (`debug_dir` as `Path | None`)
    - `main` validates input dir exists (exit 1 if not), delegates to `run_pipeline` passing `debug_dir`, returns exit code
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 23.1, 23.6_

  - [ ] 11.2 Write CLI integration tests
    - Create `tests/season_layout_generator/test_cli.py`
    - Test missing input dir exits with code 1 and stderr message
    - Test output dir creation when it doesn't exist
    - Test invalid directory name exits with code 1
    - Test `--debug-dir` argument is accepted and passed through to pipeline
    - Test that omitting `--debug-dir` results in `None` for `debug_dir`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 23.1, 23.6_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Integration testing with real chronicle PDFs
  - [ ] 13.1 Write detection integration tests
    - Create `tests/season_layout_generator/test_detection_integration.py`
    - Run full detection pipeline on real chronicle PDFs from `Chronicles/Season 5/` and `Chronicles/Season 6/`
    - Compare generated canvas coordinates against reference layouts in `Layouts/` directory (±2 percentage point tolerance)
    - Verify all expected regions are detected for Season 5+ chronicles
    - _Requirements: 4.1, 4.2, 5.1, 5.2, 6.1, 6.2, 7.1, 7.2, 8.1, 8.2, 9.1, 9.2, 10.1, 10.2, 11.1, 11.2, 12.1, 12.2, 19.1, 19.2, 19.3_

  - [ ] 13.2 Write end-to-end CLI integration test
    - In `tests/season_layout_generator/test_cli.py`, run full CLI with a real season directory and temp output dir
    - Verify output JSON file is created with correct structure, 4-space indentation, and valid canvas coordinates
    - _Requirements: 15.8, 15.9, 15.12, 18.3_

- [ ] 14. Create project documentation
  - [ ] 14.1 Create `season_layout_generator/README.md`
    - Describe purpose, CLI arguments (`--input-dir`, `--output-dir`, `--debug-dir`), usage example, and detection methodology overview
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

  - [ ] 14.2 Update top-level `README.md`
    - Add Season Layout Generator to the utilities table with relative link to `season_layout_generator/README.md`
    - _Requirements: 21.1_

- [ ] 15. Implement debug canvas clipping output
  - [ ] 15.1 Create `debug_output.py` module stub
    - Create `season_layout_generator/debug_output.py` with module-level docstring and imports (`pathlib.Path`, `numpy`, `PIL.Image`, models)
    - _Requirements: 23.2_

  - [ ] 15.2 Implement `build_debug_image_path` in `debug_output.py`
    - Construct output path: `{debug_dir}/{collection_name}/{variant_name}/{pdf_filename}/{canvas_name}.png`
    - _Requirements: 23.3_

  - [ ] 15.3 Implement `save_debug_images` in `debug_output.py`
    - For each non-None region in `PageRegions`, clip the corresponding rectangle from the page raster image and save as PNG
    - Create directories as needed (`parents=True, exist_ok=True`)
    - Catch and log errors per image to stderr without interrupting processing
    - _Requirements: 23.2, 23.4, 23.5, 23.7_

  - [ ] 15.4 Write unit tests for `debug_output.py`
    - Create `tests/season_layout_generator/test_debug_output.py`
    - Test `build_debug_image_path` returns correct path structure
    - Test `save_debug_images` creates PNG files for each non-None region using a synthetic raster image
    - Test no files are created when all regions are None
    - Test error resilience: verify processing continues when a single image write fails
    - _Requirements: 23.2, 23.3, 23.4, 23.5, 23.7_

  - [ ]* 15.5 Write property test for debug clipping PNG output
    - **Property 11: Debug clipping produces one valid PNG per detected region**
    - **Validates: Requirements 23.2, 23.4**
    - Create `tests/season_layout_generator/test_debug_output_pbt.py`
    - Generate `PageRegions` with random non-None regions and a synthetic raster image; assert exactly N PNG files are produced for N non-None regions

  - [ ]* 15.6 Write property test for debug output path construction
    - **Property 12: Debug output path construction**
    - **Validates: Requirements 23.3**
    - In `tests/season_layout_generator/test_debug_output_pbt.py`, generate combinations of collection name, variant name, PDF filename, and canvas name; assert path matches `{debug_dir}/{collection_name}/{variant_name}/{pdf_filename}/{canvas_name}.png`

- [ ] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1-12)
- Unit tests validate specific examples and edge cases
- Integration tests compare against reference layouts in `Layouts/` with ±2 percentage point tolerance
- All code follows Google-style docstrings, type hints required, per project Python standards
- The detection modules (tasks 6-8) are the core complexity; pure-function modules (tasks 2-4) are tested first to build a solid foundation
- Task 15 (debug_output.py) is placed after integration testing and documentation so that the core pipeline is complete before adding debug output support
- Tasks 10.3 and 11.1 were updated to pass `debug_dir` through the pipeline and CLI respectively (Requirement 23)
