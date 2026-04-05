# Implementation Plan: Layout Data Mode

## Overview

Adds `--mode data` to the existing `layout_visualizer` CLI. Implements parameter merging, preset resolution, content extraction, text alignment computation, and text rendering via PyMuPDF. Each task builds incrementally: data model first, then loading/merging functions, then rendering, then CLI wiring. Tests are grouped with their implementation for commit checkpoints.

## Tasks

- [x] 1. Add DataContentEntry model and data-mode loading functions
  - [x] 1.1 Add `DataContentEntry` dataclass to `layout_visualizer/models.py`
    - Add frozen dataclass with fields: param_name, example_value, entry_type, canvas, x, y, x2, y2, font, fontsize, fontweight, align, lines
    - Include type hints and Google-style docstring per design
    - _Requirements: 4.1, 4.2, 4.3, 6.1_

  - [x] 1.2 Implement `merge_parameters` in `layout_visualizer/layout_loader.py`
    - Walk root-to-leaf chain, flatten parameter groups into a single name→definition dict
    - Child definitions override parent definitions for the same parameter name
    - _Requirements: 2.1_

  - [x] 1.3 Implement `merge_presets` in `layout_visualizer/layout_loader.py`
    - Walk root-to-leaf chain, merge preset dicts with child overriding parent for same name
    - _Requirements: 3.3_

  - [x] 1.4 Implement `resolve_entry_presets` in `layout_visualizer/layout_loader.py`
    - Walk the entry's presets array, resolve nested preset references recursively (depth-first left-to-right)
    - Collect properties from presets in order, then overlay inline entry properties as final override
    - _Requirements: 3.1, 3.2_

  - [x] 1.5 Implement `load_data_content` in `layout_visualizer/layout_loader.py`
    - Walk inheritance chain, merge canvases, parameters, presets, and content
    - Extract text/multiline entries recursively (reuse trigger/choice nesting pattern)
    - Resolve presets on each entry, look up example values from merged parameters
    - Convert example values to string via `str()`
    - Skip non-text types (checkbox, strikeout, line, rectangle)
    - Warn and skip entries with missing parameters or missing example fields
    - Skip entries referencing nonexistent canvases
    - Return (entries, merged_canvases, file_paths)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.1, 9.2, 9.3_

  - [x] 1.6 Write unit tests in `tests/layout_visualizer/test_layout_loader_data.py`
    - Test `merge_parameters`: single layout, two-layout chain with override, parameter in different groups
    - Test `merge_presets`: single layout, chain with override
    - Test `resolve_entry_presets`: entry with no presets, entry with one preset, nested presets, inline override
    - Test `load_data_content`: text entry extraction, multiline entry extraction, skip checkbox/strikeout/line/rectangle, trigger nesting, choice nesting
    - Test example value loading: string example, integer example, float example, missing parameter (warning), missing example field (warning)
    - Test edge cases: empty content array, empty parameters, entry referencing nonexistent canvas
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.1, 9.2, 9.3_

  - [x] 1.7 Write property tests in `tests/layout_visualizer/test_layout_loader_data_pbt.py`
    - **Property 1: Inheritance merge with child override**
    - **Validates: Requirements 2.1, 2.2, 3.3**

  - [x] 1.8 Write property test for preset resolution
    - **Property 2: Preset resolution with inline override**
    - **Validates: Requirements 3.1, 3.2**

  - [x] 1.9 Write property test for example stringification
    - **Property 3: Example value stringification**
    - **Validates: Requirements 2.3, 4.5**

  - [x] 1.10 Write property test for non-text type filtering
    - **Property 6: Non-text type filtering**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

  - [x] 1.11 Write property test for nested content extraction
    - **Property 7: Nested content extraction from trigger and choice**
    - **Validates: Requirements 7.5, 7.6**

- [x] 2. Checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_visualizer/test_layout_loader_data.py tests/layout_visualizer/test_layout_loader_data_pbt.py` and verify all tests pass. Ask the user if questions arise.

- [x] 3. Implement data text renderer
  - [x] 3.1 Create `layout_visualizer/data_renderer.py` with `compute_text_position`
    - Implement alignment computation: horizontal (L=left, C=center, R=right) and vertical (B=bottom, M=middle, T=top)
    - Use `fitz.get_text_length` to measure text width for horizontal alignment
    - Compute baseline position per PyMuPDF's `insert_text` convention
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [x] 3.2 Implement `draw_data_text` in `layout_visualizer/data_renderer.py`
    - Create temporary PDF page matching pixmap dimensions, insert background pixmap
    - For each DataContentEntry: resolve percentage coords to pixels relative to canvas pixel rect
    - For text entries: compute insertion point via `compute_text_position`, insert text with font/size/weight
    - For multiline entries: divide bounding box height by lines count, render example value in first line slot
    - Skip entries referencing nonexistent canvases
    - Return composited RGB pixmap
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 6.1, 6.2, 6.3, 9.3_

  - [x] 3.3 Write unit tests in `tests/layout_visualizer/test_data_renderer.py`
    - Test `compute_text_position` for all 9 alignment combinations (L/C/R × B/M/T) with known values
    - Test multiline slot height computation with known height and line count
    - Test `draw_data_text` returns a pixmap of same dimensions as input
    - Test `draw_data_text` with text and multiline entries (no exceptions)
    - Test `draw_data_text` with bold fontweight
    - Test `draw_data_text` skips entries referencing nonexistent canvas
    - Test `draw_data_text` with empty entries list returns background-only pixmap
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 6.1, 6.2, 6.3, 9.3_

  - [x] 3.4 Write property test for alignment computation
    - **Property 4: Alignment position computation**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**

  - [x] 3.5 Write property test for multiline slot division
    - **Property 5: Multiline line slot division**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 4. Checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_visualizer/test_data_renderer.py tests/layout_visualizer/test_data_renderer_pbt.py` and verify all tests pass. Ask the user if questions arise.

- [x] 5. Wire data mode into CLI and pipeline
  - [x] 5.1 Add `"data"` to `--mode` choices in `layout_visualizer/__main__.py`
    - Update `parse_args` to accept `choices=["canvases", "fields", "data"]`
    - Update help text to describe the data mode
    - _Requirements: 1.1_

  - [x] 5.2 Add data mode branch to `run_visualizer` in `layout_visualizer/__main__.py`
    - Import `load_data_content` from `layout_loader` and `draw_data_text` from `data_renderer`
    - Add `elif mode == "data"` branch: call `load_data_content`, `resolve_canvas_pixels`, `draw_data_text`
    - Write composited pixmap directly (no overlay colors needed)
    - _Requirements: 1.2, 1.3, 8.1_

  - [x] 5.3 Write CLI integration tests for data mode
    - Add tests to `tests/layout_visualizer/test_cli.py` or a new `tests/layout_visualizer/test_cli_data.py`
    - Test `--mode data` is accepted by argument parser
    - Test `--mode data --watch` is accepted by argument parser
    - Test successful data mode run produces PNG file (with real layout + PDF)
    - _Requirements: 1.1, 1.2, 1.3, 8.1_

- [x] 6. Final checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_visualizer/` and verify all tests pass. Ask the user if questions arise.

## Notes

- All unit test sub-tasks (1.6, 3.3, 5.3) are mandatory
- Tasks marked with `*` are optional property-based tests that can be skipped for faster MVP
- Property tests use Hypothesis with minimum 100 iterations per property
- Each property test is tagged with a comment referencing the design property number
- Python with type hints and Google-style docstrings throughout
- PyMuPDF (`fitz`) is the only rendering dependency (already in requirements.txt)
- Hypothesis is used for property-based tests (already in requirements.txt)
- Watch mode works automatically — `run_visualizer` already receives the `mode` parameter from `watch_and_regenerate`
- Commit checkpoints: task 2 (loading + tests), task 4 (renderer + tests), task 6 (CLI wiring + tests)
