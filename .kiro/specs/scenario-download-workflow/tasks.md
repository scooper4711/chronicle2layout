# Implementation Plan: Scenario Download Workflow

## Overview

Implement the `scenario_download_workflow` Python CLI package as a thin orchestration layer over the five existing PFS Tools utilities. The package has six modules (`duration.py`, `discovery.py`, `detection.py`, `routing.py`, `pipeline.py`, `__main__.py`) plus a README. Each module is implemented with its unit tests and property-based tests before moving to the next, ensuring incremental validation. Integration tests verify the full pipeline with mocked downstream tools.

## Tasks

- [x] 1. Create package structure and duration module
  - [x] 1.1 Create `scenario_download_workflow/` package directory with `__init__.py`
    - Create `scenario_download_workflow/__init__.py` (empty or minimal)
    - _Requirements: 1.1_

  - [x] 1.2 Implement `duration.py` — `parse_duration` function
    - Parse `<positive_int><m|h|d>` into `timedelta`
    - Raise `ValueError` for invalid inputs (empty string, zero, negative, unknown suffix)
    - _Requirements: 1.4, 1.8_

  - [x] 1.3 Write unit tests for `duration.py`
    - Test valid durations: `"1h"`, `"30m"`, `"2d"`, `"999d"`
    - Test invalid inputs: `""`, `"abc"`, `"0h"`, `"-1h"`, `"1x"`, `"h"`, `"3"`
    - _Requirements: 1.4, 1.8_

  - [x] 1.4 Write property test for duration parsing (Property 1)
    - **Property 1: Duration parsing round-trip for valid inputs**
    - Generate random positive ints + valid suffixes; verify correct `timedelta`
    - Generate random non-matching strings; verify `ValueError` raised
    - **Validates: Requirements 1.4, 1.8**

- [x] 2. Implement discovery module
  - [x] 2.1 Implement `discovery.py` — `discover_recent_pdfs` function
    - Scan top-level directory for `.pdf` files (case-insensitive extension)
    - Filter by modification time within recency window
    - Skip subdirectories (no recursion)
    - Return results sorted alphabetically by filename
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.2 Write unit tests for `discovery.py`
    - Test empty directory, no PDFs, mixed file types, `.PDF`/`.Pdf` extensions
    - Test recency boundary conditions (just inside, just outside window)
    - Test that subdirectories are excluded
    - Test alphabetical sort order
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.3 Write property test for PDF discovery (Property 2)
    - **Property 2: PDF discovery filters by extension and recency, and returns sorted results**
    - Generate random filesystem entries with various extensions and timestamps
    - Verify result contains exactly the files matching extension + recency criteria
    - Verify result is sorted alphabetically by filename
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

- [x] 3. Implement detection module
  - [x] 3.1 Implement `detection.py` — `GameSystem` enum, `detect_game_system`, and `system_prefix`
    - `GameSystem` enum with `PFS` and `SFS` values
    - `detect_game_system`: case-insensitive search for "Pathfinder Society" / "Starfinder Society", PFS takes precedence when both present, return `None` if neither found
    - `system_prefix`: return `"pfs2"` for PFS, `"sfs2"` for SFS
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.2 Write unit tests for `detection.py`
    - Test Pathfinder text, Starfinder text, neither, both (precedence), case variations
    - Test `system_prefix` for both enum values
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [x] 3.3 Write property test for game system detection (Property 4)
    - **Property 4: Game system detection is consistent with society string presence**
    - Generate random text with/without "Pathfinder Society" or "Starfinder Society" injected
    - Verify correct classification, precedence, and `None` for neither
    - **Validates: Requirements 4.2, 4.3, 4.4**

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement routing module
  - [x] 5.1 Implement `routing.py` — `RoutingPaths` dataclass and `compute_routing_paths`
    - Define `RoutingPaths` frozen dataclass with all path fields and IDs
    - Implement `compute_routing_paths` handling season (N>0), quest (season=0), bounty (season=-1)
    - Compute scenarios dir, chronicles dir, layouts dir, blueprints dir, blueprint/layout IDs, system prefix
    - _Requirements: 4.5, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 5.2 Write unit tests for `routing.py`
    - Test PFS season 7 scenario, SFS season 1 scenario, quest (season=0), bounty (season=-1)
    - Verify all path components and ID patterns
    - _Requirements: 4.5, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 5.3 Write property test for directory routing (Property 5)
    - **Property 5: Directory routing uses correct system prefixes and season subdirectories**
    - Generate random `GameSystem` + random `ScenarioInfo` (positive season, 0, -1)
    - Verify scenarios dir uses display name (`PFS`/`SFS`), chronicles dir uses prefix (`pfs2`/`sfs2`), IDs follow correct pattern
    - **Validates: Requirements 4.5, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6**

- [x] 6. Implement pipeline module
  - [x] 6.1 Implement `pipeline.py` — `PipelineResult` dataclass and `process_single_pdf`
    - Define `PipelineResult` dataclass
    - Implement 5-step pipeline: scenario_renamer → chronicle_extractor → blueprint2layout → layout_generator → layout_visualizer
    - Create and clean up staging directories with `try/finally`
    - Copy (not move) PDF into staging dirs
    - Invoke each tool via `main(argv)` with correct argument lists
    - Handle non-zero exit codes, exceptions, missing output files
    - Print step progress labels and success/error messages
    - Blueprint step: use season-level base blueprint ID pattern, print resolution info, skip gracefully if no blueprint found
    - _Requirements: 6.1–6.6, 7.1–7.5, 8.1–8.6, 9.1–9.6, 10.1–10.7, 11.1–11.4, 12.1–12.4, 14.1–14.4, 15.3, 16.1–16.5_

  - [x] 6.2 Write unit tests for `pipeline.py`
    - Mock all five `main()` functions to return 0 and create expected output files
    - Verify correct argument lists passed to each tool
    - Verify staging directory creation and cleanup (even on failure)
    - Verify error propagation when a tool returns non-zero
    - Verify blueprint step skipped gracefully when no blueprint found
    - _Requirements: 6.1–6.6, 7.1–7.5, 8.1–8.6, 9.1–9.6, 10.1–10.7, 11.1–11.4, 14.1–14.4, 16.1–16.5_

- [-] 7. Implement CLI entry point
  - [x] 7.1 Implement `__main__.py` — `parse_args`, `main`, interactive confirmation, and exit code logic
    - `parse_args`: `--downloads-dir` (default `~/Downloads`), `--project-dir` (default cwd), `--recent` (default `1h`), `--non-interactive` flag
    - Interactive confirmation: prompt per PDF with y/yes, n/no, q/quit (case-insensitive)
    - Orchestration: discover → confirm → detect game system → extract scenario info → compute routes → run pipeline
    - Exit code: 0 if at least one PDF processed successfully, 1 if none processed (skipped PDFs don't count as failures), 0 if no PDFs found
    - Print summary at end (processed, skipped, failed counts)
    - _Requirements: 1.1–1.8, 3.1–3.5, 5.1–5.4, 12.1–12.5, 14.5, 15.1–15.4_

  - [~] 7.2 Write unit tests for `__main__.py`
    - Test argument parsing defaults and overrides
    - Test interactive confirmation with mocked input (y, n, q, case variations)
    - Test exit code logic with various success/fail/skip combinations
    - Test end-to-end flow with mocked tools and discovery
    - _Requirements: 1.1–1.8, 3.1–3.5, 14.5_

  - [~] 7.3 Write property test for user response classification (Property 3)
    - **Property 3: User response classification is case-insensitive**
    - Generate random case variations of "y", "yes", "n", "no", "q", "quit"
    - Verify correct action classification regardless of casing
    - **Validates: Requirements 3.2, 3.3, 3.4**

  - [~] 7.4 Write property test for exit code logic (Property 6)
    - **Property 6: Exit code reflects processing outcomes**
    - Generate random (success_count, fail_count, skip_count) tuples
    - Verify exit code is 0 when success_count > 0, 1 when success_count == 0
    - **Validates: Requirements 1.6, 14.5**

- [ ] 8. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Integration tests and documentation
  - [~] 9.1 Write integration tests for the full pipeline
    - Mock all five `main()` functions and `fitz.open()`
    - Test end-to-end flow from discovery through visualization with mocked tools
    - Verify correct argument lists passed to each tool in sequence
    - Verify staging directory lifecycle (created, populated, cleaned up)
    - Verify error handling when tools fail mid-pipeline (fail-forward behavior)
    - Verify exit codes for mixed success/failure batches
    - _Requirements: 6.1–6.6, 7.1–7.5, 8.1–8.6, 9.1–9.6, 10.1–10.7, 11.1–11.4, 14.1–14.5_

  - [~] 9.2 Create `scenario_download_workflow/README.md`
    - Describe purpose and five-step pipeline
    - Document CLI arguments (`--downloads-dir`, `--project-dir`, `--recent`, `--non-interactive`)
    - Include usage example
    - Note dependency on five existing PFS Tools utilities
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

  - [~] 9.3 Update top-level `README.md` utilities table
    - Add Scenario Download Workflow entry with relative link to utility README
    - _Requirements: 18.1_

- [ ] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 6 universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All downstream tools are invoked via `main(argv)` — no subprocess spawning
- Staging directories use `tempfile.mkdtemp()` with `try/finally` cleanup
