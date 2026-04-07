# Requirements Document

## Introduction

The Layout Visualizer's `--mode fields` currently highlights content fields that have explicit inline coordinates (`canvas`, `x`, `y`, `x2`, `y2`). However, strikeout entries in the `items` field and checkbox entries in the `summary_checkbox` field use presets to define their coordinates — a `strikeout_item` base preset provides the canvas and horizontal bounds while per-line presets (e.g., `item.line.xxx`) provide the vertical bounds, and a `checkbox` base preset provides the canvas while per-checkbox presets (e.g., `checkbox.some_key`) provide the coordinates. Because the field extraction logic does not resolve presets, these strikeout lines and checkboxes are invisible in fields mode. This feature adds support for resolving preset-based coordinates so that each strikeout item line and each checkbox is highlighted with a colored rectangle and label, consistent with how other content fields are visualized.

## Glossary

- **Layout_Visualizer**: The command-line utility that produces visualization PNGs of chronicle sheet layouts.
- **Fields_Mode**: The `--mode fields` visualization mode that draws colored rectangles for each content field position.
- **Content_Entry**: A single element in a layout's `content` array, having a `type` and positioning properties.
- **Strikeout_Entry**: A Content_Entry with `"type": "strikeout"` that represents a visual strikethrough mark on an item line.
- **Checkbox_Entry**: A Content_Entry with `"type": "checkbox"` that represents a checkbox mark drawn at specific coordinates on the summary canvas.
- **Preset**: A named set of default properties defined in the layout's `presets` object. Content entries reference presets by name to inherit positioning and styling properties.
- **Preset_Resolution**: The process of merging preset properties into a Content_Entry, where inline properties on the entry override preset values.
- **Items_Canvas**: The canvas region named `items` that contains the item list area on a chronicle sheet.
- **Summary_Canvas**: The canvas region named `summary` that contains the adventure summary area with checkboxes.
- **Field_Extraction**: The process of collecting positioned Content_Entries from the merged layout content and converting each into a CanvasRegion for visualization.

## Requirements

### Requirement 1: Preset Resolution for Field Extraction

**User Story:** As a layout author, I want the field extraction logic to resolve presets on content entries, so that entries whose coordinates come from presets are included in the visualization.

#### Acceptance Criteria

1. WHEN extracting content fields for Fields_Mode, THE Layout_Visualizer SHALL resolve presets on each Content_Entry before checking for positioning properties.
2. WHEN a Content_Entry has a `presets` array, THE Layout_Visualizer SHALL merge properties from the referenced Preset definitions in order, with later presets overriding earlier presets for the same property.
3. WHEN a Content_Entry has both preset-inherited properties and inline properties, THE Layout_Visualizer SHALL use the inline property values as overrides over the preset values.
4. WHEN a Preset references nested presets, THE Layout_Visualizer SHALL resolve the nested preset chain recursively before applying the outer preset properties.

### Requirement 2: Strikeout Entry Visualization

**User Story:** As a layout author, I want each strikeout item line to appear as a highlighted rectangle in `--mode fields`, so that I can verify the positioning of item strikethrough marks on the chronicle sheet.

#### Acceptance Criteria

1. WHEN operating in Fields_Mode, THE Layout_Visualizer SHALL include Strikeout_Entry elements in the set of extracted fields.
2. WHEN a Strikeout_Entry has resolved coordinates (`canvas`, `x`, `y`, `x2`, `y2`) after Preset_Resolution, THE Layout_Visualizer SHALL create a field rectangle at the resolved position.
3. THE Layout_Visualizer SHALL label each Strikeout_Entry rectangle with the choice key text that maps to the entry (e.g., "potion of invisibility (level 4; 20 gp)").
4. THE Layout_Visualizer SHALL draw each Strikeout_Entry rectangle with a color from the same palette used for other field rectangles, following the same color assignment and cycling rules.
5. THE Layout_Visualizer SHALL draw each Strikeout_Entry rectangle with the same semi-transparent fill, solid border, and label styling used for other field rectangles.

### Requirement 3: Choice Content Traversal for Preset-Based Entries

**User Story:** As a layout author, I want all strikeout and checkbox entries within a choice content map to be visualized, so that I can see every possible position on the sheet.

#### Acceptance Criteria

1. WHEN a Content_Entry has `"type": "choice"`, THE Layout_Visualizer SHALL iterate over all keys in the choice `content` map and extract fields from each key's content array.
2. THE Layout_Visualizer SHALL include all Strikeout_Entries and Checkbox_Entries found across all keys of the choice content map in the visualization.
3. THE Layout_Visualizer SHALL use the choice content map key (the descriptive text) as the label for each extracted Strikeout_Entry or Checkbox_Entry field rectangle.

### Requirement 4: Preset Merging with Inheritance

**User Story:** As a layout author, I want presets from parent layouts to be available during field extraction, so that strikeout entries in child layouts that reference inherited presets are correctly resolved.

#### Acceptance Criteria

1. WHEN extracting content fields, THE Layout_Visualizer SHALL merge presets from the full inheritance chain (root to leaf), with child preset definitions overriding parent definitions for the same preset name.
2. WHEN a Strikeout_Entry references a preset defined in a parent layout, THE Layout_Visualizer SHALL resolve the preset coordinates from the inherited definition.

### Requirement 5: Graceful Handling of Unresolvable Entries

**User Story:** As a layout author, I want the visualizer to skip entries that cannot be fully resolved, so that a single misconfigured entry does not prevent the rest of the visualization from rendering.

#### Acceptance Criteria

1. IF a Content_Entry references a preset name that does not exist in the merged preset definitions, THEN THE Layout_Visualizer SHALL skip the entry and continue processing remaining entries.
2. IF a Content_Entry lacks required positioning properties (`canvas`, `x`, `y`, `x2`, `y2`) after Preset_Resolution, THEN THE Layout_Visualizer SHALL skip the entry and continue processing remaining entries.
3. IF a resolved Content_Entry references a canvas name that does not exist in the merged canvas definitions, THEN THE Layout_Visualizer SHALL skip the entry and continue processing remaining entries.

### Requirement 6: Checkbox Entry Visualization

**User Story:** As a layout author, I want each checkbox to appear as a highlighted rectangle in `--mode fields`, so that I can verify the positioning of checkboxes on the chronicle sheet.

#### Acceptance Criteria

1. WHEN operating in Fields_Mode, THE Layout_Visualizer SHALL include Checkbox_Entry elements in the set of extracted fields.
2. WHEN a Checkbox_Entry has resolved coordinates (`canvas`, `x`, `y`, `x2`, `y2`) after Preset_Resolution, THE Layout_Visualizer SHALL create a field rectangle at the resolved position.
3. THE Layout_Visualizer SHALL label each Checkbox_Entry rectangle with the choice key text that maps to the entry (e.g., "killed", "recruited").
4. THE Layout_Visualizer SHALL draw each Checkbox_Entry rectangle with a color from the same palette used for other field rectangles, following the same color assignment and cycling rules.
5. THE Layout_Visualizer SHALL draw each Checkbox_Entry rectangle with the same semi-transparent fill, solid border, and label styling used for other field rectangles.
6. WHEN a Checkbox_Entry is nested inside a choice Content_Entry, THE Layout_Visualizer SHALL extract Checkbox_Entries from all keys in the choice content map, using each key as the label.
