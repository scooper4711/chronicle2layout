# Implementation Plan: Scenario Renamer

## Overview

Incremental implementation of the scenario renamer CLI utility. Each task builds on the previous, starting with pure-function modules (classifier, image parser, filename construction), then layering in the processor orchestrator and CLI wiring. Property-based tests validate correctness properties from the design; unit tests cover edge cases and integration with real scenario PDFs from the `Scenarios/` directory. The utility reuses `ScenarioInfo`, `extract_scenario_info`, `sanitize_name`, `is_scenario_pdf`, and `is_map_pdf` from the `chronicle_extractor` package.

## Tasks

- [x] 1. Set up project structure and module stubs
  - [x] 1.1 Create package and module stubs
    - Create `scenario_renamer/__init__.py` (empty package marker)
    - Create `scenario_renamer/__main__.py`, `processor.py`, `filename.py`, `image_parser.py`, `classifier.py` as modules with module-level docstrings and placeholder function signatures
    - Create `tests/scenario_renamer/` directory with empty `conftest.py`
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 2. Implement file classification
  - [x] 2.1 Implement `has_scenario_pattern` and `classify_file` in `classifier.py`
    - Define `IMAGE_EXTENSIONS` set, `PZOPFS_PREFIX` and `SEASON_NUMBER_PREFIX` regex constants
    - `has_scenario_pattern` checks if a stem contains a PZOPFS or season-number pattern
    - `classify_file` returns `('scenario_pdf', rel_path)`, `('scenario_image', rel_path)`, `('as_is', rel_path)`, or `('skip', rel_path)` based on extension and stem patterns
    - Import `is_map_pdf` from `chronicle_extractor.filters`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 9.3_

  - [ ]* 2.2 Write property test for file classification by extension and pattern
    - **Property 1: File classification by extension and pattern**
    - **Validates: Requirements 2.1, 2.2, 2.4, 2.5**
    - Create `tests/scenario_renamer/test_classifier_pbt.py`
    - Generate filenames with various extensions and stem patterns; assert classification matches expected rules

  - [ ]* 2.3 Write property test for scenario image detection by pattern
    - **Property 7: Scenario image detection by pattern**
    - **Validates: Requirements 2.2, 13.1**
    - In `tests/scenario_renamer/test_classifier_pbt.py`, generate image filenames with/without PZOPFS or season-number patterns; assert `'scenario_image'` vs `'as_is'` classification

  - [x] 2.4 Write unit tests for classifier
    - Create `tests/scenario_renamer/test_classifier.py`
    - Test concrete examples: `PZOPFS0107E.pdf` (scenario_pdf), `PZOPFS0107E Maps.pdf` (scenario_image), `2-03-Map-1.jpg` (scenario_image), `random-photo.jpg` (as_is), `notes.txt` (skip), `PZOPFS0409 A-Nighttime Ambush.jpg` (scenario_image), `PFS 2-21 Map 1.jpg` (scenario_image)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 13.1, 13.2_

- [x] 3. Implement image filename pattern extraction
  - [x] 3.1 Implement `ImageScenarioId` dataclass and `extract_image_scenario_id` in `image_parser.py`
    - Define `PZOPFS_PATTERN` and `SEASON_NUMBER_PATTERN` regex constants
    - Define `ImageScenarioId` frozen dataclass with `season`, `scenario`, `suffix` fields
    - `extract_image_scenario_id` tries PZOPFS first, then season-number; extracts suffix as remainder after identifier
    - _Requirements: 13.3, 13.4, 13.5, 13.6, 13.7, 13.8_

  - [ ]* 3.2 Write property test for PZOPFS extraction round trip
    - **Property 4: PZOPFS pattern extraction round trip**
    - **Validates: Requirements 13.3, 13.4**
    - Create `tests/scenario_renamer/test_image_parser_pbt.py`
    - Generate two-digit season (01-99) and scenario (00-99); construct `"PZOPFS{ss}{nn}E Maps"` stem; assert extracted season, scenario, and suffix match

  - [ ]* 3.3 Write property test for season-number extraction round trip
    - **Property 5: Season-number pattern extraction round trip**
    - **Validates: Requirements 13.5, 13.6**
    - In `tests/scenario_renamer/test_image_parser_pbt.py`, generate season (1-9) and two-digit scenario (00-99); construct `"{X}-{YY}-Map-1"` stem; assert extracted values match

  - [ ]* 3.4 Write property test for unrecognized stems
    - **Property 6: Unrecognized stems return None**
    - **Validates: Requirements 13.8**
    - In `tests/scenario_renamer/test_image_parser_pbt.py`, generate strings without PZOPFS or digit-dash-two-digits patterns; assert `extract_image_scenario_id` returns `None`

  - [x] 3.5 Write unit tests for image parser
    - Create `tests/scenario_renamer/test_image_parser.py`
    - Test concrete stems: `"PZOPFS0107E Maps"`, `"PZOPFS0409 A-Nighttime Ambush"`, `"2-03-Map-1"`, `"PFS 2-21 Map 1"`, `"random-image"`, `"PZOPFS0101E"` (no suffix)
    - _Requirements: 13.3, 13.4, 13.5, 13.6, 13.7, 13.8_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement output filename construction
  - [x] 5.1 Implement `subdirectory_for_season`, `build_scenario_filename`, `sanitize_image_suffix`, and `build_image_filename` in `filename.py`
    - `subdirectory_for_season` returns `"Season X"`, `"Quests"`, or `"Bounties"` based on season number
    - `build_scenario_filename` constructs `"{season}-{scenario}-{SanitizedName}.pdf"`, `"Q{scenario}-{SanitizedName}.pdf"`, or `"B{scenario}-{SanitizedName}.pdf"`
    - `sanitize_image_suffix` removes spaces and unsafe characters while preserving hyphens
    - `build_image_filename` constructs `"{season}-{scenario}-{SanitizedName}{SanitizedSuffix}.{ext}"`
    - Import `sanitize_name` from `chronicle_extractor.filename` and `_BOUNTY_SEASON` from `chronicle_extractor.parser`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 9.2, 14.1, 14.2, 14.3_

  - [ ]* 5.2 Write property test for subdirectory selection
    - **Property 2: Subdirectory selection by season number**
    - **Validates: Requirements 6.1, 6.2, 6.3**
    - Create `tests/scenario_renamer/test_filename_pbt.py`
    - Generate positive integers; assert `subdirectory_for_season` returns `"Season {n}"`; assert season=0 → `"Quests"`, season=-1 → `"Bounties"`

  - [ ]* 5.3 Write property test for scenario filename construction
    - **Property 3: Scenario filename construction**
    - **Validates: Requirements 5.1, 5.2, 5.3**
    - In `tests/scenario_renamer/test_filename_pbt.py`, generate valid `ScenarioInfo` instances; assert filename matches expected format and never contains `"Chronicle"`

  - [ ]* 5.4 Write property test for image filename construction
    - **Property 8: Image filename construction**
    - **Validates: Requirements 14.1, 14.2, 14.3**
    - In `tests/scenario_renamer/test_filename_pbt.py`, generate season, scenario, sanitized name, suffix, and extension; assert output format matches `"{season}-{scenario}-{name}{suffix}.{ext}"`

  - [ ]* 5.5 Write property test for image suffix sanitization
    - **Property 9: Image suffix sanitization**
    - **Validates: Requirements 14.2**
    - In `tests/scenario_renamer/test_filename_pbt.py`, generate suffix strings; assert output has no spaces or unsafe characters, and hyphens are preserved

  - [x] 5.6 Write unit tests for filename construction
    - Create `tests/scenario_renamer/test_filename.py`
    - Test `subdirectory_for_season` with seasons 1, 5, 0, -1
    - Test `build_scenario_filename` with Season 1 Scenario 01, Quest 14, Bounty 1
    - Test `sanitize_image_suffix` with `"Maps"`, `"A-Nighttime Ambush"`, `"Map 1"`, `""` (empty)
    - Test `build_image_filename` with concrete examples from the design
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 14.1, 14.2, 14.3_

- [x] 6. Implement processor orchestrator
  - [x] 6.1 Implement `scan_and_classify` in `processor.py`
    - Recursively walk the input directory tree using `Path.rglob('*')`
    - Skip non-files (directories, symlinks)
    - Classify each file using `classify_file` from `classifier.py`
    - Return three sorted lists: scenario PDFs, scenario images, as-is files
    - Print skip messages to stderr for files with `'skip'` classification
    - _Requirements: 2.3, 2.4, 7.1, 7.2, 15.2, 8.3_

  - [x] 6.2 Implement `copy_as_is` in `processor.py`
    - Copy file to `output_dir / relative_path` using `shutil.copy2`
    - Create parent directories as needed
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

  - [ ]* 6.3 Write property test for as-is copy path preservation
    - **Property 10: As-is copy preserves relative path**
    - **Validates: Requirements 16.4**
    - Create `tests/scenario_renamer/test_processor_pbt.py`
    - Generate nested relative paths; assert `copy_as_is` produces `output_dir / relative_path`

  - [x] 6.4 Implement `process_scenario_pdf` in `processor.py`
    - Open PDF with PyMuPDF, extract page texts, call `extract_scenario_info`
    - If extraction succeeds: build filename, copy with `shutil.copy2`, populate lookup table
    - If extraction fails: copy as-is, log warning to stderr
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 8.1, 8.4, 9.1, 12.2, 12.3, 12.4_

  - [x] 6.5 Implement `process_scenario_image` in `processor.py`
    - Call `extract_image_scenario_id` to parse filename pattern
    - Look up (season, scenario) in lookup table
    - If found: build image filename with sanitized suffix, copy to season subdirectory
    - If not found or no pattern: copy as-is, log warning to stderr
    - _Requirements: 13.8, 14.1, 14.2, 14.3, 14.4, 14.5, 8.2, 8.5_

  - [x] 6.6 Implement `process_directory` in `processor.py`
    - Orchestrate two-pass processing: scan → process PDFs → process images → copy as-is files
    - _Requirements: 12.1, 15.1, 15.2, 15.3, 8.6_

  - [x] 6.7 Write unit tests for processor
    - Create `tests/scenario_renamer/test_processor.py`
    - Test `scan_and_classify` with a temp directory containing mixed file types
    - Test `copy_as_is` preserves relative path in temp directories
    - Test `process_scenario_pdf` with real PDFs from `Scenarios/` (if available) or mocked PyMuPDF
    - Test `process_scenario_image` with lookup table populated and unpopulated
    - Test `process_directory` end-to-end with temp directory structure
    - Test error handling: corrupt PDF, copy failure
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 7.1, 7.2, 7.3, 12.1, 12.2, 12.3, 12.4, 15.1, 15.2, 15.3, 16.1, 16.5_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement CLI entry point
  - [x] 8.1 Implement `parse_args` and `main` in `__main__.py`
    - `parse_args` uses argparse with required `--input-dir` and `--output-dir` arguments, returns `Namespace` with `Path` objects
    - `main` validates input dir exists (exit 1 if not), creates output dir, delegates to `process_directory`, returns exit code
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 8.2 Write CLI integration tests
    - Create `tests/scenario_renamer/test_cli.py`
    - Test missing `--input-dir` exits with non-zero code and stderr message
    - Test non-existent `--input-dir` exits with code 1
    - Test `--output-dir` creation when it doesn't exist
    - Test successful invocation with empty input directory
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 9. Create project documentation
  - [x] 9.1 Create `scenario_renamer/README.md`
    - Describe purpose, CLI arguments (`--input-dir`, `--output-dir`), usage example, two-pass processing overview, and dependency on `chronicle_extractor`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 9.2 Update top-level `README.md`
    - Add Scenario Renamer to the utilities table with relative link to `scenario_renamer/README.md`
    - _Requirements: 11.1_

- [x] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1-10)
- Unit tests validate specific examples and edge cases
- All code follows Google-style docstrings, type hints required, per project Python standards
- The utility reuses `ScenarioInfo`, `extract_scenario_info`, `sanitize_name`, `is_scenario_pdf`, and `is_map_pdf` from `chronicle_extractor` — no duplication of shared logic
- Pure-function modules (tasks 2, 3, 5) are implemented and tested first to build a solid foundation before the orchestrator (task 6)
