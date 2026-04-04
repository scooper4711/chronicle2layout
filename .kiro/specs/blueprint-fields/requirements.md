# Requirements Document

## Introduction

Extends the Blueprint file format and the `blueprint2layout` tool to support parameters, fields, and content generation. Currently, Blueprints only declare `canvases` — rectangular regions positioned using line references, canvas references, and numeric literals. The tool resolves these to percentage coordinates and emits a layout JSON with only `id`, `parent`, `description`, `flags`, `aspectratio`, and a `canvas` section. Parameters, presets, and content must still be hand-authored in separate layout JSON files.

This feature augments Blueprints so that a single Blueprint file can declare parameters, a default chronicle location, and an ordered array of fields that bind parameters to positioned regions on the PDF. The `blueprint2layout` tool will then emit a complete layout file including `parameters` and `content` sections — eliminating the need to hand-author these for season and game-level base layouts.

Blueprints target season-level and game-level base layouts (e.g., Season 5, Bounties). Individual scenario-level concerns (choice-based checkboxes, item strikeouts) are handled by existing tooling on the main branch and are out of scope for this feature.

Additionally, the edge value syntax is extended with secondary axis references on detected lines (e.g., `h_thin[3].left`, `v_bar[0].top`) and `em` offset expressions (e.g., `"h_thin[3] - 1.2em"`), giving field authors finer positioning control.

## Glossary

- **Layout_Generator**: The `blueprint2layout` Python tool that performs the end-to-end pipeline from PDF analysis to layout JSON output.
- **Blueprint**: A JSON file that declaratively describes canvas regions, parameters, and fields by referencing detected structural lines and previously defined canvases. Has a unique `id` property and may reference a parent Blueprint.
- **Parent_Blueprint**: A Blueprint referenced by another Blueprint's `parent` property. All canvases, parameters, and fields from the Parent_Blueprint are resolved first and available to the child.
- **Field_Entry**: An object in the Blueprint's `fields` array that binds a parameter (or static value) to a positioned region within a canvas, producing a content element in the output layout with all properties inlined.
- **Field_Style**: A named, reusable bundle of styling and positioning properties declared in the Blueprint's `field_styles` dictionary. Field_Entries reference Field_Styles via a `styles` array, inheriting their properties. Properties declared directly on the Field_Entry override those inherited from styles. Styles can also reference other styles via their own `styles` array, forming a composition chain.
- **Edge_Value**: A canvas or field edge specification: a numeric literal, a Line_Reference, a Canvas_Reference, or (for fields only) an Em_Offset_Expression.
- **Line_Reference**: A string of the form `category[index]` (e.g., `h_bar[0]`) that resolves to a detected line's primary-axis position, or `category[index].secondary_edge` for the secondary axis.
- **Secondary_Axis_Reference**: A Line_Reference with a secondary edge accessor: `.left` or `.right` on horizontal lines (resolving to x or x2), `.top` or `.bottom` on vertical lines (resolving to y or y2).
- **Canvas_Reference**: A string of the form `canvas_name.edge` (e.g., `summary.bottom`) that resolves to an already-resolved canvas edge value.
- **Em_Offset_Expression**: A string of the form `"<base_ref> +/- <N>em"` where `base_ref` is a Line_Reference, Secondary_Axis_Reference, or Canvas_Reference, and `N` is a positive decimal number. Resolves to the base value offset by N times the field's font size converted to page percentage.
- **Absolute_Percentage**: A coordinate expressed as a percentage (0–100) of the full page width or height.
- **Parent_Relative_Percentage**: A coordinate expressed as a percentage (0–100) of the parent canvas width or height.
- **Detection_Result**: A structured object containing six keyed arrays (`h_thin`, `h_bar`, `h_rule`, `v_thin`, `v_bar`, `grey_box`) of detected structural elements with percentage coordinates.

## Requirements

### Requirement 1: Parameters Pass-Through

**User Story:** As a layout author, I want to declare parameters in a Blueprint file using the same schema as layout parameters, so that the output layout includes a complete `parameters` section without hand-authoring a separate file.

#### Acceptance Criteria

1. THE Layout_Generator SHALL accept an optional `parameters` property at the root level of a Blueprint, structured as a dictionary of parameter groups, each group being a dictionary of parameter definitions matching the LAYOUT_FORMAT.md parameter schema.
2. WHEN a Blueprint contains a `parameters` property, THE Layout_Generator SHALL include the parameters in the output layout's `parameters` section, preserving the group names, parameter names, and all parameter properties exactly as declared.
3. WHEN a Blueprint omits the `parameters` property, THE Layout_Generator SHALL omit the `parameters` section from the output layout.
4. THE Layout_Generator SHALL validate that the `parameters` property, when present, is a dictionary of dictionaries, and raise a descriptive error for malformed parameter structures.

### Requirement 2: Parameter Inheritance

**User Story:** As a layout author, I want child Blueprints to inherit and merge parameters from parent Blueprints, so that common parameters (like Event Info and Player Info) are defined once in a parent and extended by children.

#### Acceptance Criteria

1. WHEN a child Blueprint has a Parent_Blueprint that defines parameters, THE Layout_Generator SHALL merge the child's parameters with the parent's parameters.
2. WHEN merging parameters, THE Layout_Generator SHALL combine parameter groups: groups present only in the parent SHALL be included, groups present only in the child SHALL be added, and groups present in both SHALL have their parameter definitions merged.
3. WHEN a parameter group exists in both parent and child, THE Layout_Generator SHALL merge individual parameter definitions within the group: parameters present only in the parent SHALL be included, parameters present only in the child SHALL be added, and parameters present in both SHALL use the child's definition (child overrides parent).
4. THE Layout_Generator SHALL perform parameter merging recursively through the full inheritance chain, applying merges from root ancestor to immediate parent to child in order.

### Requirement 3: Default Chronicle Location Pass-Through

**User Story:** As a layout author, I want to declare a `defaultChronicleLocation` string in a Blueprint, so that the output layout includes the Foundry VTT module path to the chronicle PDF.

#### Acceptance Criteria

1. THE Layout_Generator SHALL accept an optional `defaultChronicleLocation` property at the root level of a Blueprint, with a string value.
2. WHEN a Blueprint contains a `defaultChronicleLocation` property, THE Layout_Generator SHALL include the property in the output layout exactly as declared.
3. WHEN a Blueprint omits the `defaultChronicleLocation` property, THE Layout_Generator SHALL omit the property from the output layout.
4. IF the `defaultChronicleLocation` property is present but not a string, THEN THE Layout_Generator SHALL raise a descriptive error.

### Requirement 4: Secondary Axis References on Detected Lines

**User Story:** As a layout author, I want to reference the secondary axis of detected lines (e.g., where a horizontal line starts and ends horizontally), so that I can position field edges using the full extent of detected structural elements.

#### Acceptance Criteria

1. WHEN an Edge_Value is a Secondary_Axis_Reference on a horizontal line (e.g., `h_thin[3].left` or `h_bar[1].right`), THE Layout_Generator SHALL resolve `.left` to the line's x position and `.right` to the line's x2 position.
2. WHEN an Edge_Value is a Secondary_Axis_Reference on a vertical line (e.g., `v_bar[0].top` or `v_thin[2].bottom`), THE Layout_Generator SHALL resolve `.top` to the line's y position and `.bottom` to the line's y2 position.
3. WHEN an Edge_Value is a plain Line_Reference without a secondary edge (e.g., `h_bar[0]`), THE Layout_Generator SHALL continue to resolve to the primary axis value as before (y for horizontal, x for vertical).
4. IF a Secondary_Axis_Reference uses an invalid edge name for the element category (e.g., `h_thin[0].top`), THEN THE Layout_Generator SHALL raise a descriptive error explaining which secondary edges are valid for that category.
5. WHEN an Edge_Value is a Secondary_Axis_Reference on a `grey_box` element (e.g., `grey_box[0].left`, `grey_box[0].right`, `grey_box[0].top`, `grey_box[0].bottom`), THE Layout_Generator SHALL resolve to the corresponding edge of the grey box's bounding rectangle.
6. Secondary_Axis_References SHALL be valid in both canvas edge values and field edge values.

### Requirement 5: Em Offset Expressions

**User Story:** As a layout author, I want to offset edge positions by a number of `em` units relative to a field's font size, so that I can position text fields with typographically meaningful spacing.

#### Acceptance Criteria

1. WHEN a field Edge_Value is an Em_Offset_Expression (e.g., `"h_thin[3] - 1.2em"`), THE Layout_Generator SHALL resolve the base reference to an Absolute_Percentage, then add or subtract the em offset converted to a page percentage.
2. THE Layout_Generator SHALL compute the em offset as: `offset_percentage = em_count * fontsize / page_dimension * 100`, where `page_dimension` is the page height (in points) for vertical offsets (top/bottom edges) and the page width (in points) for horizontal offsets (left/right edges).
3. WHEN the operator is `+`, THE Layout_Generator SHALL add the offset (moving toward bottom for vertical edges, toward right for horizontal edges).
4. WHEN the operator is `-`, THE Layout_Generator SHALL subtract the offset (moving toward top for vertical edges, toward left for horizontal edges).
5. THE Layout_Generator SHALL derive the page dimensions from the Blueprint's `aspectratio` property (or inherited aspectratio) and a reference font size unit of 72 points per inch.
6. Em_Offset_Expressions SHALL only be valid on Field_Entry edge values, not on canvas edge values.
7. IF an Em_Offset_Expression is used on a canvas edge value, THEN THE Layout_Generator SHALL raise a descriptive error explaining that em offsets require font context and are only available on fields.
8. THE Layout_Generator SHALL support Em_Offset_Expressions with any valid base reference: Line_References, Secondary_Axis_References, and Canvas_References.
9. THE Layout_Generator SHALL parse the em value as a positive decimal number (integer or float) following the `+` or `-` operator and preceding the `em` suffix.

### Requirement 6: Field Styles

**User Story:** As a layout author, I want to define reusable field styles (font, size, alignment, canvas, edges, etc.) and reference them from multiple fields, so that I don't have to repeat common styling on every field.

#### Acceptance Criteria

1. THE Layout_Generator SHALL accept an optional `field_styles` property at the root level of a Blueprint, structured as a dictionary mapping style names (strings) to style definition objects.
2. EACH style definition object MAY contain any property valid on a Field_Entry: `canvas`, `type`, `font`, `fontsize`, `fontweight`, `align`, `color`, `linewidth`, `size`, `lines`, `left`, `right`, `top`, `bottom`.
3. EACH style definition object MAY contain a `styles` array referencing other style names, forming a composition chain (styles inherit from other styles).
4. WHEN resolving a Field_Entry's effective properties, THE Layout_Generator SHALL apply styles in the order listed in the field's `styles` array, with later styles overriding earlier ones, and properties declared directly on the Field_Entry overriding all styles.
5. WHEN a style itself references other styles via its own `styles` array, THE Layout_Generator SHALL resolve the chain recursively, applying base styles first and more specific styles later.
6. IF a `styles` array references a style name that is not defined in the Blueprint's `field_styles` (or inherited field_styles), THEN THE Layout_Generator SHALL raise a descriptive error.
7. IF style resolution encounters a circular reference, THEN THE Layout_Generator SHALL raise a descriptive error.
8. Field_Styles SHALL inherit from parent Blueprints: a child Blueprint's `field_styles` are merged with the parent's, with child definitions overriding parent definitions for the same style name.
9. THE `fontsize` used for em offset computation and top-edge defaulting SHALL be the effective fontsize after style resolution.

### Requirement 7: Field Entry Parsing

**User Story:** As a layout author, I want to declare fields in a Blueprint as an ordered array of field entries, so that each field binds a parameter to a positioned region on the PDF.

#### Acceptance Criteria

1. THE Layout_Generator SHALL accept an optional `fields` property at the root level of a Blueprint, structured as an ordered array of Field_Entry objects.
2. EACH Field_Entry SHALL have a `name` property (string, required) that uniquely identifies the field within the Blueprint.
3. EACH Field_Entry SHALL have a `canvas` property (string, required) specifying which canvas the field renders in. This MAY be inherited from a Field_Style.
4. EACH Field_Entry SHALL have a `type` property (string, required) specifying the element type, which SHALL be one of: `text`, `multiline`, `line`, `rectangle`. This MAY be inherited from a Field_Style.
5. EACH Field_Entry MAY have a `param` property (string) naming the parameter this field renders, or a `value` property (string) for static text.
6. EACH Field_Entry MAY have edge properties `left`, `right`, `top`, `bottom`, each being an Edge_Value (numeric literal, Line_Reference, Secondary_Axis_Reference, Canvas_Reference, or Em_Offset_Expression).
7. EACH Field_Entry MAY have styling properties that are passed through to the output preset: `font`, `fontsize`, `fontweight`, `align`, `color`, `linewidth`, `size`, `lines`.
8. EACH Field_Entry MAY have a `styles` array referencing Field_Style names to inherit properties from (see Requirement 6).
9. EACH Field_Entry MAY have a `trigger` property (string) that wraps the output content element in a trigger element for conditional rendering.
10. AFTER style resolution, EACH Field_Entry SHALL have an effective `canvas` and `type` (either declared directly or inherited from styles). IF either is missing after resolution, THE Layout_Generator SHALL raise a descriptive error.
11. IF a Field_Entry has duplicate `name` within the same Blueprint (including inherited fields), THEN THE Layout_Generator SHALL raise a descriptive error.
12. IF a Field_Entry references a `canvas` that is not defined in the Blueprint or its ancestors, THEN THE Layout_Generator SHALL raise a descriptive error.

### Requirement 8: Field Top Edge Default

**User Story:** As a layout author, I want the `top` edge of a text field to default to `bottom - 1em` when omitted, so that single-line text fields only need a bottom edge and font size to be fully positioned.

#### Acceptance Criteria

1. WHEN a Field_Entry omits the `top` edge and has both a `bottom` edge and an effective `fontsize` (declared directly or inherited from Field_Styles), THE Layout_Generator SHALL compute the default `top` as the resolved `bottom` value minus one em (where 1em = fontsize / page_height * 100).
2. WHEN a Field_Entry omits the `top` edge and lacks either a `bottom` edge or an effective `fontsize` (after style resolution), THEN THE Layout_Generator SHALL raise a descriptive error explaining that `top` is required when `bottom` or `fontsize` is missing.
3. THE Layout_Generator SHALL apply the top-edge default after resolving the `bottom` edge value to an Absolute_Percentage.

### Requirement 9: Field Output Generation — Inline Content

**User Story:** As a layout author, I want each field to produce a content element in the output layout with all resolved properties inlined directly on the element, so that the output is self-contained without needing separate presets.

#### Acceptance Criteria

1. FOR each Field_Entry with a `param` property, THE Layout_Generator SHALL generate a content element with `value` set to `"param:<param_name>"` and `type` set to the field's effective type.
2. FOR each Field_Entry with a `value` property, THE Layout_Generator SHALL generate a content element with `value` set to the static text and `type` set to the field's effective type.
3. THE generated content element SHALL include the `canvas` property set to the field's effective canvas name.
4. THE generated content element SHALL include all resolved edge positions (`x`, `y`, `x2`, `y2`) as Parent_Relative_Percentages within the field's canvas.
5. THE generated content element SHALL include all effective styling properties (`font`, `fontsize`, `fontweight`, `align`, `color`, `linewidth`, `size`, `lines`) after style resolution.
6. THE Layout_Generator SHALL convert field edge values (left, right, top, bottom) to parent-relative coordinates (x, x2, y, y2) relative to the field's canvas, using the same conversion formula as canvas coordinates.
7. WHEN a Field_Entry has a `trigger` property, THE Layout_Generator SHALL wrap the content element inside a trigger element with `type` set to `"trigger"`, `trigger` set to `"param:<trigger_value>"`, and `content` containing the field's content element.
8. THE Layout_Generator SHALL emit content elements in the same order as the fields appear in the Blueprint's `fields` array.
9. THE Layout_Generator SHALL NOT generate a `presets` section for fields. All field properties SHALL be inlined on the content element.

### Requirement 10: Field Inheritance

**User Story:** As a layout author, I want child Blueprints to inherit fields from parent Blueprints, so that common fields (like character name, society ID, XP/GP fields) are defined once and reused.

#### Acceptance Criteria

1. WHEN a child Blueprint has a Parent_Blueprint that defines fields, THE Layout_Generator SHALL include the parent's fields in the resolution process, making parent canvases available for field canvas references.
2. THE Layout_Generator SHALL produce output content only from the child Blueprint's own fields, not from inherited parent fields (matching the scoping rule for canvases).
3. Child fields MAY reference canvases defined in parent Blueprints.
4. IF a child Blueprint defines a field with the same name as an inherited field, THEN THE Layout_Generator SHALL raise a descriptive error identifying the duplicate field name.

### Requirement 11: Complete Layout Output Assembly

**User Story:** As a layout author, I want the tool to produce a complete layout file with parameters, canvases, and content sections, so that the output is a fully functional season/game-level base layout requiring no hand-editing.

#### Acceptance Criteria

1. THE Layout_Generator SHALL produce an output layout containing sections in the following order: `id`, `parent` (if present), `description` (if present), `flags` (if present), `aspectratio` (if present), `defaultChronicleLocation` (if present), `parameters` (if present), `canvas`, `content` (if fields are defined).
2. THE `parameters` section SHALL contain the merged result of inherited parameters and Blueprint-declared parameters.
3. THE `content` section SHALL contain all content elements generated from the Blueprint's own fields, in field declaration order, with all properties inlined.
4. WHEN a Blueprint defines no fields, THE Layout_Generator SHALL produce output with only the sections it produces today (id, parent, description, flags, aspectratio, canvas) plus any declared parameters and defaultChronicleLocation — maintaining backward compatibility.
5. THE Layout_Generator SHALL format the output Layout_JSON with 2-space indentation.

### Requirement 12: Edge Value Resolution Extension

**User Story:** As a developer, I want the edge value resolver to handle the new reference types (secondary axis, em offsets) alongside the existing types, so that all edge value forms resolve correctly.

#### Acceptance Criteria

1. THE Layout_Generator SHALL extend the edge value resolver to recognize Secondary_Axis_References matching the pattern `category[index].edge` where edge is `left`, `right`, `top`, or `bottom`.
2. THE Layout_Generator SHALL extend the edge value resolver to recognize Em_Offset_Expressions matching the pattern `<base_ref> [+-] <number>em`.
3. THE Layout_Generator SHALL resolve grey_box references: `grey_box[index].left` to x, `grey_box[index].right` to x2, `grey_box[index].top` to y, `grey_box[index].bottom` to y2.
4. THE Layout_Generator SHALL continue to resolve existing edge value types (numeric literals, plain line references, canvas references) without change.
5. IF an edge value string does not match any recognized pattern (numeric, line reference, secondary axis reference, canvas reference, or em offset expression), THEN THE Layout_Generator SHALL raise a descriptive error.

### Requirement 13: Blueprint Parsing Extension

**User Story:** As a developer, I want the Blueprint parser to accept the new root-level properties (`parameters`, `defaultChronicleLocation`, `fields`) alongside existing properties, so that augmented Blueprints are parsed correctly.

#### Acceptance Criteria

1. THE Layout_Generator SHALL extend the Blueprint parser to accept and store the optional `parameters` property as a dictionary.
2. THE Layout_Generator SHALL extend the Blueprint parser to accept and store the optional `defaultChronicleLocation` property as a string.
3. THE Layout_Generator SHALL extend the Blueprint parser to accept and store the optional `field_styles` property as a dictionary mapping style names to style definition objects.
4. THE Layout_Generator SHALL extend the Blueprint parser to accept and store the optional `fields` property as an ordered list of Field_Entry objects.
5. THE Layout_Generator SHALL validate each Field_Entry during parsing, checking for required properties (`name`) and valid property types. Properties `canvas` and `type` are required after style resolution but may be inherited from styles.
6. Blueprints that contain only `canvases` (no parameters, fields, field_styles, or defaultChronicleLocation) SHALL continue to parse and produce output identically to the current behavior.

### Requirement 14: Round-Trip Consistency for Extended Output

**User Story:** As a developer, I want the extended layout output (with parameters, presets, and content) to be JSON-serializable and round-trip stable, so that generated layout files can be saved, loaded, and compared reliably.

#### Acceptance Criteria

1. THE Layout_JSON produced by the Layout_Generator SHALL be directly serializable to JSON using Python's `json.dumps` without custom encoders, including the new parameters and content sections.
2. FOR ALL valid Layout_JSON outputs with parameters and content, serializing to JSON and deserializing back SHALL produce a dictionary equal to the original output (round-trip property).
3. THE Layout_JSON SHALL contain only Python built-in types: `dict`, `list`, `float`, `int`, `str`, and `bool`.
