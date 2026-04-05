# Implementation Plan: Layout Visualizer

## Overview

Incremental implementation of the `layout_visualizer` Python CLI tool. Each task builds on the previous, starting with data models, then layering in layout loading/inheritance, coordinate resolution, PDF rendering, overlay drawing, CLI wiring, and watch mode. The tool takes a layout JSON + chronicle PDF and produces a PNG visualization of canvas regions.

## Tasks

- [x] 1. Set up project structure and data models
  - [x] 1.1 Create package and module stubs
    - Create `layout_visualizer/__init__.py`, `__main__.py`, `layout_loader.py`, `pdf_renderer.py`, `coordinate_resolver.py`, `overlay_renderer.py`, `models.py`, `colors.py` as modules with module-level docstrings
    - Create `tests/layout_visualizer/` directory with empty `conftest.py`
    - _Requirements: 1.5_

  - [x] 1.2 Implement data models in `models.py`
    - Define frozen dataclasses: `CanvasRegion` (name, x, y, x2, y2, parent) and `PixelRect` (name, x, y, x2, y2, parent)
    - Include type hints and Google-style docstrings
    - _Requirements: 4.1_

  - [x] 1.3 Implement color palette in `colors.py`
    - Define `PALETTE` as a list of 12 RGB tuples
    - _Requirements: 5.2_

- [x] 2. Implement layout loading and inheritance resolution
  - [x] 2.1 Implement `build_layout_index` in `layout_loader.py`
    - Scan directory recursively for `.json` files
    - Parse `id` field from each and build id-to-path map
    - Skip files without an `id` field or with invalid JSON
    - _Requirements: 2.2_

  - [x] 2.2 Implement `load_layout_with_inheritance` in `layout_loader.py`
    - Parse layout JSON and extract `canvas` object into `CanvasRegion` instances
    - Walk parent chain via `parent` field and layout index
    - Merge canvases from root to leaf (child overrides parent for same name)
    - Return merged canvases dict and list of all layout file paths in chain
    - Raise `FileNotFoundError` for missing layout file
    - Raise `ValueError` for invalid JSON or missing parent id
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.3 Write unit tests for layout loading
    - Create `tests/layout_visualizer/test_layout_loader.py`
    - Test `build_layout_index` with temp directory of layout files
    - Test `load_layout_with_inheritance`: single layout (no parent), parent-child chain, missing parent id error, invalid JSON error
    - Test canvas merging: child overrides parent for same-named canvas
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.4 Write property tests for layout loading
    - Create `tests/layout_visualizer/test_layout_loader_pbt.py`
    - **Property 2**: Generate random canvas dicts, verify extraction round-trip
    - **Property 3**: Generate random layout chains with overlapping canvas names, verify child override
    - Tag: `Feature: layout-visualizer, Property 2: Canvas extraction round-trip`
    - Tag: `Feature: layout-visualizer, Property 3: Inheritance chain merging with child override`
    - Minimum 100 iterations per property
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Implement coordinate resolution
  - [x] 3.1 Implement `topological_sort_canvases` in `coordinate_resolver.py`
    - Sort canvas names so parents come before children
    - Raise `ValueError` if a canvas references a nonexistent parent
    - _Requirements: 4.4, 4.5_

  - [x] 3.2 Implement `resolve_canvas_pixels` in `coordinate_resolver.py`
    - Process canvases in topological order
    - For canvases with parent: compute pixels relative to parent's resolved pixel bounds
    - For canvases without parent: compute pixels relative to full page dimensions
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.3 Implement `assign_colors` in `coordinate_resolver.py` (or `colors.py`)
    - Assign `PALETTE[i % len(PALETTE)]` to each canvas name by index
    - _Requirements: 5.1, 5.3_

  - [x] 3.4 Write unit tests for coordinate resolution
    - Create `tests/layout_visualizer/test_coordinate_resolver.py`
    - Test topological sort with known parent-child relationships
    - Test pixel conversion with known percentages and page dimensions
    - Test orphaned canvas (missing parent) raises error
    - Test color assignment and cycling
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.3_

  - [x] 3.5 Write property tests for coordinate resolution
    - Create `tests/layout_visualizer/test_coordinate_resolver_pbt.py`
    - **Property 4**: Generate random CanvasRegion + page dimensions, verify pixel formula
    - **Property 5**: Generate random canvas forests, verify parent-before-child ordering
    - **Property 6**: Generate random canvas name lists, verify palette cycling
    - Tag: `Feature: layout-visualizer, Property 4: Percentage-to-pixel coordinate conversion`
    - Tag: `Feature: layout-visualizer, Property 5: Topological ordering preserves parent-before-child`
    - Tag: `Feature: layout-visualizer, Property 6: Color assignment with palette cycling`
    - Minimum 100 iterations per property
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.3_

- [x] 4. Checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_visualizer/` and verify all tests pass. Ask the user if questions arise.

- [x] 5. Implement PDF rendering
  - [x] 5.1 Implement `render_pdf_page` in `pdf_renderer.py`
    - Open PDF with PyMuPDF, render first page at 150 DPI
    - Return RGB `fitz.Pixmap`
    - Raise `FileNotFoundError` for missing PDF
    - Raise `ValueError` for invalid PDF
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 5.2 Write unit tests for PDF rendering
    - Create `tests/layout_visualizer/test_pdf_renderer.py`
    - Test with a real chronicle PDF from `PFS/` directory
    - Verify returned pixmap has expected dimensions for 150 DPI
    - Test `FileNotFoundError` for missing PDF
    - Test `ValueError` for non-PDF file
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 6. Implement overlay rendering
  - [x] 6.1 Implement `draw_overlays` in `overlay_renderer.py`
    - Create a temporary PDF page matching pixmap dimensions
    - For each canvas region: draw semi-transparent filled rectangle (~40% opacity), solid border (2px), and text label with canvas name
    - Position label inside the rectangle with contrasting background
    - Composite the overlay onto the background pixmap
    - Return the composited pixmap
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2, 7.3_

  - [x] 6.2 Write unit tests for overlay rendering
    - Create `tests/layout_visualizer/test_overlay_renderer.py`
    - Test that `draw_overlays` returns a pixmap of the same dimensions as input
    - Test with multiple canvas regions to verify no exceptions
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2, 7.3_

- [x] 7. Implement CLI entry point and pipeline
  - [x] 7.1 Implement `parse_args` in `__main__.py`
    - Two positional args: layout_file, pdf_file
    - Optional positional: output (PNG path)
    - Optional flag: `--watch`
    - Default output: same directory as layout file, `.png` extension
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

  - [x] 7.2 Implement `run_visualizer` in `__main__.py`
    - Wire the full pipeline: load_layout_with_inheritance → render_pdf_page → resolve_canvas_pixels → assign_colors → draw_overlays → write PNG
    - Infer Layouts directory from layout file path (walk up to find `Layouts/` root)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 8.1, 8.2_

  - [x] 7.3 Implement `main` in `__main__.py`
    - Parse args, validate file existence, run pipeline
    - Print errors to stderr, return exit code 0 or 1
    - If `--watch`, call `watch_and_regenerate` instead
    - _Requirements: 1.5, 8.2, 8.3, 9.1, 9.2, 9.3, 9.4_

  - [x] 7.4 Write CLI integration tests
    - Create `tests/layout_visualizer/test_cli.py`
    - Test missing arguments prints usage and exits non-zero
    - Test missing layout file exits non-zero with error to stderr
    - Test missing PDF file exits non-zero with error to stderr
    - Test default output path derivation
    - Test successful run produces PNG file (with real layout + PDF)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 9.1, 9.2, 9.3, 9.4_

  - [x] 7.5 Write property test for default output path
    - Add to `tests/layout_visualizer/test_cli.py` or separate PBT file
    - **Property 1**: Generate random Path objects, verify default output has `.png` extension and same directory
    - Tag: `Feature: layout-visualizer, Property 1: Default output path derivation`
    - Minimum 100 iterations
    - _Requirements: 1.4_

- [x] 8. Checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_visualizer/` and verify all tests pass. Ask the user if questions arise.

- [x] 9. Implement watch mode
  - [x] 9.1 Implement `watch_and_regenerate` in `__main__.py`
    - Run pipeline once, then poll file modification times every 1 second
    - Monitor the target layout file and all parent layout files
    - On change: print message to stdout, re-run pipeline
    - On regeneration error: print to stderr, continue watching
    - On SIGINT: exit cleanly with status code 0
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [x] 9.2 Manual testing of watch mode
    - Verify watch mode detects layout file changes and regenerates PNG
    - Verify Ctrl+C exits cleanly
    - Verify invalid JSON during watch prints error and continues
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 10. Final checkpoint — Ensure all tests pass
  - Run `pytest tests/layout_visualizer/` and verify all tests pass. Ask the user if questions arise.

## Notes

- All unit test tasks are mandatory
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Python with type hints and Google-style docstrings throughout
- PyMuPDF (`fitz`) is the only external dependency for rendering and drawing (already in requirements.txt)
- Hypothesis is used for property-based tests (already in requirements.txt)
- Watch mode (task 9) is tested manually since it involves long-running process behavior
- All dataclasses are frozen for immutability
- The Layouts directory is inferred from the layout file path by walking up to find the `Layouts/` directory
