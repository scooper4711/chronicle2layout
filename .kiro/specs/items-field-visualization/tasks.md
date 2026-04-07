# Implementation Plan: Items Field Visualization

## Overview

Extend `--mode fields` to visualize strikeout and checkbox entries by wiring preset resolution into the field extraction pipeline in `layout_loader.py`. Reuses existing `merge_presets` and `resolve_entry_presets` functions. No new modules required.

## Tasks

- [ ] 1. Modify `load_content_fields` to merge presets from the inheritance chain
  - [x] 1.1 Call `merge_presets(chain)` in `load_content_fields` and pass the merged presets dict to `_extract_fields_from_content`
    - Add `merge_presets(chain)` call after the existing chain iteration loop
    - Pass the resulting `presets` dict as a new argument to `_extract_fields_from_content`
    - _Requirements: 4.1, 4.2_

  - [x] 1.2 Write unit tests for preset merging in `load_content_fields`
    - Test that presets from parent layouts are available during field extraction
    - Test that child preset definitions override parent definitions for the same name
    - Add tests to `tests/layout_visualizer/test_layout_loader.py`
    - _Requirements: 4.1, 4.2_

- [ ] 2. Modify `_extract_fields_from_content` to accept presets and handle preset-based entry types
  - [x] 2.1 Update `_extract_fields_from_content` signature to accept `presets` and `label` parameters
    - Add `presets: dict[str, dict]` parameter
    - Add `label: str | None = None` parameter for choice-key propagation
    - Remove `strikeout` and `checkbox` from `_SKIP_TYPES` (or stop consulting it for these types)
    - _Requirements: 1.1, 2.1, 6.1_

  - [x] 2.2 Add choice content traversal with per-key labeling
    - When `type` is `"choice"`, iterate all keys in `entry["content"]` map
    - Recurse into each key's content array with `label=key`
    - Replace the existing `_get_nested_content` call for choice entries with inline iteration
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 2.3 Add trigger content recursion with label passthrough
    - When `type` is `"trigger"`, recurse into `entry["content"]` passing current `label` and `presets`
    - _Requirements: 1.1_

  - [x] 2.4 Create `_extract_preset_based_field` helper function
    - Call `resolve_entry_presets(entry, presets)` to merge preset properties
    - Check that resolved dict has `canvas`, `x`, `y`, `x2`, `y2`
    - Use `label` if provided, otherwise fall back to `f"field_{counter[0]}"`
    - Return `CanvasRegion` or `None` if coordinates are incomplete
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 5.1, 5.2_

  - [x] 2.5 Wire `_extract_preset_based_field` into the extraction loop for strikeout and checkbox types
    - When `type` is `"strikeout"` or `"checkbox"`, call `_extract_preset_based_field`
    - Append the result to `fields` if not `None`
    - For other types, continue using existing `_try_parse_field`
    - _Requirements: 2.1, 2.2, 2.3, 6.1, 6.2, 6.3_

  - [x] 2.6 Write unit tests for strikeout entry extraction
    - Test that a strikeout entry with preset-resolved coordinates produces a CanvasRegion
    - Test that the choice key text is used as the label
    - Test that entries with incomplete coordinates after resolution are skipped
    - Test that entries referencing missing presets are skipped
    - Add tests to `tests/layout_visualizer/test_layout_loader.py`
    - _Requirements: 2.1, 2.2, 2.3, 5.1, 5.2_

  - [x] 2.7 Write unit tests for checkbox entry extraction
    - Test that a checkbox entry with preset-resolved coordinates produces a CanvasRegion
    - Test that the choice key text is used as the label
    - Test checkbox entries nested inside choice content maps
    - Add tests to `tests/layout_visualizer/test_layout_loader.py`
    - _Requirements: 6.1, 6.2, 6.3, 6.6_

  - [x] 2.8 Write unit tests for choice content traversal
    - Test that all keys in a choice content map are iterated
    - Test that entries from all choice branches are included in the output
    - Test that the choice key is propagated as the label to nested entries
    - Add tests to `tests/layout_visualizer/test_layout_loader.py`
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Handle graceful skipping of unresolvable entries
  - [x] 4.1 Ensure entries with missing preset names are silently skipped
    - `resolve_entry_presets` already returns an empty dict for unknown presets; verify `_extract_preset_based_field` handles this by returning `None`
    - _Requirements: 5.1_

  - [x] 4.2 Ensure entries with incomplete coordinates after resolution are skipped
    - The coordinate check in `_extract_preset_based_field` already handles this; verify no exceptions are raised
    - _Requirements: 5.2_

  - [x] 4.3 Write unit tests for graceful error handling
    - Test entry with nonexistent preset name is skipped without error
    - Test entry missing `y`/`y2` after resolution is skipped
    - Test entry referencing nonexistent canvas name still produces a CanvasRegion (canvas validation happens downstream in `resolve_field_pixels`)
    - Add tests to `tests/layout_visualizer/test_layout_loader.py`
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 5. Verify styling consistency with existing field visualization
  - [x] 5.1 Confirm that extracted CanvasRegions flow through the existing `resolve_field_pixels` → `draw_overlays` pipeline unchanged
    - No code changes needed in `coordinate_resolver.py`, `overlay_renderer.py`, or `__main__.py`
    - Verify by running `--mode fields` on a layout with strikeout/checkbox entries
    - _Requirements: 2.4, 2.5, 6.4, 6.5_

- [x] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- No new modules or data models are needed; all changes are in `layout_loader.py`
- Existing `merge_presets` and `resolve_entry_presets` are reused from the data-mode pipeline (DRY)
- The `_get_nested_content` helper is replaced by inline logic in `_extract_fields_from_content` to support per-key labeling
