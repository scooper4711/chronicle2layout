# Requirements Document

## Introduction

A Python CLI utility that analyzes a directory of single-page chronicle PDF files (produced by the chronicle-extractor utility) and generates a `seasonX.json` layout file defining the overarching layout for that season. The utility detects eight canvas regions on the chronicle sheet — Player Info, Adventure Summary, Rewards, Items, Notes, Boons, Reputation, and Session Info — using a combination of PDF text extraction and image-based region detection. The scope of this utility is canvas boundary detection only; field-level detection within canvases is out of scope. The output follows the layout format documented in `LAYOUT_FORMAT.md`, producing percentage-based coordinates relative to the page.

This utility is the second in the PFS Tools collection. It produces the season-level layout definition only; scenario-specific layout files (`pfs.sX-YY.json`) are out of scope.

## Glossary

- **Season_Layout_Generator**: The Python CLI utility that analyzes chronicle PDFs and produces a season layout JSON file.
- **Chronicle_PDF**: A single-page PDF file containing a chronicle sheet, located in a season subdirectory under the Chronicles directory (e.g., `Chronicles/Season 5/5-01-...Chronicle.pdf`). Produced by the Chronicle_Extractor utility.
- **Season_Directory**: A directory containing Chronicle_PDFs for a single season (e.g., `Chronicles/Season 5/`).
- **Season_Layout_File**: The output JSON file defining canvas regions, parameters, presets, and content for a season (e.g., `Season5.json`), placed in a season subdirectory under the Layouts directory.
- **Layout_Output_Directory**: The directory where the Season_Layout_File is written (e.g., `Layouts/pfs2/Season 5/`).
- **Canvas_Region**: A named rectangular area on the chronicle sheet, defined by percentage-based coordinates (0–100) relative to a parent canvas. Standard regions are: page, main, player_info, summary, rewards, items, notes, boons, reputation, session_info.
- **Player_Info_Canvas**: The canvas region at the top of the chronicle page containing fields for character name, organized play number, and character number.
- **Summary_Canvas**: The canvas region below the Player_Info_Canvas, identified by a black horizontal bar with white "Adventure Summary" text at its top edge.
- **Notes_Canvas**: The canvas region containing rows of horizontal lines for free-text player notes.
- **Boons_Canvas**: The canvas region containing boon text entries that players can earn from the scenario.
- **Reputation_Canvas**: The canvas region containing reputation tracking, identified by a label starting with "Reputation" (e.g., "Reputation", "Reputation Gained", "Reputation/Infamy"). This canvas may not be present on all chronicle sheets.
- **Page_Canvas**: The full-page canvas region (always 0–100 on both axes), serving as the root parent for all other canvases.
- **Main_Canvas**: The primary content area within the page margins, serving as the parent for most other canvas regions.
- **Region_Detection**: The process of identifying canvas region boundaries on a chronicle sheet using a combination of text extraction and image analysis techniques.
- **Image_Analysis**: The process of converting a PDF page to a raster image and analyzing pixel data to detect visual features such as black bars, thick borders, and grey backgrounds.
- **Text_Extraction**: The process of reading text content and positional metadata from a PDF page using PyMuPDF.
- **Consensus_Coordinates**: The final percentage-based coordinates for a canvas region, derived by analyzing multiple Chronicle_PDFs from the same season and selecting representative values.
- **Season_Number**: The integer identifying which season a set of chronicles belongs to, extracted from the Season_Directory name (e.g., `5` from `Season 5`).
- **Collection_Name**: A generalized identifier for the group of chronicles being processed. For seasons this is the Season_Number (e.g., `5`); for Quests and Bounties it is the directory name itself (e.g., `Quests`, `Bounties`).
- **Quests_Directory**: A directory named `Quests` containing Chronicle_PDFs for Pathfinder Society quest scenarios.
- **Bounties_Directory**: A directory named `Bounties` containing Chronicle_PDFs for Pathfinder Society bounty scenarios.
- **Layout_Variant**: A distinct chronicle template within a single collection where canvas regions differ significantly in size or position from other chronicles in the same collection. When detected, each variant produces a separate layout file.
- **Variant_Suffix**: A lowercase letter (a, b, c, ...) appended to the layout ID and filename to distinguish multiple Layout_Variants within the same collection (e.g., `pfs2.season4a`, `pfs2.season4b`).
- **Layout_Divergence_Threshold**: The maximum percentage-point difference in any single canvas coordinate (x, y, x2, y2) between two Chronicle_PDFs before they are considered to belong to different Layout_Variants.
- **Debug_Directory**: An optional directory specified via the `--debug-dir` CLI argument. When provided, the Season_Layout_Generator saves clipped canvas region images to subdirectories within this directory for visual confirmation of detection accuracy.
- **Debug_Image**: A raster image file clipped from a Chronicle_PDF page corresponding to a single detected Canvas_Region. Saved as a PNG file within the Debug_Directory.

## Requirements

### Requirement 1: CLI Interface

**User Story:** As a user, I want to specify the input chronicle directory and output layout directory via command-line arguments, so that I can control where chronicles are read from and where the season layout file is saved.

#### Acceptance Criteria

1. THE Season_Layout_Generator SHALL accept a required `--input-dir` command-line argument specifying the Season_Directory containing Chronicle_PDFs.
2. THE Season_Layout_Generator SHALL accept a required `--output-dir` command-line argument specifying the base Layout_Output_Directory for saving the Season_Layout_File.
3. IF the `--input-dir` path does not exist, THEN THE Season_Layout_Generator SHALL exit with a non-zero exit code and print a descriptive error message to stderr.
4. IF the `--input-dir` directory contains no Chronicle_PDFs, THEN THE Season_Layout_Generator SHALL exit with a non-zero exit code and print a descriptive error message to stderr.
5. IF the `--output-dir` path does not exist, THEN THE Season_Layout_Generator SHALL create the directory including parent directories.

### Requirement 2: Collection Name Extraction

**User Story:** As a user, I want the utility to automatically determine the season number or collection name from the input directory name, so that the output file is named correctly without manual input.

#### Acceptance Criteria

1. WHEN the input directory name matches the pattern `Season X` (where X is a positive integer), THE Season_Layout_Generator SHALL extract X as the Season_Number and use it as the Collection_Name.
2. WHEN the input directory name is `Quests` (case-insensitive), THE Season_Layout_Generator SHALL use `Quests` as the Collection_Name.
3. WHEN the input directory name is `Bounties` (case-insensitive), THE Season_Layout_Generator SHALL use `Bounties` as the Collection_Name.
4. IF the input directory name does not match `Season X`, `Quests`, or `Bounties`, THEN THE Season_Layout_Generator SHALL exit with a non-zero exit code and print a descriptive error message to stderr.

### Requirement 3: Chronicle PDF Discovery

**User Story:** As a user, I want the utility to find all chronicle PDFs in the input directory, so that it can analyze a representative sample of the season's chronicle sheets.

#### Acceptance Criteria

1. THE Season_Layout_Generator SHALL scan the Season_Directory for files with a `.pdf` extension (case-insensitive).
2. THE Season_Layout_Generator SHALL skip non-file entries (directories, symlinks) in the Season_Directory.
3. THE Season_Layout_Generator SHALL process files in the immediate Season_Directory only, without recursing into subdirectories.

### Requirement 4: Page Region Detection — Player Info Canvas

**User Story:** As a user, I want the utility to detect the Player Info region at the top of the chronicle sheet, so that the season layout accurately defines where character name and society ID fields are located.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Player_Info_Canvas at the top of the page by identifying text fields for character name, organized play number, and character number.
2. THE Season_Layout_Generator SHALL determine the Player_Info_Canvas boundaries as percentage-based coordinates (x, y, x2, y2) relative to the Main_Canvas.

### Requirement 5: Page Region Detection — Adventure Summary Canvas

**User Story:** As a user, I want the utility to detect the Adventure Summary region, so that the season layout defines the area where adventure summary checkboxes and text are located.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Summary_Canvas by locating a black horizontal bar containing white text that includes the words "Adventure Summary" (case-insensitive).
2. THE Season_Layout_Generator SHALL determine the Summary_Canvas boundaries as percentage-based coordinates relative to the Main_Canvas, with the top edge at the black bar and the bottom edge at the lower boundary of the summary content area.

### Requirement 6: Page Region Detection — Rewards Canvas

**User Story:** As a user, I want the utility to detect the Rewards region on the right side of the page, so that the season layout defines where XP and GP fields are located.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Rewards_Canvas by identifying a region on the right side of the page surrounded by thick black lines and containing text related to XP and GP fields.
2. THE Season_Layout_Generator SHALL determine the Rewards_Canvas boundaries as percentage-based coordinates relative to the Main_Canvas.

### Requirement 7: Page Region Detection — Items Canvas

**User Story:** As a user, I want the utility to detect the Items region, so that the season layout defines where the available items list is located.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Items_Canvas by identifying a region bounded by thick black lines on the top and bottom edges, with a black bar at the top containing white text that includes the word "Items" (case-insensitive).
2. THE Season_Layout_Generator SHALL determine the Items_Canvas boundaries as percentage-based coordinates relative to the Main_Canvas.

### Requirement 8: Page Region Detection — Session Info Canvas

**User Story:** As a user, I want the utility to detect the Session Info region at the bottom of the page, so that the season layout defines where event and GM fields are located.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Session_Info_Canvas at the bottom of the page by identifying a region with a light grey background containing text fields for event, event code, date, and GM organized play number.
2. THE Season_Layout_Generator SHALL determine the Session_Info_Canvas boundaries as percentage-based coordinates relative to the Main_Canvas.

### Requirement 9: Page Region Detection — Notes Canvas

**User Story:** As a user, I want the utility to detect the Notes region, so that the season layout defines where the free-text player notes area is located.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Notes_Canvas by identifying a region containing rows of horizontal lines intended for free-text notes.
2. THE Season_Layout_Generator SHALL determine the Notes_Canvas boundaries as percentage-based coordinates relative to the Main_Canvas.

### Requirement 10: Page Region Detection — Boons Canvas

**User Story:** As a user, I want the utility to detect the Boons region, so that the season layout defines where boon entries are located.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Boons_Canvas by identifying a region containing boon text content.
2. THE Season_Layout_Generator SHALL determine the Boons_Canvas boundaries as percentage-based coordinates relative to the Main_Canvas.

### Requirement 11: Page Region Detection — Reputation Canvas

**User Story:** As a user, I want the utility to detect the Reputation region, so that the season layout defines where reputation tracking is located.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Reputation_Canvas by identifying a region containing text that starts with "Reputation" (case-insensitive), matching labels such as "Reputation", "Reputation Gained", or "Reputation/Infamy".
2. THE Season_Layout_Generator SHALL determine the Reputation_Canvas boundaries as percentage-based coordinates relative to the Main_Canvas.
3. IF the Reputation_Canvas is not detected in a Chronicle_PDF, THE Season_Layout_Generator SHALL treat this as a valid result and continue processing without error.

### Requirement 12: Main Canvas Detection

**User Story:** As a user, I want the utility to detect the main content area within the page margins, so that all other canvas regions are positioned relative to a consistent reference frame.

#### Acceptance Criteria

1. WHEN analyzing a Chronicle_PDF, THE Season_Layout_Generator SHALL detect the Main_Canvas by identifying the content boundary within the page margins.
2. THE Season_Layout_Generator SHALL determine the Main_Canvas boundaries as percentage-based coordinates relative to the Page_Canvas.

### Requirement 13: Multi-PDF Consensus

**User Story:** As a user, I want the utility to analyze multiple chronicle PDFs from the same season and produce consensus coordinates, so that the layout is robust against minor variations between individual scenario PDFs.

#### Acceptance Criteria

1. THE Season_Layout_Generator SHALL analyze at least two Chronicle_PDFs from the Season_Directory to determine Consensus_Coordinates for each Canvas_Region within each Layout_Variant group.
2. WHEN multiple Chronicle_PDFs in the same Layout_Variant group produce different coordinates for the same Canvas_Region, THE Season_Layout_Generator SHALL compute Consensus_Coordinates by selecting the median value for each coordinate (x, y, x2, y2).
3. IF a Canvas_Region is detected in fewer than half of the analyzed Chronicle_PDFs within a Layout_Variant group, THEN THE Season_Layout_Generator SHALL log a warning to stderr indicating the region and the number of PDFs where detection succeeded.
4. THE Season_Layout_Generator SHALL log to stdout the number of Chronicle_PDFs analyzed, the number of Layout_Variants detected, and the number of successful detections per Canvas_Region per variant.

### Requirement 14: Layout Variant Detection

**User Story:** As a user, I want the utility to detect when chronicle PDFs within the same collection use different template layouts, so that each distinct layout produces its own season layout file (as Season 4 does with its five variants).

#### Acceptance Criteria

1. WHEN processing Chronicle_PDFs in sorted filename order, THE Season_Layout_Generator SHALL compare each PDF's detected canvas coordinates against the current Layout_Variant group's Consensus_Coordinates.
2. IF any canvas coordinate differs by more than the Layout_Divergence_Threshold from the current group's consensus, THEN THE Season_Layout_Generator SHALL start a new Layout_Variant group beginning with that Chronicle_PDF.
3. THE Season_Layout_Generator SHALL assign Variant_Suffixes only to the second and subsequent Layout_Variants, in alphabetical order (a, b, c, ...). The first Layout_Variant SHALL use the base name with no suffix.
4. FOR each Layout_Variant after the first, THE Season_Layout_Generator SHALL include in the variant's `description` field the scenario number of the first Chronicle_PDF that belongs to that variant (e.g., `Season 4 Base Layout (starting 4-09)`).
5. THE first Layout_Variant's `description` field SHALL use the standard base layout description without a scenario number reference.

### Requirement 15: Season Layout JSON Output

**User Story:** As a user, I want the utility to produce well-structured season layout JSON files following the documented format, so that they integrate with the existing layout inheritance hierarchy.

#### Acceptance Criteria

1. WHEN the Collection_Name is a Season_Number, THE Season_Layout_Generator SHALL produce the first Layout_Variant's Season_Layout_File with the `id` field set to `pfs2.seasonX` where X is the Season_Number.
2. FOR each subsequent Layout_Variant (second, third, etc.), THE Season_Layout_Generator SHALL produce a Season_Layout_File with the `id` field set to `pfs2.seasonX{suffix}` where suffix is the Variant_Suffix (e.g., `pfs2.season4a`, `pfs2.season4b`).
3. WHEN the Collection_Name is `Quests` or `Bounties`, THE Season_Layout_Generator SHALL produce the first Layout_Variant's layout file with the `id` field set to `pfs2.quests` or `pfs2.bounties` respectively.
4. FOR each subsequent Layout_Variant when the Collection_Name is `Quests` or `Bounties`, THE Season_Layout_Generator SHALL append the Variant_Suffix to the `id` (e.g., `pfs2.questsa`, `pfs2.questsb`).
5. THE Season_Layout_Generator SHALL set the `parent` field to `pfs2`.
6. THE first Layout_Variant SHALL use the standard description: `Season X Base Layout` (for seasons) or `{Collection_Name} Base Layout` (for Quests/Bounties).
7. EACH subsequent Layout_Variant SHALL include the scenario number of the first Chronicle_PDF in that variant group in the `description` field (e.g., `Season 4 Base Layout (starting 4-09)`).
8. THE Season_Layout_Generator SHALL include a `canvas` object containing the Page_Canvas, Main_Canvas, and all detected Canvas_Regions with their Consensus_Coordinates as percentage-based values.
9. WHEN the Collection_Name is a Season_Number, THE Season_Layout_Generator SHALL write the first variant to `{output-dir}/Season {X}/Season{X}.json` and subsequent variants to `{output-dir}/Season {X}/Season{X}{suffix}.json` (e.g., `Season4a.json`).
10. WHEN the Collection_Name is `Quests` or `Bounties`, THE Season_Layout_Generator SHALL write the first variant to `{output-dir}/{Collection_Name}/{Collection_Name}.json` and subsequent variants to `{output-dir}/{Collection_Name}/{Collection_Name}{suffix}.json`.
11. IF the output subdirectory does not exist, THEN THE Season_Layout_Generator SHALL create the subdirectory before writing the file.
12. THE Season_Layout_Generator SHALL format the output JSON with 4-space indentation for readability.

### Requirement 16: Image-Based Region Detection

**User Story:** As a user, I want the utility to use image analysis to detect visual features like black bars, thick borders, and grey backgrounds, so that region detection works reliably even when text-based detection alone is insufficient.

#### Acceptance Criteria

1. WHEN performing Region_Detection, THE Season_Layout_Generator SHALL convert the Chronicle_PDF page to a raster image for Image_Analysis.
2. THE Season_Layout_Generator SHALL use Image_Analysis to detect black horizontal bars (for the Summary_Canvas top edge).
3. THE Season_Layout_Generator SHALL use Image_Analysis to detect thick black border lines (for the Rewards_Canvas and Items_Canvas boundaries).
4. THE Season_Layout_Generator SHALL use Image_Analysis to detect light grey background regions (for the Session_Info_Canvas).
5. THE Season_Layout_Generator SHALL combine results from Text_Extraction and Image_Analysis to determine the final boundaries for each Canvas_Region.

### Requirement 17: Text-Based Region Detection

**User Story:** As a user, I want the utility to use text extraction to identify content within regions, so that canvas boundaries are informed by the actual text fields present on the chronicle sheet.

#### Acceptance Criteria

1. WHEN performing Region_Detection, THE Season_Layout_Generator SHALL extract text content and positional metadata from the Chronicle_PDF using PyMuPDF.
2. THE Season_Layout_Generator SHALL use extracted text positions to identify the Player_Info_Canvas by locating text characteristic of the player info area (e.g., "Character Name", "Organized Play #").
3. THE Season_Layout_Generator SHALL use extracted text positions to confirm the Summary_Canvas by locating "Adventure Summary" text.
4. THE Season_Layout_Generator SHALL use extracted text positions to identify the Rewards_Canvas by locating reward-related text (e.g., "XP", "GP").
5. THE Season_Layout_Generator SHALL use extracted text positions to identify the Session_Info_Canvas by locating session-related text (e.g., "Event", "Date", "GM").
6. THE Season_Layout_Generator SHALL use extracted text positions to identify the Notes_Canvas by locating notes-related text or horizontal rule patterns.
7. THE Season_Layout_Generator SHALL use extracted text positions to identify the Boons_Canvas by locating boon-related text content.
8. THE Season_Layout_Generator SHALL use extracted text positions to identify the Reputation_Canvas by locating text starting with "Reputation" (e.g., "Reputation", "Reputation Gained", "Reputation/Infamy").

### Requirement 18: Processing Feedback

**User Story:** As a user, I want to see progress and diagnostic information as the utility processes chronicle PDFs, so that I can verify the detection is working correctly and troubleshoot issues.

#### Acceptance Criteria

1. WHEN a Chronicle_PDF is successfully analyzed, THE Season_Layout_Generator SHALL print the filename and detected regions to stdout.
2. WHEN a Canvas_Region fails to be detected in a Chronicle_PDF, THE Season_Layout_Generator SHALL print a warning to stderr indicating the filename and the undetected region.
3. WHEN the Season_Layout_File is successfully written, THE Season_Layout_Generator SHALL print the output file path to stdout.
4. IF an error occurs while reading a Chronicle_PDF, THEN THE Season_Layout_Generator SHALL print an error message to stderr and continue processing remaining files.

### Requirement 19: Consistent Detection Methodology

**User Story:** As a user, I want the same detection approach applied to all seasons, so that the utility produces consistent results regardless of which season is being analyzed.

#### Acceptance Criteria

1. THE Season_Layout_Generator SHALL use the same Region_Detection algorithms for all seasons.
2. THE Season_Layout_Generator SHALL use the same Image_Analysis thresholds and parameters for all seasons.
3. THE Season_Layout_Generator SHALL use the same Text_Extraction patterns for all seasons.

### Requirement 20: Utility-Specific README

**User Story:** As a developer, I want a README.md in the season-layout-generator utility's subdirectory, so that I can understand how to use and contribute to this utility independently.

#### Acceptance Criteria

1. THE Season_Layout_Generator project SHALL include a README.md in the Season_Layout_Generator utility's subdirectory.
2. THE README SHALL describe the purpose of the Season_Layout_Generator utility.
3. THE README SHALL document the command-line arguments accepted by the Season_Layout_Generator (`--input-dir`, `--output-dir`, and `--debug-dir`).
4. THE README SHALL include at least one usage example showing a complete command invocation.
5. THE README SHALL describe the detection methodology at a high level (text extraction combined with image analysis).

### Requirement 21: Top-Level README Update

**User Story:** As a developer, I want the top-level README updated to include the new utility, so that the project index stays current.

#### Acceptance Criteria

1. WHEN the Season_Layout_Generator is added to the project, THE Top_Level_README SHALL be updated to include the Season_Layout_Generator in the utilities table with a relative link to the utility's README.

### Requirement 22: Python Dependency Updates

**User Story:** As a developer, I want any new dependencies added to requirements.txt, so that the virtual environment can be reproduced reliably.

#### Acceptance Criteria

1. IF the Season_Layout_Generator requires Python packages not already listed in the Requirements_File, THEN THE Requirements_File SHALL be updated to include the new packages.
2. THE Season_Layout_Generator SHALL use PyMuPDF (fitz) for PDF text extraction and page-to-image conversion.
3. THE Season_Layout_Generator SHALL use Pillow or numpy (both already available in the virtual environment) for Image_Analysis operations.

### Requirement 23: Debug Canvas Clipping Output

**User Story:** As a user, I want to pass a debug flag with an associated directory so that detected canvas regions are clipped from each PDF and saved as images, allowing me to visually confirm that canvas detection is working correctly.

#### Acceptance Criteria

1. THE Season_Layout_Generator SHALL accept an optional `--debug-dir` command-line argument specifying the Debug_Directory for saving Debug_Images.
2. WHEN `--debug-dir` is provided and a Canvas_Region is detected on a Chronicle_PDF, THE Season_Layout_Generator SHALL clip the corresponding region from the PDF page raster image and save it as a PNG Debug_Image.
3. THE Season_Layout_Generator SHALL save each Debug_Image to a subdirectory path of the form `{debug-dir}/{collection_name}/{layout_variant_name}/{pdf_filename}/{canvas_name}.png`, where `collection_name` is the Collection_Name (e.g., `Season 5`, `Quests`, `Bounties`), `layout_variant_name` is the layout variant identifier (e.g., `Season5`, `Season4a`), `pdf_filename` is the Chronicle_PDF filename without extension, and `canvas_name` is the Canvas_Region name (e.g., `player_info`, `summary`, `rewards`).
4. THE Season_Layout_Generator SHALL produce one Debug_Image per detected Canvas_Region per Chronicle_PDF, so that the user can inspect what was detected on each individual PDF rather than only the consensus result.
5. IF the Debug_Directory or any required subdirectory does not exist, THEN THE Season_Layout_Generator SHALL create the directory including parent directories.
6. IF `--debug-dir` is not provided, THEN THE Season_Layout_Generator SHALL skip all debug clipping and image saving without error.
7. IF an error occurs while saving a Debug_Image, THEN THE Season_Layout_Generator SHALL print a warning to stderr and continue processing without interrupting the main pipeline.
