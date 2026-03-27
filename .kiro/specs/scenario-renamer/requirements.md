# Requirements Document

## Introduction

A Python command-line utility that creates renamed copies of Pathfinder Society (PFS) scenario PDF and map files. The utility reuses the existing scenario info extraction and filename sanitization logic from the chronicle_extractor package to determine each scenario's season, number, and name. Unlike the chronicle extractor (which extracts only the last page), the scenario renamer copies the entire file and names it without the "Chronicle" suffix. Output files are organized into season-based subdirectories under a configurable output directory (e.g., `PFS/Season 1/1-01-TheAbsalomInitiation.pdf`).

In addition to scenario PDFs, the utility processes image files (PDF maps, JPG, and PNG). Image files cannot be parsed for scenario metadata, so the utility first processes all scenario PDFs to build a lookup table mapping (season, scenario) pairs to scenario names, then renames image files by extracting the scenario identifier from the filename and resolving it against the lookup table. The scenario identifier is detected via PZOPFS filename prefix or X-YY season-number pattern. Any descriptive suffix after the identifier (e.g., "Maps", "A-Nighttime Ambush") is preserved in the output filename. Files that cannot be attributed to a scenario (no extractable metadata, or unresolved identifiers) are copied as-is to the output directory with their original filenames, ensuring no input files are lost.

This utility is the third in the PFS Tools collection. It shares the `ScenarioInfo` extraction and `sanitize_name` logic with the chronicle_extractor but operates on the full scenario PDF rather than a single extracted page.

## Glossary

- **Scenario_Renamer**: The Python command-line utility that copies and renames scenario PDFs and scenario images into an organized directory structure.
- **Scenario_PDF**: A Pathfinder Society scenario PDF file in the input directory, containing the full scenario content (e.g., `PZOPFS0101E.pdf`).
- **Scenario_Info**: The parsed metadata for a scenario, consisting of season number, scenario number, and scenario name. Extracted using the existing `extract_scenario_info` function from the chronicle_extractor package.
- **Sanitized_Name**: The scenario name with spaces removed and unsafe filename characters stripped, produced by the existing `sanitize_name` function from the chronicle_extractor package.
- **Output_Directory**: The base directory where renamed scenario PDFs are saved (e.g., `PFS/`).
- **Season_Subdirectory**: A subdirectory under the Output_Directory named `Season X` where X is the season number (e.g., `PFS/Season 1/`).
- **Quests_Subdirectory**: A subdirectory under the Output_Directory named `Quests` for quest scenario PDFs.
- **Bounties_Subdirectory**: A subdirectory under the Output_Directory named `Bounties` for bounty scenario PDFs.
- **Scenario_Image**: A JPG, PNG, or PDF file associated with a scenario that is not a Scenario_PDF. Identified by having a PZOPFS_Pattern or Season_Number_Pattern in its filename stem. Includes map files, handout images, and other scenario-related images. The portion of the stem after the scenario identifier is the Image_Suffix.
- **Image_Suffix**: The trailing portion of a Scenario_Image stem after the scenario identifier and any edition letter/whitespace. Preserved during renaming with spaces removed and unsafe characters stripped. Examples: "Maps" from `PZOPFS0107E Maps.pdf`, "A-Nighttime Ambush" from `PZOPFS0409 A-Nighttime Ambush.jpg`, "Map-1" from `2-03-Map-1.jpg`.
- **PZOPFS_Pattern**: A filename prefix in the format `PZOPFSssnn` where `ss` is the zero-padded season number and `nn` is the zero-padded scenario number (e.g., `PZOPFS0107` = Season 1, Scenario 07). May include a trailing edition letter (e.g., `PZOPFS0107E`).
- **Season_Number_Pattern**: A scenario identifier embedded in a filename in the format `X-YY` where X is the season number and YY is the zero-padded scenario number (e.g., `2-03` = Season 2, Scenario 03). May also appear as `PFS X-YY` with a "PFS" prefix.
- **Scenario_Lookup_Table**: An in-memory mapping from (season, scenario) pairs to Sanitized_Names, built by processing all Scenario_PDFs before processing Scenario_Images.
- **As-Is_Copy**: A file copy operation where the file is copied to the Output_Directory using its original filename, performed when the file cannot be attributed to a specific scenario. Uses `shutil.copy2` to preserve file metadata.

## Requirements

### Requirement 1: CLI Argument Parsing

**User Story:** As a user, I want to specify input and output directories via command-line arguments, so that I can control where scenario PDFs are read from and where renamed copies are saved.

#### Acceptance Criteria

1. THE Scenario_Renamer SHALL accept a required `--input-dir` command-line argument specifying the directory containing Scenario_PDFs.
2. THE Scenario_Renamer SHALL accept a required `--output-dir` command-line argument specifying the base Output_Directory for saving renamed Scenario_PDFs.
3. IF the `--input-dir` path does not exist, THEN THE Scenario_Renamer SHALL exit with a non-zero exit code and print a descriptive error message to stderr.
4. IF the `--output-dir` path does not exist, THEN THE Scenario_Renamer SHALL create the directory including parent directories.

### Requirement 2: File Filtering

**User Story:** As a user, I want the utility to process PDF, JPG, and PNG files and skip unrelated files, so that scenario PDFs and scenario images are processed.

#### Acceptance Criteria

1. THE Scenario_Renamer SHALL process files with a `.pdf` extension (case-insensitive) as either Scenario_PDFs or Scenario_Images.
2. THE Scenario_Renamer SHALL process files with a `.jpg`, `.jpeg`, or `.png` extension (case-insensitive) as Scenario_Images when the filename stem contains a PZOPFS_Pattern or Season_Number_Pattern.
3. THE Scenario_Renamer SHALL skip non-file entries (directories, symlinks) in the input directory.
4. THE Scenario_Renamer SHALL skip files that are not PDF, JPG/JPEG, or PNG.
5. THE Scenario_Renamer SHALL copy as-is any JPG/JPEG/PNG file whose stem does not contain a PZOPFS_Pattern or Season_Number_Pattern.

### Requirement 3: Scenario Info Extraction

**User Story:** As a user, I want the utility to automatically identify the PFS scenario number and name from each PDF, so that renamed files are named correctly without manual input.

#### Acceptance Criteria

1. WHEN a Scenario_PDF is opened, THE Scenario_Renamer SHALL extract Scenario_Info by delegating to the existing `extract_scenario_info` function from the chronicle_extractor package.
2. WHEN the extraction requires reading multiple pages (first page, interior pages, last page), THE Scenario_Renamer SHALL provide the appropriate page texts to the extraction function.
3. IF the extraction function returns no Scenario_Info, THEN THE Scenario_Renamer SHALL copy the file as-is to the Output_Directory with its original filename and log a warning message to stderr.

### Requirement 4: Full PDF Copy

**User Story:** As a user, I want the entire scenario PDF copied to the output location, so that I have a complete renamed copy of the scenario file.

#### Acceptance Criteria

1. WHEN valid Scenario_Info is extracted, THE Scenario_Renamer SHALL copy the entire Scenario_PDF to the output path using `shutil.copy2` from the Python standard library to preserve file metadata.
2. THE Scenario_Renamer SHALL save the copied Scenario_PDF to the appropriate subdirectory under the Output_Directory (Season_Subdirectory, Quests_Subdirectory, or Bounties_Subdirectory).
3. IF the target subdirectory does not exist, THEN THE Scenario_Renamer SHALL create the subdirectory including parent directories before copying.

### Requirement 5: Output Filename Construction

**User Story:** As a user, I want renamed files named with the scenario number and a sanitized scenario name (without a "Chronicle" suffix), so that files are easy to identify and compatible with all operating systems.

#### Acceptance Criteria

1. THE Scenario_Renamer SHALL construct the output filename in the format `{season}-{scenario}-{Sanitized_Name}.pdf` for regular scenarios (e.g., `1-01-TheAbsalomInitiation.pdf`).
2. THE Scenario_Renamer SHALL construct the output filename in the format `Q{scenario}-{Sanitized_Name}.pdf` for quests (season=0) (e.g., `Q14-TheSwordlordsChallenge.pdf`).
3. THE Scenario_Renamer SHALL construct the output filename in the format `B{scenario}-{Sanitized_Name}.pdf` for bounties (season=-1) (e.g., `B1-TheWhitefangWyrm.pdf`).
4. THE Scenario_Renamer SHALL use the existing `sanitize_name` function from the chronicle_extractor package to produce the Sanitized_Name.

### Requirement 6: Output Directory Structure

**User Story:** As a user, I want renamed scenario PDFs organized into subdirectories by season, quests, or bounties, so that the output mirrors a logical organizational structure.

#### Acceptance Criteria

1. WHEN the Scenario_Info has a positive season number, THE Scenario_Renamer SHALL place the output file in `{Output_Directory}/Season {season}/`.
2. WHEN the Scenario_Info has season=0 (quest), THE Scenario_Renamer SHALL place the output file in `{Output_Directory}/Quests/`.
3. WHEN the Scenario_Info has season=-1 (bounty), THE Scenario_Renamer SHALL place the output file in `{Output_Directory}/Bounties/`.

### Requirement 7: Recursive Directory Traversal

**User Story:** As a user, I want the utility to recursively process all files under the input directory tree, so that I can point it at a top-level directory (e.g., `Scenarios/`) and process all seasons, quests, and bounties in one invocation.

#### Acceptance Criteria

1. THE Scenario_Renamer SHALL recursively traverse all subdirectories under the input directory.
2. THE Scenario_Renamer SHALL process files found at any depth within the input directory tree.
3. THE Scenario_Renamer SHALL determine the output subdirectory for each file based on the extracted Scenario_Info (season number, quest, or bounty), NOT based on the input subdirectory structure.

### Requirement 8: Processing Feedback

**User Story:** As a user, I want to see what the utility is doing as it processes files, so that I can verify it is working correctly and troubleshoot issues.

#### Acceptance Criteria

1. WHEN a Scenario_PDF is successfully copied and renamed, THE Scenario_Renamer SHALL print the output file path to stdout.
2. WHEN a Scenario_Image is successfully copied and renamed, THE Scenario_Renamer SHALL print the output file path to stdout.
3. WHEN a file is skipped due to filtering rules, THE Scenario_Renamer SHALL print a skip message to stderr indicating the filename and reason.
4. WHEN a file is copied as-is because no Scenario_Info is found, THE Scenario_Renamer SHALL print a warning to stderr indicating the filename and the as-is copy destination.
5. WHEN a Scenario_Image is copied as-is because the scenario identifier is not in the Scenario_Lookup_Table, THE Scenario_Renamer SHALL print a warning to stderr indicating the filename, the unresolved identifier, and the as-is copy destination.
6. IF an error occurs while reading or copying a file, THEN THE Scenario_Renamer SHALL print an error message to stderr and continue processing remaining files.

### Requirement 9: Reuse of Shared Logic

**User Story:** As a developer, I want the scenario renamer to import and reuse the existing extraction and sanitization logic from the chronicle_extractor package, so that naming logic is maintained in a single place (DRY principle).

#### Acceptance Criteria

1. THE Scenario_Renamer SHALL import `extract_scenario_info` and `ScenarioInfo` from the chronicle_extractor.parser module.
2. THE Scenario_Renamer SHALL import `sanitize_name` from the chronicle_extractor.filename module.
3. THE Scenario_Renamer SHALL import `is_scenario_pdf` and `is_map_pdf` from the chronicle_extractor.filters module.
4. THE Scenario_Renamer SHALL NOT duplicate the scenario info extraction, filename sanitization, or file filtering logic.

### Requirement 10: Utility-Specific README

**User Story:** As a developer, I want a README.md in the scenario_renamer utility's subdirectory, so that I can understand how to use and contribute to this utility independently.

#### Acceptance Criteria

1. THE Scenario_Renamer project SHALL include a README.md in the scenario_renamer utility's subdirectory.
2. THE README SHALL describe the purpose of the Scenario_Renamer utility.
3. THE README SHALL document the command-line arguments accepted by the Scenario_Renamer (`--input-dir` and `--output-dir`).
4. THE README SHALL include at least one usage example showing a complete command invocation.
5. THE README SHALL note the dependency on the chronicle_extractor package for shared logic.

### Requirement 11: Top-Level README Update

**User Story:** As a developer, I want the top-level README updated to include the new utility, so that the project index stays current.

#### Acceptance Criteria

1. WHEN the Scenario_Renamer is added to the project, THE Top_Level_README SHALL be updated to include the Scenario_Renamer in the utilities table with a relative link to the utility's README.

### Requirement 12: Scenario Lookup Table Construction

**User Story:** As a user, I want the utility to build a lookup table of scenario names from processed scenario PDFs, so that map files can be renamed using the correct scenario name.

#### Acceptance Criteria

1. THE Scenario_Renamer SHALL process all Scenario_PDFs before processing any Scenario_Images.
2. WHEN a Scenario_PDF is successfully processed, THE Scenario_Renamer SHALL store the (season, scenario) pair and corresponding Sanitized_Name in the Scenario_Lookup_Table.
3. THE Scenario_Lookup_Table SHALL map each (season, scenario) tuple to the Sanitized_Name extracted from the corresponding Scenario_PDF.
4. IF multiple Scenario_PDFs produce the same (season, scenario) key, THEN THE Scenario_Renamer SHALL use the Sanitized_Name from the last processed Scenario_PDF for that key.

### Requirement 13: Scenario Image Detection and Classification

**User Story:** As a user, I want the utility to identify scenario-related image files by their filename patterns, so that images are processed separately from scenario PDFs.

#### Acceptance Criteria

1. THE Scenario_Renamer SHALL classify a non-Scenario_PDF file as a Scenario_Image when its stem contains a PZOPFS_Pattern or Season_Number_Pattern and its extension is `.pdf`, `.jpg`, `.jpeg`, or `.png` (case-insensitive).
2. FOR PDF files, THE Scenario_Renamer SHALL classify the file as a Scenario_Image (rather than a Scenario_PDF) when the file stem ends with "Map" or "Maps" (case-insensitive), optionally followed by a separator and numeric suffix.
3. THE Scenario_Renamer SHALL detect the PZOPFS_Pattern in a Scenario_Image stem when the stem starts with `PZOPFS` followed by at least four digits (e.g., `PZOPFS0107E Maps.pdf`, `PZOPFS0409 A-Nighttime Ambush.jpg`).
4. WHEN a PZOPFS_Pattern is detected, THE Scenario_Renamer SHALL extract the season number from the first two digits after "PZOPFS" and the scenario number from the next two digits (e.g., `PZOPFS0107` yields season=1, scenario=07).
5. THE Scenario_Renamer SHALL detect the Season_Number_Pattern in a Scenario_Image stem when the stem contains a pattern matching `X-YY` where X is one or more digits and YY is two or more digits (e.g., `2-03-Map-1.jpg`, `PFS 2-21 Map 1.jpg`).
6. WHEN a Season_Number_Pattern is detected, THE Scenario_Renamer SHALL extract the season number (X) and scenario number (YY) from the pattern.
7. THE Scenario_Renamer SHALL extract the Image_Suffix as the portion of the stem after the scenario identifier (PZOPFS code + optional edition letter, or X-YY pattern), stripped of leading whitespace and separators.
8. IF a Scenario_Image stem matches neither the PZOPFS_Pattern nor the Season_Number_Pattern, THEN THE Scenario_Renamer SHALL copy the file as-is to the Output_Directory with its original filename and log a warning to stderr.

### Requirement 14: Scenario Image Renaming

**User Story:** As a user, I want scenario images renamed to include the full scenario name, so that images are easy to identify alongside their corresponding scenario PDFs.

#### Acceptance Criteria

1. WHEN a Scenario_Image has a matching entry in the Scenario_Lookup_Table, THE Scenario_Renamer SHALL construct the output filename in the format `{season}-{scenario}-{Sanitized_Name}{Sanitized_Image_Suffix}.{extension}` (e.g., `1-07-FloodedKingsCourtMaps.pdf`, `4-09-PerilousExperimentA-NighttimeAmbush.jpg`).
2. THE Scenario_Renamer SHALL sanitize the Image_Suffix by removing spaces and unsafe filename characters (using the same rules as Sanitized_Name), while preserving hyphens as word separators.
3. THE Scenario_Renamer SHALL preserve the original file extension (`.pdf`, `.jpg`, or `.png`) in the output filename.
4. THE Scenario_Renamer SHALL place the renamed Scenario_Image in the same Season_Subdirectory as the corresponding scenario (based on the season number extracted from the filename stem).
5. IF the extracted (season, scenario) pair from a Scenario_Image has no matching entry in the Scenario_Lookup_Table, THEN THE Scenario_Renamer SHALL copy the file as-is to the Output_Directory with its original filename and log a warning to stderr indicating the filename and the unresolved scenario identifier.

### Requirement 15: Two-Pass Processing Order

**User Story:** As a user, I want scenario PDFs processed before image files, so that the scenario name lookup table is fully populated before image renaming begins.

#### Acceptance Criteria

1. THE Scenario_Renamer SHALL execute processing in two passes: first pass for Scenario_PDFs, second pass for Scenario_Images.
2. WHEN scanning the input directory tree recursively, THE Scenario_Renamer SHALL separate files into Scenario_PDFs and Scenario_Images before beginning processing.
3. THE Scenario_Renamer SHALL complete all Scenario_PDF processing (including Scenario_Lookup_Table population) before beginning any Scenario_Image processing.

### Requirement 16: Fallback Copy for Unattributable Files

**User Story:** As a user, I want files that cannot be attributed to a scenario copied to the output directory with their original filenames, so that no input files are lost during processing.

#### Acceptance Criteria

1. WHEN a Scenario_PDF yields no Scenario_Info, THE Scenario_Renamer SHALL copy the file to the Output_Directory using its original filename via `shutil.copy2`.
2. WHEN a Scenario_Image stem matches neither the PZOPFS_Pattern nor the Season_Number_Pattern, THE Scenario_Renamer SHALL copy the file to the Output_Directory using its original filename via `shutil.copy2`.
3. WHEN a Scenario_Image has an extracted scenario identifier with no matching entry in the Scenario_Lookup_Table, THE Scenario_Renamer SHALL copy the file to the Output_Directory using its original filename via `shutil.copy2`.
4. WHEN a JPG/JPEG/PNG file does not contain a recognizable scenario identifier pattern, THE Scenario_Renamer SHALL copy the file to the Output_Directory using its original filename via `shutil.copy2`.
5. THE Scenario_Renamer SHALL place the As-Is_Copy in the Output_Directory preserving the file's relative path from the input directory (e.g., a file at `Scenarios/Season 1/unknown.pdf` with `--input-dir Scenarios` is copied to `PFS/Season 1/unknown.pdf`).
