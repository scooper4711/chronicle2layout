# Requirements Document

## Introduction

The Layout Visualizer is a command-line utility that renders a visual representation of a chronicle sheet's canvas regions. Given a resolved layout JSON file and the corresponding chronicle PDF, the tool renders the PDF page as a background image and overlays semi-transparent colored rectangles for each canvas region defined in the layout. Each rectangle is labeled with the canvas name. The output is a PNG file that allows layout authors to quickly verify that canvas coordinates are correct and that regions align with the underlying PDF content.

## Glossary

- **Layout_Visualizer**: The command-line utility that produces the visualization PNG.
- **Layout_File**: A resolved JSON file conforming to the Layout Format specification, containing canvas regions with percentage-based coordinates.
- **Chronicle_PDF**: A Pathfinder Society chronicle sheet PDF file used as the background image.
- **Canvas_Region**: A named rectangular area defined in the layout's `canvas` object, with percentage-based coordinates relative to a parent canvas.
- **Resolved_Coordinates**: Absolute pixel coordinates computed by converting percentage-based canvas coordinates through the parent-child chain to page-level pixel positions.
- **Color_Assignment**: The process of assigning a distinct, visually distinguishable color to each canvas region for the overlay.
- **Label**: A text annotation placed on each colored rectangle showing the canvas region name.
- **Watch_Mode**: An optional operating mode where the Layout_Visualizer monitors the Layout_File for changes and automatically regenerates the PNG output, running continuously until interrupted by the user (Ctrl+C).

## Requirements

### Requirement 1: CLI Interface

**User Story:** As a layout author, I want to run the visualizer from the command line with a layout file and a chronicle PDF, so that I can quickly generate a visual overlay of the canvas regions.

#### Acceptance Criteria

1. THE Layout_Visualizer SHALL accept a positional argument for the path to a Layout_File.
2. THE Layout_Visualizer SHALL accept a positional argument for the path to a Chronicle_PDF.
3. THE Layout_Visualizer SHALL accept an optional argument for the output PNG file path.
4. WHEN no output path is provided, THE Layout_Visualizer SHALL write the PNG to the same directory as the Layout_File, using the layout file's base name with a `.png` extension.
5. THE Layout_Visualizer SHALL be invocable as `python -m layout_visualizer`.
6. THE Layout_Visualizer SHALL accept an optional `--watch` flag.

### Requirement 2: Layout Loading and Inheritance Resolution

**User Story:** As a layout author, I want the visualizer to resolve the full layout inheritance chain, so that I can visualize the complete set of canvas regions including those inherited from parent layouts.

#### Acceptance Criteria

1. WHEN a Layout_File is provided, THE Layout_Visualizer SHALL parse the JSON and extract the `canvas` object.
2. WHEN the Layout_File has a `parent` property, THE Layout_Visualizer SHALL locate and load the parent layout by searching the Layouts directory tree for a layout with a matching `id`.
3. WHEN a parent layout itself has a `parent` property, THE Layout_Visualizer SHALL recursively resolve the entire inheritance chain up to the root layout.
4. THE Layout_Visualizer SHALL merge canvas regions from the full inheritance chain, with child definitions overriding parent definitions for canvases with the same name.
5. IF a referenced parent layout file cannot be found, THEN THE Layout_Visualizer SHALL report an error identifying the missing parent id and exit with a non-zero status code.

### Requirement 3: PDF Rendering

**User Story:** As a layout author, I want the chronicle PDF rendered as a background image, so that I can see how the canvas regions align with the actual PDF content.

#### Acceptance Criteria

1. WHEN a Chronicle_PDF is provided, THE Layout_Visualizer SHALL render the first page of the PDF as a raster image.
2. THE Layout_Visualizer SHALL render the PDF page at 150 DPI resolution.
3. IF the Chronicle_PDF cannot be opened or is not a valid PDF, THEN THE Layout_Visualizer SHALL report a descriptive error and exit with a non-zero status code.

### Requirement 4: Canvas Coordinate Resolution

**User Story:** As a layout author, I want the percentage-based canvas coordinates converted to pixel positions on the rendered PDF, so that the overlay rectangles appear in the correct locations.

#### Acceptance Criteria

1. THE Layout_Visualizer SHALL convert each Canvas_Region's percentage coordinates (x, y, x2, y2) to absolute pixel positions on the rendered page image.
2. WHEN a Canvas_Region has a parent canvas, THE Layout_Visualizer SHALL compute the pixel coordinates relative to the parent canvas's resolved pixel bounds.
3. WHEN a Canvas_Region has no explicit parent, THE Layout_Visualizer SHALL treat the full page as the parent (0,0 to page width, page height).
4. THE Layout_Visualizer SHALL process canvas regions in dependency order, resolving parent canvases before their children.
5. IF a Canvas_Region references a parent canvas that does not exist in the merged layout, THEN THE Layout_Visualizer SHALL report an error identifying the orphaned canvas and the missing parent name.

### Requirement 5: Color Assignment

**User Story:** As a layout author, I want each canvas region drawn in a distinct color, so that I can visually distinguish overlapping or adjacent regions.

#### Acceptance Criteria

1. THE Layout_Visualizer SHALL assign a visually distinct color to each Canvas_Region.
2. THE Layout_Visualizer SHALL use a predefined palette of colors that are distinguishable from each other.
3. WHEN the number of canvas regions exceeds the palette size, THE Layout_Visualizer SHALL cycle through the palette.

### Requirement 6: Rectangle Overlay Rendering

**User Story:** As a layout author, I want semi-transparent colored rectangles drawn over the PDF background, so that I can see both the canvas boundaries and the underlying PDF content.

#### Acceptance Criteria

1. THE Layout_Visualizer SHALL draw a semi-transparent filled rectangle for each Canvas_Region at its Resolved_Coordinates.
2. THE Layout_Visualizer SHALL draw a solid-color border around each rectangle to clearly delineate the region boundary.
3. THE Layout_Visualizer SHALL use an opacity level that allows the underlying PDF content to remain visible through the overlay.

### Requirement 7: Label Rendering

**User Story:** As a layout author, I want each rectangle labeled with the canvas name, so that I can identify which region is which without cross-referencing the JSON file.

#### Acceptance Criteria

1. THE Layout_Visualizer SHALL render a text Label containing the canvas region name on each rectangle.
2. THE Layout_Visualizer SHALL position each Label within the bounds of its corresponding rectangle.
3. THE Layout_Visualizer SHALL render Labels with a contrasting background or outline so that the text is readable against both the colored rectangle and the PDF background.

### Requirement 8: PNG Output

**User Story:** As a layout author, I want the final visualization saved as a PNG file, so that I can open it in any image viewer and share it with others.

#### Acceptance Criteria

1. THE Layout_Visualizer SHALL write the composited image (PDF background with rectangle overlays and labels) to a PNG file at the specified output path.
2. WHEN the output file is written successfully, THE Layout_Visualizer SHALL exit with status code 0.
3. IF the output path is not writable, THEN THE Layout_Visualizer SHALL report a descriptive error and exit with a non-zero status code.

### Requirement 9: Error Handling

**User Story:** As a layout author, I want clear error messages when something goes wrong, so that I can fix the issue and try again.

#### Acceptance Criteria

1. IF the Layout_File path does not exist, THEN THE Layout_Visualizer SHALL print an error message identifying the missing file to stderr and exit with a non-zero status code.
2. IF the Chronicle_PDF path does not exist, THEN THE Layout_Visualizer SHALL print an error message identifying the missing file to stderr and exit with a non-zero status code.
3. IF the Layout_File contains invalid JSON, THEN THE Layout_Visualizer SHALL print an error message describing the parse failure to stderr and exit with a non-zero status code.
4. THE Layout_Visualizer SHALL print all error messages to stderr.

### Requirement 10: Watch Mode

**User Story:** As a layout author, I want the visualizer to watch for changes to the layout file and automatically regenerate the PNG, so that I can see my edits reflected immediately without re-running the command.

#### Acceptance Criteria

1. WHEN the `--watch` flag is provided, THE Layout_Visualizer SHALL generate the PNG once and then continue running, monitoring the Layout_File for modifications.
2. WHEN the Layout_File is modified while in Watch_Mode, THE Layout_Visualizer SHALL regenerate the PNG output using the updated layout content.
3. WHEN in Watch_Mode, THE Layout_Visualizer SHALL also monitor all parent Layout_Files in the inheritance chain and regenerate the PNG when any of them change.
4. WHEN in Watch_Mode, THE Layout_Visualizer SHALL print a message to stdout each time it detects a change and regenerates the PNG.
5. WHEN in Watch_Mode, THE Layout_Visualizer SHALL continue running until the user sends an interrupt signal (Ctrl+C / SIGINT).
6. WHEN the user sends an interrupt signal in Watch_Mode, THE Layout_Visualizer SHALL exit cleanly with status code 0.
7. IF a regeneration fails due to invalid JSON in the modified Layout_File, THE Layout_Visualizer SHALL print the error to stderr and continue watching (not exit).
