# Implementation Plan: Blueprint Fields

## Overview

Extends the `blueprint2layout` tool to support parameters, field styles, fields, and content generation. Implementation proceeds bottom-up: data models first, then parsing/merging, then edge resolution extensions, then the new field resolver, then output assembly, and finally pipeline wiring. Each step builds on the previous and is validated by tests before moving on.

## Tasks

- [x] 1. Extend data models in `models.py`
  - [x] 1.1 Add `FieldEntry` and `ResolvedField` dataclasses to `blueprint2layout/models.py`
    - `FieldEntry`: frozen dataclass with `name`, `canvas`, `type`, `param`, `value`, edge properties (`left`/`right`/`top`/`bottom`), styling properties (`font`, `fontsize`, `fontweight`, `align`, `color`, `linewidth`, `size`, `lines`), `styles` list, and `trigger`
    - `ResolvedField`: frozen dataclass with `name`, `canvas`, `type`, `param`, `value`, resolved coordinates (`x`/`y`/`x2`/`y2`), styling properties, and `trigger`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9_

  - [x] 1.2 Extend the `Blueprint` dataclass with new optional fields
    - Add `parameters: dict | None = None`
    - Add `default_chronicle_location: str | None = None`
    - Add `field_styles: dict[str, dict] | None = None`
    - Add `fields: list[FieldEntry] | None = None`
    - _Requirements: 1.1, 3.1, 6.1, 7.1, 13.1, 13.2, 13.3, 13.4_

- [x] 2. Extend Blueprint parsing and inheritance in `blueprint.py`
  - [x] 2.1 Implement `_validate_parameters`, `_parse_field_entry`, and `_merge_parameters` functions
    - `_validate_parameters`: validate parameters is a dict-of-dicts, raise descriptive error otherwise
    - `_parse_field_entry`: convert raw dict to `FieldEntry`, validate `name` is present and a string, validate property types
    - `_merge_parameters`: merge parent and child parameter dicts at group and individual parameter level, child overrides parent
    - _Requirements: 1.4, 2.1, 2.2, 2.3, 2.4, 7.2, 13.5_

  - [x] 2.2 Implement `_merge_field_styles` and extend `parse_blueprint` to handle new properties
    - `_merge_field_styles`: merge parent and child field_styles dicts, child definitions override parent for same name
    - Extend `parse_blueprint` to parse `parameters` (validated), `defaultChronicleLocation` (validated as string), `field_styles` (validated as dict), and `fields` (validated as list, each entry parsed via `_parse_field_entry`)
    - Validate `defaultChronicleLocation` is a string when present, raise descriptive error otherwise
    - _Requirements: 1.1, 1.4, 3.1, 3.4, 6.1, 6.8, 7.1, 13.1, 13.2, 13.3, 13.4, 13.5_

  - [x] 2.3 Extend `load_blueprint_with_inheritance` for parameter/style merging and field name validation
    - Merge parameters through the full inheritance chain (root ancestor → parent → child)
    - Merge field_styles through the full inheritance chain
    - Validate field name uniqueness across the inheritance chain (child field names must not duplicate parent field names)
    - Return merged parameters and merged field_styles alongside the existing return values
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.8, 10.1, 10.4_

  - [x] 2.4 Write unit tests for extended Blueprint parsing (`tests/blueprint2layout/test_blueprint_fields.py`)
    - Test parsing Blueprints with parameters, defaultChronicleLocation, field_styles, and fields
    - Test parameter validation (dict-of-dicts, error on malformed)
    - Test field entry parsing (required name, valid types, missing name error)
    - Test parameter merging (parent-only groups, child-only groups, shared groups with child override)
    - Test field_styles merging (child overrides parent for same name)
    - Test field name uniqueness validation across inheritance
    - Test backward compatibility: Blueprints with only canvases parse identically to before
    - _Requirements: 1.1, 1.4, 2.1, 2.2, 2.3, 2.4, 3.1, 3.4, 6.1, 6.8, 7.2, 10.4, 13.5, 13.6_

  - [x] 2.5 Write property tests for Blueprint parsing (`tests/blueprint2layout/test_blueprint_fields_pbt.py`)
    - **Property 1: Pass-through properties round-trip**
    - **Validates: Requirements 1.2, 3.2**
    - **Property 2: Parameter merging preserves all definitions with child-wins override**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    - **Property 7: Field style merging is child-overrides-parent**
    - **Validates: Requirements 6.8**
    - **Property 14: Invalid root property types raise errors**
    - **Validates: Requirements 1.4, 3.4**

- [x] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Extend edge value resolution in `resolver.py`
  - [x] 4.1 Add secondary axis reference resolution and grey box reference resolution
    - Add `SECONDARY_AXIS_PATTERN` regex: `r"^(h_thin|h_bar|h_rule|v_thin|v_bar|grey_box)\[(\d+)\]\.(left|right|top|bottom)$"`
    - Add valid secondary edge maps: horizontal → `{left, right}`, vertical → `{top, bottom}`, grey_box → `{left, right, top, bottom}`
    - Extend `resolve_edge_value` to check secondary axis pattern before canvas reference pattern
    - Resolve horizontal `.left` → x, `.right` → x2; vertical `.top` → y, `.bottom` → y2; grey_box all four edges
    - Raise descriptive error for invalid edge names per category (e.g., `.top` on horizontal line)
    - Remove the existing grey_box rejection in `_resolve_line_reference` since grey_box is now handled via secondary axis pattern
    - Update `LINE_REFERENCE_PATTERN` to exclude `grey_box` from plain line references (grey_box requires a secondary edge)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 12.1, 12.3, 12.4, 12.5_

  - [x] 4.2 Write unit tests for extended resolver (`tests/blueprint2layout/test_resolver_extended.py`)
    - Test secondary axis references on horizontal lines (`.left`, `.right`)
    - Test secondary axis references on vertical lines (`.top`, `.bottom`)
    - Test grey box edge references (all four edges)
    - Test plain line references still work unchanged
    - Test invalid secondary edge names raise descriptive errors
    - Test unrecognized edge value strings raise errors
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 12.1, 12.3, 12.5_

  - [x] 4.3 Write property tests for extended resolver (`tests/blueprint2layout/test_resolver_extended_pbt.py`)
    - **Property 3: Secondary axis resolution matches element attributes**
    - **Validates: Requirements 4.1, 4.2, 4.5, 12.1, 12.3**
    - **Property 4: Invalid secondary edge names raise errors**
    - **Validates: Requirements 4.4**
    - **Property 16: Unrecognized edge value strings raise errors**
    - **Validates: Requirements 12.5**

- [x] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement field resolver (`blueprint2layout/field_resolver.py`)
  - [x] 6.1 Implement `resolve_field_styles` for style composition chain resolution
    - Resolve styles recursively: base styles first, then more specific styles, then field direct properties
    - Track visited style names to detect circ
 * fontsize / page_dimension * 100` (height for top/bottom, width for left/right)
    - Derive page dimensions from aspectratio string (e.g., "603:783" → width=603, height=783 points)
    - Apply `+` (add) or `-` (subtract) operator
    - Raise error if em offset used without fontsize
    - For non-em edge values, delegate to `resolve_edge_value`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.8, 5.9, 12.2_

  - [x] 6.3 Implement `compute_top_default` and `resolve_fields` orchestrator
    - `compute_top_default`: compute `bottom - (fontsize / page_height * 100)` from aspectratio
    - `resolve_fields`: for each field — resolve styles, validate canvas/type, resolve edges (including em offsets), apply top-edge default when top is omitted, convert to parent-relative coordinates using existing `convert_to_parent_relative` logic, return ordered list of `ResolvedField`
    - Validate field type is one of `{text, multiline, line, rectangle}`
    - Validate field references a defined canvas
    - Raise descriptive error when top is omitted but bottom or fontsize is missing
    - _Requirements: 5.6, 5.7, 7.3, 7.4, 7.10, 7.11, 7.12, 8.1, 8.2, 8.3, 9.6_

  - [x] 6.4 Write unit tests for field resolver (`tests/blueprint2layout/test_field_resolver.py`)
    - Test style resolution: single style, chained styles, direct property override
    - Test circular style reference detection
    - Test undefined style reference error
    - Test em offset computation for top/bottom (uses height) and left/right (uses width)
    - Test em offset with `+` and `-` operators
    - Test em offset error when fontsize is missing
    - Test top-edge default computation (bottom - 1em)
    - Test top-edge default error when bottom or fontsize missing
    - Test full field resolution with parent-relative coordinate conversion
    - Test field type validation
    - Test field canvas reference validation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7, 6.3, 6.4, 6.5, 6.6, 6.7, 7.10, 7.12, 8.1, 8.2_

  - [x] 6.5 Write property tests for field resolver (`tests/blueprint2layout/test_field_resolver_pbt.py`)
    - **Property 5: Em offset computation is correct**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.8, 5.9, 12.2**
    - **Property 6: Style override ordering follows last-writer-wins**
    - **Validates: Requirements 6.4, 6.5**
    - **Property 8: Top edge defaults to bottom minus one em**
    - **Validates: Requirements 8.1**
    - **Property 15: Missing required field properties after resolution raise errors**
    - **Validates: Requirements 7.10, 8.2**

- [x] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Extend output assembly in `output.py`
  - [x] 8.1 Implement `_generate_content_element` and extend `assemble_layout`
    - `_generate_content_element`: generate content element dict from `ResolvedField`, inline all non-None styling properties, wrap in trigger element when trigger is present
    - Extend `assemble_layout` signature to accept `resolved_fields` and `merged_parameters`
    - Add `defaultChronicleLocation` to output when present on Blueprint
    - Add `parameters` section to output when merged_parameters is not None
    - Add `content` section with generated content elements when resolved_fields is not None and non-empty
    - Maintain output key ordering: id, parent, description, flags, aspectratio, defaultChronicleLocation, parameters, canvas, content
    - Ensure backward compatibility: canvas-only Blueprints produce identical output to before
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.7, 9.8, 9.9, 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 8.2 Write unit tests for extended output (`tests/blueprint2layout/test_output_fields.py`)
    - Test output with parameters section
    - Test output with defaultChronicleLocation
    - Test output with content elements from resolved fields
    - Test content element with param value (`"param:<name>"`)
    - Test content element with static value
    - Test trigger wrapping
    - Test output key ordering
    - Test backward compatibility (no parameters/fields → same output as before)
    - Test only non-None styling properties are included
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.7, 9.8, 9.9, 11.1, 11.4_

  - [x] 8.3 Write property tests for extended output (`tests/blueprint2layout/test_output_fields_pbt.py`)
    - **Property 9: Content element generation preserves field properties**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.8**
    - **Property 10: Trigger fields produce wrapper elements**
    - **Validates: Requirements 9.7**
    - **Property 11: Output contains only child Blueprint's fields**
    - **Validates: Requirements 10.2**
    - **Property 12: Canvas-only Blueprints produce backward-compatible output**
    - **Validates: Requirements 11.4, 13.6**
    - **Property 13: Output JSON round-trip stability**
    - **Validates: Requirements 14.1, 14.2, 14.3**
    - **Property 17: Output section ordering**
    - **Validates: Requirements 11.1**

- [x] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Wire pipeline and add Hypothesis strategies
  - [x] 10.1 Extend `generate_layout` in `__init__.py` to integrate field resolution and extended output
    - After `resolve_canvases`, call `resolve_fields` when Blueprint has fields
    - Pass merged parameters and resolved fields to extended `assemble_layout`
    - Handle the case where Blueprint has no fields (skip field resolution, pass None)
    - Ensure the aspectratio is available for em offset computation (inherit from parent chain if needed)
    - _Requirements: 10.1, 10.2, 10.3, 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 10.2 Add Hypothesis strategies to `tests/blueprint2layout/conftest.py`
    - `parameter_groups()`: generates valid parameter group dicts (dict of dicts)
    - `field_style_dicts()`: generates valid field_styles dicts (no circular refs)
    - `field_entries()`: generates valid FieldEntry instances with consistent canvas/type/edge values
    - `detection_results_with_elements()`: generates DetectionResult with at least one element per category
    - `aspectratio_strings()`: generates valid aspectratio strings
    - `em_offset_expressions()`: generates valid em offset expression strings
    - _Requirements: supports all property tests_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (17 total)
- Unit tests validate specific examples and edge cases
- The design uses Python throughout — no language selection needed
- All new code goes in the `blueprint2layout/` package, all new tests in `tests/blueprint2layout/`
