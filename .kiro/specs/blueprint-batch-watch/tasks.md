# Implementation Plan: Blueprint Batch & Watch

## Overview

Refactor `blueprint2layout/__main__.py` to replace the positional-argument CLI with a named-argument, batch-oriented interface mirroring `layout_visualizer`'s pattern. All new functions live in `blueprint2layout/__main__.py`; existing modules (`__init__.py`, `blueprint.py`, `output.py`, `shared/layout_index.py`) remain unchanged. Tests go in `tests/blueprint2layout/test_batch_watch.py`.

## Tasks

- [x] 1. Implement `match_blueprint_ids()` and `resolve_default_chronicle_location()`
  - [x] 1.1 Implement `match_blueprint_ids(pattern, blueprint_index)` in `blueprint2layout/__main__.py`
    - Use `fnmatch.fnmatch` for wildcard patterns (`*`, `?`, `[`), literal lookup otherwise
    - Return sorted list of matching ids; raise `ValueError` when no matches
    - Mirror `layout_visualizer.__main__.match_layout_ids` closely
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 1.2 Write property test for `match_blueprint_ids`
    - **Property 1: Wildcard matching returns the correct sorted set**
    - Generate random id-to-path indexes and patterns (with/without wildcards), verify result matches `fnmatch` filtering and is sorted, verify `ValueError` on no matches
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

  - [x] 1.3 Implement `resolve_default_chronicle_location(blueprint_path, blueprint_index)` in `blueprint2layout/__main__.py`
    - Use `shared.layout_index.collect_inheritance_chain` to walk the parent chain
    - Return `defaultChronicleLocation` from the leaf-most blueprint that defines it, walking toward root
    - Return `None` if no blueprint in the chain defines it
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 1.4 Implement `resolve_chronicle_pdf(blueprint_id, blueprint_index)` in `blueprint2layout/__main__.py`
    - Call `resolve_default_chronicle_location` to get the location string
    - Raise `ValueError` if no location found in the chain
    - Raise `FileNotFoundError` if the resolved PDF path doesn't exist on disk
    - Return the resolved `Path`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 1.5 Write property test for `resolve_default_chronicle_location`
    - **Property 2: Chronicle resolution returns the leaf-most defaultChronicleLocation**
    - Generate random inheritance chains with optional `defaultChronicleLocation`, write to temp files, verify resolution returns leaf-most value or `None`
    - **Validates: Requirements 3.1, 3.2, 3.3**

  - [x] 1.6 Write unit tests for `match_blueprint_ids` and `resolve_chronicle_pdf`
    - Test empty index, no-match pattern, literal id not found, missing PDF on disk, no location in chain
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

- [x] 2. Implement `derive_output_path()` and `run_single_layout()`
  - [x] 2.1 Implement `derive_output_path(blueprint_id, blueprint_path, blueprints_dir, output_dir)` in `blueprint2layout/__main__.py`
    - Strip the blueprint id prefix up to and including the first `.`, append `.json` for the filename
    - Compute the relative subdirectory of the blueprint file's parent from `blueprints_dir`
    - Return `output_dir / relative_subdir / filename`
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 2.2 Write property test for `derive_output_path`
    - **Property 3: Output path derivation preserves directory structure and strips id prefix**
    - Generate random blueprint ids (with dots), relative subdirectory paths, output dirs; verify derived path structure
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x] 2.3 Implement `run_single_layout(blueprints_dir, blueprint_id, output_path)` in `blueprint2layout/__main__.py`
    - Build blueprint index, resolve chronicle PDF, call `generate_layout`, create output directory, call `write_layout`, print status
    - _Requirements: 5.1, 5.2_

  - [x] 2.4 Write unit tests for `derive_output_path`
    - Test blueprint in root dir (no subdirectory), deeply nested subdirectory, id with single dot, id with multiple dots
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 3. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement watch mode helpers and `watch_and_regenerate()`
  - [x] 4.1 Implement `_collect_watched_paths(blueprints_dir, blueprint_ids)` in `blueprint2layout/__main__.py`
    - Build blueprint index, walk inheritance chains for all target ids using `shared.layout_index.collect_inheritance_chain`
    - Return deduplicated list of all blueprint file paths across all chains
    - _Requirements: 6.3_

  - [x] 4.2 Implement `_record_mtimes(paths)` and `_any_file_changed(paths, previous_mtimes)` in `blueprint2layout/__main__.py`
    - `_record_mtimes`: return `dict[Path, float]` of `os.path.getmtime` for each path
    - `_any_file_changed`: return `True` if any file's mtime differs from recorded value
    - _Requirements: 6.1, 6.2_

  - [x] 4.3 Implement `watch_and_regenerate(blueprints_dir, targets)` in `blueprint2layout/__main__.py`
    - Generate all layouts once, collect watched paths, record mtimes
    - Poll every 1 second; on change: print message, regenerate all targets, re-collect paths, re-record mtimes
    - On error during regeneration: print to stderr, continue watching
    - On `KeyboardInterrupt`: print "Stopped.", return
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [x] 4.4 Write property test for `_collect_watched_paths`
    - **Property 4: Watched paths cover all files in all inheritance chains**
    - Generate random blueprint indexes with inheritance chains, verify collected paths is a superset of all chain files with no duplicates
    - **Validates: Requirements 6.3**

  - [x] 4.5 Write unit tests for watch mode helpers
    - Test `_record_mtimes` with real temp files, `_any_file_changed` detecting modifications
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 5. Implement `parse_args()` and `main()` — wire everything together
  - [x] 5.1 Replace existing `parse_args()` in `blueprint2layout/__main__.py`
    - Accept required `--blueprints-dir` and `--blueprint-id`, optional `--output-dir` (default `.`), optional `--watch` flag
    - Remove old positional arguments (`blueprint`, `pdf`, `output`)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 5.2 Replace existing `main()` in `blueprint2layout/__main__.py`
    - Validate `--blueprints-dir` is a directory
    - Build blueprint index, match ids, resolve chronicle PDFs, derive output paths
    - If `--watch`: call `watch_and_regenerate`, else batch-generate all layouts
    - Catch `ValueError`, `FileNotFoundError`, `OSError`; print to stderr, return 1
    - Return 0 on success
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 5.1, 5.2, 5.3, 7.1, 7.2, 7.3, 7.4_

  - [x] 5.3 Write unit tests for `parse_args` and `main`
    - Test required args, defaults, flag behavior, invalid blueprints-dir, successful batch run (mocked pipeline), watch mode entry (mocked), error messages to stderr
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 5.3, 7.1, 7.4_

- [x] 6. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Update README documentation
  - [x] 7.1 Update `blueprint2layout/README.md` with the new CLI interface
    - Document `--blueprints-dir`, `--blueprint-id`, `--output-dir`, `--watch` arguments
    - Include usage examples for batch generation and watch mode
    - Remove documentation of the old positional-argument interface
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 8. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- All new code lives in `blueprint2layout/__main__.py`; existing modules are unchanged
- All tests go in `tests/blueprint2layout/test_batch_watch.py`
- Property tests use Hypothesis with `@settings(max_examples=100)`
- The implementation mirrors `layout_visualizer/__main__.py` closely for consistency
