# Implementation Plan: Layout Generator

## Overview

Migrate and refactor the existing `src/` scripts (`layout_generator.py`, `item_segmenter.py`, `checkbox_extractor.py`, `chronicle2layout.py`) into a proper `layout_generator/` package following the same patterns as `chronicle_extractor/`, `layout_visualizer/`, `blueprint2layout/`, and `scenario_renamer/`. The `metadata.py` module is entirely new (TOML parsing with regex rules). The `text_extractor.py` module is extracted from `src/chronicle2layout.py`'s `extract_text_lines` function. Canvas resolution is reimplemented using `shared.layout_index` instead of the old `shared_utils`. After migration, the original `src/` files are deleted.

## Tasks

- [x] 1. Set up package structure and module stubs
  - [x] 1.1 Create package and module stubs
    - Create `layout_generator/__init__.py` (empty package marker)
    - Create `layout_generator/__main__.py`, `generator.py`, `item_segmenter.py`, `checkbox_extractor.py`, `text_extractor.py`, `metadata.py` as modules with module-level docstrings and placeholder function signatures from the design
    - Create `tests/layout_generator/` directory with empty `__init__.py` and `conftest.py`
    - _Requirements: 1.1_

- [x] 2. Implement metadata TOML parsing and regex rule matching
  - [x] 2.1 Implement `MetadataRule`, `MetadataConfig`, `MatchedMetadata` dataclasses and `load_metadata` in `metadata.py`
    - Define frozen dataclasses per the design
    - `load_metadata` parses a TOML file using `tomllib`, validates required fields (`pattern`, `id`, `parent`), reads optional `layouts_dir` and optional rule fields (`description`, `default_chronicle_location`)
    - Raise `FileNotFoundError` if file missing, `ValueError` if malformed or missing required fields
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.9_

  - [x] 2.2 Implement `apply_substitutions` and `match_rule` in `metadata.py`
    - `apply_substitutions` replaces `$0`, `$1`, `$2`, etc. in a template with regex match groups; leaves non-existent group references as literal strings and prints a warning to stderr
    - `match_rule` tests rules in order, returns `MatchedMetadata` for the first match with substitutions applied, or `None` if no rule matches
    - _Requirements: 2.7, 15.1, 15.2, 15.3, 15.4_

  - [x] 2.3 Write unit tests for metadata module
    - Create `tests/layout_generator/test_metadata.py`
    - Test `load_metadata`: valid TOML with all fields, missing file, malformed TOML, missing required fields, optional fields omitted
    - Test `apply_substitutions`: single group, multiple groups, `$0` full match, non-existent group left as literal
    - Test `match_rule`: first-match semantics, no match returns `None`, substitution in all template fields
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.9, 15.1, 15.2, 15.3, 15.4_

  - [x] 2.4 Write property test for first-match rule semantics
    - **Property 1: First-match rule semantics**
    - **Validates: Requirements 2.7**
    - Create `tests/layout_generator/test_metadata_pbt.py`
    - Generate ordered lists of `MetadataRule` instances with valid regex patterns; verify `match_rule` returns the first matching rule's metadata

  - [x] 2.5 Write property test for regex substitution
    - **Property 11: Regex substitution replaces all valid group references**
    - **Validates: Requirements 15.1, 15.2**
    - In `tests/layout_generator/test_metadata_pbt.py`
    - Generate regex patterns with N capture groups and templates with `$0` through `$N` references; verify all valid references replaced, invalid references left as literals

- [x] 3. Implement text extraction from PDF
  - [x] 3.1 Implement `extract_text_lines` in `text_extractor.py`
    - Migrate and refactor from `src/chronicle2layout.py`'s `extract_text_lines`, `_group_words_by_line`, `_find_matching_line_y`, and `_convert_lines_to_results`
    - Simplified signature: accepts `pdf_path` and `region_pct` only (no layout_dir/parent_id resolution — that moves to `__main__.py`)
    - Opens last page of PDF, filters words to region, groups by y-coordinate within `Y_COORDINATE_GROUPING_TOLERANCE` (2.0 points), converts to region-relative percentages, sorts top-to-bottom
    - Skips bare "items" header lines
    - Returns empty list for zero-page PDFs
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 3.2 Write unit tests for text extraction
    - Create `tests/layout_generator/test_text_extractor.py`
    - Test with a real chronicle PDF from `Scenarios/` directory using known region coordinates
    - Test empty PDF (zero pages) returns empty list
    - Test filtering: words outside region excluded
    - Test y-coordinate grouping: words within tolerance grouped, words beyond tolerance separated
    - Test percentage conversion: bounding boxes are region-relative
    - Test sort order: lines sorted top-to-bottom
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 3.3 Write property test for region-relative sorted lines
    - **Property 3: Text extraction produces region-relative sorted lines**
    - **Validates: Requirements 4.3, 4.5, 4.6**
    - Create `tests/layout_generator/test_text_extractor_pbt.py`

  - [x] 3.4 Write property test for y-coordinate line grouping
    - **Property 4: Y-coordinate line grouping within tolerance**
    - **Validates: Requirements 4.4**
    - In `tests/layout_generator/test_text_extractor_pbt.py`

- [x] 4. Implement item seg
.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 4.2 Write unit tests for item segmentation
    - Create `tests/layout_generator/test_item_segmenter.py`
    - Test `clean_text`: trailing U removal, hair-space removal, whitespace stripping
    - Test `segment_items`: single-line item, multi-line item spanning parentheses, two items on consecutive lines, empty input, bare "items" header skipped
    - Test parenthesis heuristic: two groups force split, unbalanced continues to next line
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 4.3 Write property test for token preservation
    - **Property 5: Item segmentation preserves all non-header tokens**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
    - Create `tests/layout_generator/test_item_segmenter_pbt.py`

  - [x] 4.4 Write property test for text cleaning
    - **Property 6: Text cleaning removes artifacts and hair spaces**
    - **Validates: Requirements 5.5**
    - In `tests/layout_generator/test_item_segmenter_pbt.py`

- [x] 5. Checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_generator/` and verify all tests pass. Ask the user if questions arise.

- [x] 6. Implement checkbox detection and label extraction
  - [x] 6.1 Implement `detect_checkboxes` and `extract_checkbox_labels` in `checkbox_extractor.py`
    - Migrate and refactor from `src/checkbox_extractor.py`
    - `detect_checkboxes` scans last page for checkbox Unicode characters, filters to region, returns region-relative percentage bounding boxes
    - `extract_checkbox_labels` scans words after each checkbox until delimiter (another checkbox, "or", trailing punctuation), strips trailing punctuation (preserving ellipsis and decimals)
    - Rename `image_checkboxes` to `detect_checkboxes` per design
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 6.2 Write unit tests for checkbox extraction
    - Create `tests/layout_generator/test_checkbox_extractor.py`
    - Test `detect_checkboxes` with a real chronicle PDF using known checkbox region
    - Test empty PDF returns empty list
    - Test region filtering: checkboxes outside region excluded
    - Test `extract_checkbox_labels`: label collection, delimiter handling ("or", next checkbox, punctuation), trailing punctuation stripping, ellipsis preservation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 6.3 Write property test for checkbox region-relative positions
    - **Property 7: Checkbox detection produces region-relative positions**
    - **Validates: Requirements 6.2, 6.3**
    - Create `tests/layout_generator/test_checkbox_extractor_pbt.py`

  - [x] 6.4 Write property test for trailing punctuation stripping
    - **Property 8: Trailing punctuation stripping preserves ellipsis and decimals**
    - **Validates: Requirements 7.5**
    - In `tests/layout_generator/test_checkbox_extractor_pbt.py`

- [x] 7. Implement core layout assembly
  - [x] 7.1 Implement `make_safe_label` and `generate_layout_json` in `generator.py`
    - Migrate and refactor from `src/layout_generator.py`
    - `make_safe_label` replaces spaces with underscores, strips commas/periods/parentheses/quotes, truncates to 50 chars
    - `generate_layout_json` orchestrates the full pipeline: text extraction → item segmentation → checkbox detection → label extraction → layout assembly
    - Simplified signature per design: accepts `pdf_path`, `item_region_pct`, `checkbox_region_pct`, canvas names, and metadata fields (no layout_dir/parent_id — resolution moves to `__main__.py`)
    - Raise `FileNotFoundError` if pdf_path does not exist
    - Assemble layout dict with metadata, parameters, presets, and content per LAYOUT_FORMAT.md
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11, 8.12, 11.1, 11.2, 11.3, 11.4, 14.1, 14.2, 14.3_

  - [x] 7.2 Write unit tests for generator
    - Create `tests/layout_generator/test_generator.py`
    - Test `make_safe_label`: space replacement, punctuation stripping, truncation to 50 chars, deterministic output
    - Test `generate_layout_json` with a real chronicle PDF: verify output has expected structure (id, parent, parameters, presets, content)
    - Test with no items and no checkboxes: metadata-only output
    - Test `FileNotFoundError` for missing PDF
    - Test item section assembly: parameter choices, base preset, line presets, content entry
    - Test checkbox section assembly: parameter choices, base preset, checkbox presets, content entry
    - Test section ordering: items skeleton → checkboxes → item line presets
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11, 8.12, 11.1, 11.2, 11.3, 11.4, 14.1, 14.2, 14.3_

  - [x] 7.3 Write property test for safe label sanitization
    - **Property 9: Safe label sanitization**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4**
    - Create `tests/layout_generator/test_generator_pbt.py`

  - [x] 7.4 Write property test for layout JSON round-trip
    - **Property 10: Layout JSON round-trip**
    - **Validates: Requirements 12.1, 12.2**
    - In `tests/layout_generator/test_generator_pbt.py`

  - [x] 7.5 Write property test for item layout assembly
    - **Property 12: Item layout assembly produces correct structure**
    - **Validates: Requirements 8.2, 8.3, 8.4, 8.5**
    - In `tests/layout_generator/test_generator_pbt.py`

  - [x] 7.6 Write property test for checkbox layout assembly
    - **Property 13: Checkbox layout assembly produces correct structure**
    - **Validates: Requirements 8.6, 8.7, 8.8, 8.9**
    - In `tests/layout_generator/test_generator_pbt.py`

- [x] 8. Checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_generator/` and verify all tests pass. Ask the user if questions arise.

- [x] 9. Implement canvas resolution and CLI entry point
  - [x] 9.1 Implement `resolve_canvas_region` in `__main__.py`
    - Build layout index from layouts directory using `shared.layout_index.build_json_index`
    - Walk parent inheritance chain using `shared.layout_index.collect_inheritance_chain`
    - Merge canvas definitions from root to leaf
    - Convert target canvas's relative percentages to absolute page percentages by walking the canvas parent chain
    - Return `[x0, y0, x1, y1]` as absolute page percentages, or `None` if canvas not found
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 9.2 Implement `parse_args` in `__main__.py`
    - Required positional `pdf_path` (file or directory)
    - Optional `--metadata-file` (default `chronicle_properties.toml`)
    - Optional `--layouts-dir` (fallback to TOML `layouts_dir`)
    - Optional `--output-dir` (default to resolved `--layouts-dir`)
    - Optional `--item-canvas` (default `items`), `--checkbox-canvas` (default `summary`)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x] 9.3 Implement `main` in `__main__.py`
    - Parse args, load metadata, build layout index, validate layouts directory
    - For directory mode: recursively find all `.pdf` files, match each against metadata rules
    - For single-file mode: match the file against metadata rules
    - For each matched PDF: resolve canvas regions, call `generate_layout_json`, write output JSON
    - Create output directories as needed, print output paths to stdout
    - Log errors/warnings to stderr with identifying context (layout id or PDF path)
    - Print summary of generated/skipped counts
    - Exit 0 when at least one layout generated, exit 1 otherwise
    - _Requirements: 1.5, 1.9, 2.8, 3.4, 3.5, 3.6, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 13.1, 13.2, 13.3, 13.4_

  - [x] 9.4 Write property test for canvas coordinate resolution
    - **Property 2: Canvas coordinate resolution composes correctly**
    - **Validates: Requirements 3.2, 3.3**
    - Create `tests/layout_generator/test_cli_pbt.py`

  - [x] 9.5 Write CLI integration tests
    - Create `tests/layout_generator/test_cli.py`
    - Test missing arguments prints usage and exits non-zero
    - Test missing metadata file exits non-zero with error to stderr
    - Test missing layouts directory exits non-zero with error to stderr
    - Test `--layouts-dir` not provided and not in TOML exits non-zero
    - Test single-file mode with real chronicle PDF and TOML fixture
    - Test directory mode with temp directory containing PDFs and TOML fixture
    - Test no matching rules prints warning and exits with code 1
    - Test output directory creation
    - Test summary output (generated/skipped counts)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 13.1, 13.2, 13.3, 13.4_

- [x] 10. Checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_generator/` and verify all tests pass. Ask the user if questions arise.

- [x] 11. Delete migrated source files
  - [x] 11.1 Remove old `src/` files
    - Delete `src/layout_generator.py`, `src/item_segmenter.py`, `src/checkbox_extractor.py`, `src/chronicle2layout.py`
    - Verify no remaining imports reference the old `src/` modules
    - _Requirements: 1.1_

- [x] 12. Final checkpoint — Ensure all tests pass
  - Run `pytest` (full test suite) and verify all tests pass. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–13)
- Unit tests validate specific examples and edge cases
- All code follows Google-style docstrings, type hints required, per project Python standards
- PyMuPDF (`fitz`) and `tomllib` (stdlib 3.11+) are the key dependencies
- Hypothesis is used for property-based tests (already in requirements.txt)
- The `metadata.py` module is entirely new; all other modules are migrated from `src/` and refactored to match the rewrite's coding standards
- Canvas resolution uses `shared.layout_index` (build_json_index, collect_inheritance_chain) instead of the old `shared_utils`
- The `text_extractor.py` module has a simplified signature (no layout_dir/parent_id) — canvas resolution is handled in `__main__.py`
