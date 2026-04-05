# Requirements Document

## Introduction

The Layout Data Mode is a new visualization mode (`--mode data`) for the existing `layout_visualizer` CLI tool. Instead of drawing colored overlay rectangles (as `canvases` and `fields` modes do), this mode renders the actual example data from the layout's `parameters` section into the correct positions on the chronicle PDF. Each content entry's example text is rendered using the font, fontsize, fontweight, and alignment specified in the content entry (with preset inheritance). This allows layout authors to preview how a filled-in chronicle sheet would look using the example data, verifying that text positioning, sizing, and alignment are correct.

## Glossary

- **Layout_Visualizer**: The existing command-line utility that produces visualization PNGs of chronicle sheet layouts.
- **Data_Mode**: The new `--mode data` operating mode that renders example parameter values as text on the chronicle PDF instead of drawing colored overlay rectangles.
- **Layout_File**: A resolved JSON file conforming to the Layout Format specification, containing parameters, canvas regions, presets, and content entries.
- **Content_Entry**: An element in the layout's `content` array that specifies a value to render, its type, positioning (canvas, x, y, x2, y2), and styling (font, fontsize, fontweight, align).
- **Parameter_Reference**: A content entry `value` field in the form `"param:param_name"` that references a named parameter in the layout's `parameters` section.
- **Example_Value**: The `example` field of a parameter definition, containing sample data used for preview rendering.
- **Preset**: A reusable property bundle defined in the layout's `presets` object that provides default styling and positioning values to content entries.
- **Alignment_Code**: A two-character string specifying horizontal (L/C/R) and vertical (B/M/T) text alignment within a content entry's bounding box.
- **Merged_Layout**: The fully resolved layout produced by walking the inheritance chain and merging parameters, canvases, presets, and content from root to leaf.
- **Data_Renderer**: The module responsible for rendering example text onto the PDF page pixmap at resolved pixel positions with the specified styling.
- **Multiline_Entry**: A content entry of type `multiline` that has a `lines` property specifying the number of text lines to render within the bounding box.

## Requirements

### Requirement 1: CLI Mode Extension

**User Story:** As a layout author, I want to run the visualizer with `--mode data`, so that I can preview how example data looks when rendered on the chronicle PDF.

#### Acceptance Criteria

1. THE Layout_Visualizer SHALL accept `data` as a valid value for the `--mode` argument, in addition to the existing `canvases` and `fields` values.
2. WHEN `--mode data` is specified, THE Layout_Visualizer SHALL render Example_Values from the Merged_Layout's parameters onto the chronicle PDF instead of drawing colored overlay rectangles.
3. THE Layout_Visualizer SHALL produce a PNG output file when running in Data_Mode, using the same output path resolution as existing modes.

### Requirement 2: Parameter Example Loading

**User Story:** As a layout author, I want the visualizer to load example values from the full inheritance chain, so that parameters defined in parent layouts are included in the preview.

#### Acceptance Criteria

1. WHEN running in Data_Mode, THE Layout_Visualizer SHALL load the `parameters` section from each layout in the inheritance chain and merge them from root to leaf, with child definitions overriding parent definitions for parameters with the same name.
2. WHEN a Content_Entry contains a Parameter_Reference (`value: "param:param_name"`), THE Layout_Visualizer SHALL look up the referenced parameter across all parameter groups in the Merged_Layout.
3. WHEN a referenced parameter has an `example` field, THE Layout_Visualizer SHALL use the Example_Value as the text to render.
4. IF a referenced parameter does not exist in the Merged_Layout, THEN THE Layout_Visualizer SHALL skip that Content_Entry and output a warning, naming the referenced parameter.
5. IF a referenced parameter exists but has no `example` field, THEN THE Layout_Visualizer SHALL skip that Content_Entry and output a warning, naming the referenced parameter..

### Requirement 3: Preset Resolution

**User Story:** As a layout author, I want content entries to inherit styling from presets, so that the rendered text uses the correct font, size, weight, and alignment even when those values come from presets rather than being specified inline.

#### Acceptance Criteria

1. WHEN a Content_Entry references one or more Presets via its `presets` array, THE Layout_Visualizer SHALL resolve the preset chain (including nested preset references) and apply the inherited properties as defaults.
2. WHEN a Content_Entry specifies a property (font, fontsize, fontweight, align, canvas, x, y, x2, y2) both inline and via a Preset, THE Layout_Visualizer SHALL use the inline value, treating it as an override of the Preset default.
3. THE Layout_Visualizer SHALL load the `presets` section from each layout in the inheritance chain and merge them from root to leaf, with child definitions overriding parent definitions for presets with the same name.

### Requirement 4: Text Rendering

**User Story:** As a layout author, I want example text rendered at the correct position with the correct styling, so that I can verify the layout's font choices, sizes, and positioning are correct.

#### Acceptance Criteria

1. WHEN rendering a Content_Entry of type `text`, THE Data_Renderer SHALL render the Example_Value as a single line of text within the Content_Entry's resolved pixel bounding box.
2. THE Data_Renderer SHALL use the `font` property from the resolved Content_Entry to select the font family for rendering.
3. THE Data_Renderer SHALL use the `fontsize` property from the resolved Content_Entry to set the font size in points for rendering.
4. WHEN the resolved Content_Entry has `fontweight` set to `"bold"`, THE Data_Renderer SHALL render the text in bold.
5. THE Data_Renderer SHALL convert the Example_Value to a string before rendering, handling numeric example values (integers and floats) by converting them to their string representation.

### Requirement 5: Alignment Handling

**User Story:** As a layout author, I want text aligned according to the layout's alignment codes, so that the preview matches how the chronicle generator would render the data.

#### Acceptance Criteria

1. THE Data_Renderer SHALL interpret the first character of the Alignment_Code as horizontal alignment: `L` for left, `C` for center, `R` for right.
2. THE Data_Renderer SHALL interpret the second character of the Alignment_Code as vertical alignment: `B` for bottom, `M` for middle, `T` for top.
3. WHEN horizontal alignment is `L`, THE Data_Renderer SHALL position the text starting at the left edge of the bounding box.
4. WHEN horizontal alignment is `C`, THE Data_Renderer SHALL position the text centered horizontally within the bounding box.
5. WHEN horizontal alignment is `R`, THE Data_Renderer SHALL position the text ending at the right edge of the bounding box.
6. WHEN vertical alignment is `B`, THE Data_Renderer SHALL position the text baseline at the bottom edge of the bounding box.
7. WHEN vertical alignment is `M`, THE Data_Renderer SHALL position the text baseline at the vertical center of the bounding box.
8. WHEN vertical alignment is `T`, THE Data_Renderer SHALL position the text baseline at the top edge of the bounding box.

### Requirement 6: Multiline Text Rendering

**User Story:** As a layout author, I want multiline content entries rendered with the correct number of lines, so that I can verify that multi-line fields like notes and reputation have proper spacing.

#### Acceptance Criteria

1. WHEN rendering a Content_Entry of type `multiline`, THE Data_Renderer SHALL divide the bounding box height evenly by the `lines` property to determine the height of each line slot.
2. WHEN the Example_Value contains fewer characters than would fill all lines, THE Data_Renderer SHALL render the Example_Value in the first line slot.
3. THE Data_Renderer SHALL apply the same font, fontsize, fontweight, and horizontal alignment to each line of a Multiline_Entry as specified in the resolved Content_Entry.

### Requirement 7: Non-Text Content Entry Handling

**User Story:** As a layout author, I want the data mode to focus on text rendering and gracefully skip non-text content types, so that the preview is clean and focused on verifiable text positioning.

#### Acceptance Criteria

1. WHEN a Content_Entry has type `checkbox`, THE Data_Renderer SHALL skip rendering that entry.
2. WHEN a Content_Entry has type `strikeout`, THE Data_Renderer SHALL skip rendering that entry.
3. WHEN a Content_Entry has type `line`, THE Data_Renderer SHALL skip rendering that entry.
4. WHEN a Content_Entry has type `rectangle`, THE Data_Renderer SHALL skip rendering that entry.
5. WHEN a Content_Entry has type `trigger`, THE Data_Renderer SHALL process the nested `content` array within the trigger, applying the same rendering rules to each nested entry.
6. WHEN a Content_Entry has type `choice`, THE Data_Renderer SHALL process all nested content arrays within the choice's `content` map, applying the same rendering rules to each nested entry.

### Requirement 8: Watch Mode Compatibility

**User Story:** As a layout author, I want `--mode data` to work with the `--watch` flag, so that I can see my layout changes reflected in the data preview automatically.

#### Acceptance Criteria

1. WHEN `--mode data` is combined with the `--watch` flag, THE Layout_Visualizer SHALL monitor layout files for changes and regenerate the data preview PNG, using the same watch behavior as existing modes.

### Requirement 9: Error Handling

**User Story:** As a layout author, I want clear feedback when something goes wrong during data mode rendering, so that I can diagnose and fix layout issues.

#### Acceptance Criteria

1. IF the Layout_File contains no `content` array in the Merged_Layout, THEN THE Layout_Visualizer SHALL produce a PNG showing only the PDF background with no rendered text.
2. IF the Layout_File contains no `parameters` section in the Merged_Layout, THEN THE Layout_Visualizer SHALL produce a PNG showing only the PDF background with no rendered text.
3. IF a Content_Entry references a canvas that does not exist in the Merged_Layout, THEN THE Layout_Visualizer SHALL skip that Content_Entry and continue rendering the remaining entries.
