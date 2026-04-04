# Requirements Document

## Introduction

A Python tool that takes two inputs — a Blueprint JSON file and a chronicle PDF — and produces a layout.json file conforming to LAYOUT_FORMAT.md. The tool opens the chronicle PDF, strips text and embedded images to isolate structural vector art, renders the cleaned page to a 150 DPI raster image, detects structural lines and grey boxes by pixel analysis, resolves the Blueprint against the detected elements, converts absolute page percentages to parent-relative percentages, and writes the final layout.json output.

A Blueprint is a declarative authoring format where canvas edges reference detected line arrays by category and index (e.g., `h_bar[0]`, `v_thin[2]`) or previously defined canvas edges (e.g., `summary.bottom`). Blueprints support inheritance: a child Blueprint can reference a parent Blueprint to pull in already-defined canvases, avoiding repetition of common definitions like `page` and `main`. The layout.json is the pre-computed runtime format used by the Foundry VTT module, with parent-relative percentage coordinates.

## Glossary

- **Layout_Generator**: The Python tool that performs the end-to-end pipeline from PDF analysis to layout.json output.
- **Chronicle_PDF**: A single-page PDF file containing a Pathfinder Society chronicle sheet.
- **Blueprint**: A JSON file that declaratively describes canvas regions by referencing detected structural lines and previously defined canvases, rather than hard-coded percentages. Has a unique `id` property and contains an ordered array of canvas entries, each with a name, optional parent canvas, and four edge values (left, right, top, bottom) that are numeric literals, line references, or canvas references. May reference a parent Blueprint by id to inherit canvas definitions.
- **Parent_Blueprint**: A Blueprint referenced by another Blueprint's `parent` property (by id). All canvases from the Parent_Blueprint are resolved first and are available for Canvas_References in the child Blueprint.
- **Cleaned_Image**: A raster image produced by stripping all text blocks and embedded images from a Chronicle_PDF page and rendering at 150 DPI.
- **Detection_Result**: A structured dictionary containing six keyed arrays (`h_thin`, `h_bar`, `h_rule`, `v_thin`, `v_bar`, `grey_box`) of detected structural elements with percentage coordinates.
- **Line_Reference**: A string of the form `category[index]` (e.g., `h_bar[0]`, `v_thin[2]`) that resolves to a detected line's percentage position on the primary axis.
- **Canvas_Reference**: A string of the form `canvas_name.edge` (e.g., `summary.bottom`, `main.left`) that resolves to an already-resolved canvas edge value.
- **Edge_Value**: A canvas edge specification that is one of: a numeric literal (float or int), a Line_Reference, or a Canvas_Reference.
- **Absolute_Percentage**: A coordinate expressed as a percentage (0–100) of the full page width or height.
- **Parent_Relative_Percentage**: A coordinate expressed as a percentage (0–100) of the parent canvas width or height, as required by LAYOUT_FORMAT.md.
- **Grayscale_Value**: An integer 0–255 representing pixel brightness, where 0 is black and 255 is white.
- **Black_Pixel**: A pixel with a Grayscale_Value below 50.
- **Thin_Line**: A horizontal or vertical line group with thickness of 5 pixels or fewer at 150 DPI.
- **Thick_Bar**: A horizontal or vertical line group with thickness greater than 5 pixels at 150 DPI.
- **Grey_Line**: A horizontal line detected from medium-grey pixels (Grayscale_Value between 50 and 200 inclusive) that does not overlap with any detected black horizontal line or bar.
- **Grey_Box**: A filled rectangular region composed of neutral grey pixels (R, G, B channels each in the 220–240 range with channel differences less than 8).
- **Line_Group**: A set of consecutive rows or columns containing qualifying pixel runs, grouped when gaps between consecutive qualifying rows or columns do not exceed a grouping tolerance.
- **Layout_JSON**: The output file conforming to LAYOUT_FORMAT.md, containing a `canvas` section with Parent_Relative_Percentage coordinates.

## Requirements

### Requirement 1: PDF Page Preparation

**User Story:** As a layout author, I want the tool to strip text and images from a chronicle PDF page before analysis, so that only structural vector art (lines, boxes, fills) remains for detection.

#### Acceptance Criteria

1. WHEN a Chronicle_PDF path is provided, THE Layout_Generator SHALL open the last page of the PDF using PyMuPDF.
2. THE Layout_Generator SHALL redact all text blocks on the page by adding redaction annotations over each text block bounding box and applying the redactions.
3. THE Layout_Generator SHALL redact all embedded images on the page by adding redaction annotations over each image bounding box and applying the redactions.
4. WHEN redactions are applied, THE Layout_Generator SHALL render the cleaned page to a Cleaned_Image at 150 DPI.
5. THE Layout_Generator SHALL convert the Cleaned_Image to both a grayscale array and an RGB array for subsequent detection steps.

### Requirement 2: Horizontal Black Line Detection

**User Story:** As a layout author, I want the tool to detect all horizontal black lines on the chronicle page, so that `h_thin` and `h_bar` arrays are populated for canvas edge resolution.

#### Acceptance Criteria

1. THE Layout_Generator SHALL scan each row of the Cleaned_Image grayscale array for runs of consecutive Black_Pixels that span more than 5% of the page width.
2. THE Layout_Generator SHALL group qualifying rows into Line_Groups where consecutive qualifying rows are separated by no more than 5 pixels.
3. FOR each horizontal Line_Group, THE Layout_Generator SHALL compute the bounding box as Absolute_Percentages: y position from the topmost row, x from the leftmost pixel, x2 from the rightmost pixel.
4. THE Layout_Generator SHALL classify each horizontal Line_Group as a Thin_Line (thickness ≤ 5 pixels) or a Thick_Bar (thickness > 5 pixels).
5. THE Layout_Generator SHALL store Thin_Lines in the `h_thin` array and Thick_Bars in the `h_bar` array of the Detection_Result, each sorted by y position ascending.
6. FOR each detected horizontal line, THE Layout_Generator SHALL include the thickness in pixels in the output entry.

### Requirement 3: Vertical Black Line Detection

**User Story:** As a layout author, I want the tool to detect all vertical black lines on the chronicle page, so that `v_thin` and `v_bar` arrays are populated for canvas edge resolution.

#### Acceptance Criteria

1. THE Layout_Generator SHALL scan each column of the Cleaned_Image grayscale array for runs of consecutive Black_Pixels that span more than 3% of the page height.
2. THE Layout_Generator SHALL group qualifying columns into Line_Groups where consecutive qualifying columns are separated by no more than 5 pixels.
3. FOR each vertical Line_Group, THE Layout_Generator SHALL compute the bounding box as Absolute_Percentages: x from the leftmost column, y from the topmost pixel, y2 from the bottommost pixel.
4. THE Layout_Generator SHALL classify each vertical Line_Group as a Thin_Line (thickness ≤ 5 pixels) or a Thick_Bar (thickness > 5 pixels).
5. THE Layout_Generator SHALL store Thin_Lines in the `v_thin` array and Thick_Bars in the `v_bar` array of the Detection_Result, each sorted by x position ascending.
6. FOR each detected vertical line, THE Layout_Generator SHALL include the thickness in pixels in the output entry.

### Requirement 4: Grey Horizontal Rule Detection

**User Story:** As a layout author, I want the tool to detect grey horizontal rule lines, so that `h_rule` entries are available for field placement definitions in the canvas definition.

#### Acceptance Criteria

1. THE Layout_Generator SHALL scan each row of the Cleaned_Image grayscale array for runs of consecutive pixels with Grayscale_Value between 50 and 200 (inclusive) that span more than 5% of the page width.
2. THE Layout_Generator SHALL group qualifying rows into Line_Groups where consecutive qualifying rows are separated by no more than 3 pixels.
3. FOR each grey horizontal Line_Group, THE Layout_Generator SHALL compute the bounding box as Absolute_Percentages: y position, x position, and x2 position.
4. THE Layout_Generator SHALL deduplicate grey horizontal lines against detected black horizontal lines: IF a grey line's y position is within 0.5 percentage points of any `h_thin` or `h_bar` entry's y position, THEN THE Layout_Generator SHALL discard the grey line.
5. THE Layout_Generator SHALL store the remaining grey lines in the `h_rule` array of the Detection_Result, sorted by y position ascending.

### Requirement 5: Grey Box Detection

**User Story:** As a layout author, I want the tool to detect grey filled rectangles, so that `grey_box` entries are available for canvas definitions referencing session info bars and input field backgrounds.

#### Acceptance Criteria

1. THE Layout_Generator SHALL identify structural grey pixels in the RGB array where all three channels are each in the range 220–240 and the absolute difference between any two channels is less than 8.
2. THE Layout_Generator SHALL divide the Cleaned_Image into a grid of 10×10 pixel blocks and classify each block as grey when more than 50% of its pixels are structural grey.
3. THE Layout_Generator SHALL perform a flood-fill on the grid to identify connected components of grey blocks.
4. THE Layout_Generator SHALL discard connected components with fewer than 3 grid blocks.
5. FOR each remaining connected component, THE Layout_Generator SHALL refine the bounding box by scanning the structural grey pixel mask within the component's grid bounds to find the tightest pixel-level bounding box.
6. THE Layout_Generator SHALL discard components whose refined bounding box area is less than 500 square pixels.
7. THE Layout_Generator SHALL store the remaining grey boxes in the `grey_box` array of the Detection_Result as Absolute_Percentages (x, y, x2, y2), sorted by y ascending then x ascending.

### Requirement 6: Detection Result Structure

**User Story:** As a layout author, I want the detection output to have a consistent structure with six keyed arrays, so that the canvas resolver can look up elements by category and zero-based index.

#### Acceptance Criteria

1. THE Layout_Generator SHALL produce a Detection_Result dictionary with exactly six keys: `h_thin`, `h_bar`, `h_rule`, `v_thin`, `v_bar`, and `grey_box`.
2. EACH entry in `h_thin`, `h_bar`, and `h_rule` SHALL contain the keys `y`, `x`, `x2`, and `thickness_px`, where `y` is the top-edge Absolute_Percentage, `x` is the left-edge Absolute_Percentage, `x2` is the right-edge Absolute_Percentage, and `thickness_px` is the thickness in pixels.
3. EACH entry in `v_thin` and `v_bar` SHALL contain the keys `x`, `y`, `y2`, and `thickness_px`, where `x` is the left-edge Absolute_Percentage, `y` is the top-edge Absolute_Percentage, `y2` is the bottom-edge Absolute_Percentage, and `thickness_px` is the thickness in pixels.
4. EACH entry in `grey_box` SHALL contain the keys `x`, `y`, `x2`, and `y2` as Absolute_Percentages.
5. ALL Absolute_Percentage values in the Detection_Result SHALL be rounded to one decimal place.
6. EACH array in the Detection_Result SHALL use zero-based indexing and be sorted according to its category's primary axis: `h_thin`, `h_bar`, and `h_rule` by `y` ascending; `v_thin` and `v_bar` by `x` ascending; `grey_box` by `y` ascending then `x` ascending.

### Requirement 7: Blueprint Parsing

**User Story:** As a layout author, I want to provide a Blueprint JSON file that describes canvases using line references and canvas references, so that I can author layouts declaratively without hard-coding pixel coordinates.

#### Acceptance Criteria

1. THE Layout_Generator SHALL accept a Blueprint JSON file containing a `canvases` array of canvas entry objects.
2. EACH canvas entry SHALL have a `name` (string) and four edge properties: `left`, `right`, `top`, `bottom`, each being an Edge_Value.
3. EACH canvas entry MAY have a `parent` property (string) naming the parent canvas for coordinate conversion.
4. THE Layout_Generator SHALL validate that all canvas names within a Blueprint (including inherited canvases from a Parent_Blueprint) are unique.
5. IF a Blueprint contains a canvas name that duplicates a canvas name already defined in the same Blueprint or inherited from a Parent_Blueprint, THEN THE Layout_Generator SHALL raise a descriptive error identifying the duplicate name.
6. IF the Blueprint file does not exist or is not valid JSON, THEN THE Layout_Generator SHALL raise a descriptive error.

### Requirement 8: Blueprint Inheritance

**User Story:** As a layout author, I want a Blueprint to reference a parent Blueprint by id so that common canvas definitions (like `page` and `main`) are defined once and inherited by child Blueprints, mirroring how layout files use `id` and `parent` properties.

#### Acceptance Criteria

1. EACH Blueprint SHALL have an `id` property (string) that uniquely identifies it (e.g., `"pfs2.blueprint"`, `"pfs2.season5.blueprint"`).
2. A Blueprint MAY contain a `parent` property (string) at the top level whose value is the `id` of a Parent_Blueprint.
3. THE Layout_Generator SHALL accept a directory (or set of files) containing all Blueprint files, build an id-to-file map, and resolve parent references by id lookup — matching the same pattern used by layout files in LAYOUT_FORMAT.md.
4. WHEN a Blueprint has a `parent` property, THE Layout_Generator SHALL load and resolve the Parent_Blueprint first, recursively resolving any further parent references in the chain.
5. THE Layout_Generator SHALL resolve all canvases from the Parent_Blueprint before resolving canvases from the child Blueprint.
6. Canvases inherited from a Parent_Blueprint SHALL be available for Canvas_References in the child Blueprint's canvas entries.
7. IF a child Blueprint defines a canvas with the same name as a canvas inherited from a Parent_Blueprint, THEN THE Layout_Generator SHALL raise a descriptive error identifying the duplicate canvas name and the Blueprint ids involved.
8. IF a `parent` id does not match any known Blueprint id, THEN THE Layout_Generator SHALL raise a descriptive error identifying the unknown parent id.
9. THE Layout_Generator SHALL detect circular parent references and raise a descriptive error if a cycle is found.

### Requirement 9: Edge Value Resolution

**User Story:** As a layout author, I want edge values to resolve numeric literals, line references, and canvas references into absolute page percentages, so that canvases are positioned according to the detected structural elements.

#### Acceptance Criteria

1. WHEN an Edge_Value is a numeric literal (int or float), THE Layout_Generator SHALL use the value directly as an Absolute_Percentage.
2. WHEN an Edge_Value is a Line_Reference matching the pattern `category[index]`, THE Layout_Generator SHALL resolve the value to the detected line's primary-axis Absolute_Percentage: `y` for horizontal categories (`h_thin`, `h_bar`, `h_rule`) and `x` for vertical categories (`v_thin`, `v_bar`).
3. WHEN an Edge_Value is a Canvas_Reference matching the pattern `canvas_name.edge`, THE Layout_Generator SHALL resolve the value to the named canvas's resolved Absolute_Percentage for the specified edge (`left`, `right`, `top`, or `bottom`).
4. IF a Line_Reference refers to a category not present in the Detection_Result, THEN THE Layout_Generator SHALL raise a descriptive error identifying the unknown category.
5. IF a Line_Reference index is out of bounds for the detected array, THEN THE Layout_Generator SHALL raise a descriptive error identifying the category and index.
6. IF a Canvas_Reference names a canvas that has not yet been resolved (forward reference), THEN THE Layout_Generator SHALL raise a descriptive error explaining that the referenced canvas must appear earlier in the array.

### Requirement 10: Canvas Resolution Order

**User Story:** As a layout author, I want canvases to be resolved in array order with only backward references allowed, so that the resolution is deterministic and cycle-free.

#### Acceptance Criteria

1. THE Layout_Generator SHALL resolve canvases in the order they appear in the `canvases` array of the Blueprint, after all inherited canvases from any Parent_Blueprint have been resolved.
2. WHEN resolving canvas N, THE Layout_Generator SHALL permit Canvas_References only to canvases at positions 0 through N-1 in the array.
3. IF canvas N contains a Canvas_Reference to a canvas at position N or later, THEN THE Layout_Generator SHALL raise a descriptive error indicating a forward reference.
4. THE Layout_Generator SHALL store each resolved canvas's four edge values as Absolute_Percentages before proceeding to the next canvas in the array.

### Requirement 11: Parent-Relative Coordinate Conversion

**User Story:** As a layout author, I want the resolved absolute percentages to be converted to parent-relative percentages, so that the output conforms to LAYOUT_FORMAT.md's canvas coordinate system.

#### Acceptance Criteria

1. FOR each resolved canvas that has a parent, THE Layout_Generator SHALL convert the canvas's Absolute_Percentages to Parent_Relative_Percentages using the parent's resolved absolute edges.
2. THE Layout_Generator SHALL compute the parent-relative x as `(canvas_left - parent_left) / parent_width * 100`, where parent_width is `parent_right - parent_left`.
3. THE Layout_Generator SHALL compute the parent-relative y as `(canvas_top - parent_top) / parent_height * 100`, where parent_height is `parent_bottom - parent_top`.
4. THE Layout_Generator SHALL compute the parent-relative x2 as `(canvas_right - parent_left) / parent_width * 100`.
5. THE Layout_Generator SHALL compute the parent-relative y2 as `(canvas_bottom - parent_top) / parent_height * 100`.
6. FOR each resolved canvas without a parent, THE Layout_Generator SHALL use the Absolute_Percentages directly as the output coordinates.
7. ALL Parent_Relative_Percentage values in the output SHALL be rounded to one decimal place.
8. IF a canvas references a parent name that does not match any resolved canvas, THEN THE Layout_Generator SHALL raise a descriptive error identifying the unknown parent.

### Requirement 12: Layout JSON Output

**User Story:** As a layout author, I want the tool to write a layout.json file with only the canvases defined in the target Blueprint (not inherited ones), so that the output mirrors the Blueprint's scope and parent Blueprints produce their own separate layout files.

#### Acceptance Criteria

1. THE Layout_Generator SHALL produce a Layout_JSON file containing an `id` property set to the target Blueprint's `id`.
2. IF the target Blueprint has a `parent` property, THE Layout_Generator SHALL include a `parent` property in the Layout_JSON set to the same parent id as the Blueprint's `parent` — linking the output layout to the parent layout in the layout inheritance chain.
3. THE Layout_Generator SHALL include a `canvas` object containing ONLY the canvases defined directly in the target Blueprint, NOT canvases inherited from a Parent_Blueprint.
4. EACH canvas entry in the `canvas` object SHALL contain `x`, `y`, `x2`, `y2` as Parent_Relative_Percentages.
5. FOR each canvas with a parent canvas, THE Layout_Generator SHALL include a `parent` property in the canvas entry with the parent canvas name.
6. THE Layout_Generator SHALL format the Layout_JSON with 2-space indentation.
7. THE Layout_Generator SHALL write the Layout_JSON to the output file path specified via the CLI.
8. THE Layout_Generator SHALL produce output that is valid JSON parseable by Python's `json.loads`.

### Requirement 13: CLI Entry Point

**User Story:** As a layout author, I want to run the tool from the command line with a Blueprint file, a chronicle PDF, and an output path, so that I can generate layout.json files during development.

#### Acceptance Criteria

1. THE Layout_Generator SHALL provide a CLI entry point invocable as `python -m blueprint2layout <blueprint.json> <chronicle.pdf> <output.json>`.
2. THE Layout_Generator SHALL accept a `--blueprints-dir` option specifying the directory to scan for Blueprint files when resolving parent references. IF omitted, THE Layout_Generator SHALL default to the directory containing the target Blueprint file.
3. WHEN invoked with valid arguments, THE Layout_Generator SHALL execute the full pipeline and write the Layout_JSON to the specified output path.
4. IF any required argument (Blueprint, PDF, or output path) is missing, THEN THE Layout_Generator SHALL print a usage message to stderr and exit with a non-zero exit code.
5. IF an error occurs during any pipeline stage, THEN THE Layout_Generator SHALL print the error message to stderr and exit with a non-zero exit code.

### Requirement 14: Round-Trip Consistency

**User Story:** As a developer, I want the Layout_JSON output to be JSON-serializable and round-trip stable, so that layout files can be saved, loaded, and compared reliably.

#### Acceptance Criteria

1. THE Layout_JSON produced by the Layout_Generator SHALL be directly serializable to JSON using Python's `json.dumps` without custom encoders.
2. FOR ALL valid Layout_JSON outputs, serializing to JSON and deserializing back SHALL produce a dictionary equal to the original output (round-trip property).
3. THE Layout_JSON SHALL contain only Python built-in types: `dict`, `list`, `float`, `int`, and `str`.

### Requirement 15: Programmatic API

**User Story:** As a developer, I want a clean public function that accepts a canvas definition path and a PDF path and returns the resolved layout dictionary, so that the tool is easy to integrate into larger pipelines.

#### Acceptance Criteria

1. THE Layout_Generator SHALL expose a public function `generate_layout` that accepts a Blueprint file path, a Chronicle_PDF file path, and returns the Layout_JSON content as a Python dictionary.
2. IF the Blueprint file path does not exist, THEN THE Layout_Generator SHALL raise a `FileNotFoundError` with a descriptive message including the path.
3. IF the Chronicle_PDF file path does not exist, THEN THE Layout_Generator SHALL raise a `FileNotFoundError` with a descriptive message including the path.
4. IF the Chronicle_PDF is not a valid PDF, THEN THE Layout_Generator SHALL raise a `ValueError` with a descriptive message.
5. THE `generate_layout` function SHALL handle the complete pipeline internally: open PDF, strip text and images, render to image, detect structural elements, parse Blueprint (with inheritance), resolve edges, convert to parent-relative coordinates, and return the assembled layout dictionary.

### Requirement 16: Remove season_layout_generator Package

**User Story:** As a developer, I want the old season_layout_generator package removed, so that the codebase has a single approach to layout generation via Blueprints rather than two competing implementations.

**Note:** This requirement SHALL be implemented as a separate commit after the main feature is complete.

#### Acceptance Criteria

1. THE Layout_Generator feature SHALL remove the `season_layout_generator/` package directory and all its modules (`image_detection.py`, `text_detection.py`, `region_merge.py`, `consensus.py`, `layout_builder.py`, `models.py`, `collection.py`, `pipeline.py`, `__init__.py`, `__main__.py`).
2. THE Layout_Generator feature SHALL remove the `tests/season_layout_generator/` test directory and all its test modules.
3. THE Layout_Generator feature SHALL remove the `clip_canvases.py` script that depended on the season_layout_generator package.
4. THE Layout_Generator feature SHALL remove the `.kiro/specs/season-layout-generator/` spec directory.
5. IF any other files in the project import from `season_layout_generator`, THEN those imports SHALL be removed or updated.
