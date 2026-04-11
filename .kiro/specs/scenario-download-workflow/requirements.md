# Requirements Document

## Introduction

The Scenario Download Workflow is a Python CLI tool (`python -m scenario_download_workflow`) that automates the end-to-end processing of newly downloaded Pathfinder Society (PFS) and Starfinder Society (SFS) scenario PDFs. When a user downloads a new scenario PDF to `~/Downloads`, this tool discovers it, prompts the user for confirmation, then orchestrates the five existing PFS Tools utilities in sequence: scenario_renamer (rename and file the PDF), chronicle_extractor (extract the chronicle sheet), blueprint2layout (convert blueprint to layout), layout_generator (generate leaf layout JSON), and layout_visualizer (render a data-mode preview).

The tool detects whether a scenario is Pathfinder or Starfinder by inspecting the PDF's first page text for "Pathfinder Society" or "Starfinder Society" headers. It uses this classification to route files to the correct directory trees: `Scenarios/PFS/` vs `Scenarios/SFS/` for scenario PDFs, and `pfs2/` vs `sfs2/` subdirectories under `modules/pfs-chronicle-generator/assets/chronicles/` and `modules/pfs-chronicle-generator/assets/layouts/` for chronicles and layouts.

Because the existing tools operate on directories (input-dir/output-dir pattern), the workflow creates temporary staging directories to process individual PDFs through each tool, then verifies the expected output files exist before proceeding to the next step.

## Glossary

- **Download_Workflow**: The Python CLI tool that orchestrates the end-to-end processing of newly downloaded scenario PDFs.
- **Downloads_Directory**: The user's `~/Downloads` directory, scanned for recently modified PDF files.
- **Downloaded_PDF**: A PDF file in the Downloads_Directory whose filesystem modification time falls within the Recency_Window.
- **Recency_Window**: The maximum age of a PDF file (measured from its filesystem modification time to the current time) for it to be considered a recent download. Defaults to 1 hour. Configurable via the `--recent` CLI argument as a human-readable duration string (e.g., `1h`, `30m`, `2d`).
- **Game_System**: The tabletop RPG system a scenario belongs to, either Pathfinder (`pfs`) or Starfinder (`sfs`). Detected from the PDF's first page text.
- **System_Prefix**: The directory prefix derived from the Game_System: `pfs2` for Pathfinder scenarios, `sfs2` for Starfinder scenarios.
- **Scenarios_Directory**: The top-level directory where renamed scenario PDFs are filed, organized as `Scenarios/PFS/` or `Scenarios/SFS/` with season subdirectories.
- **Chronicles_Directory**: The directory where extracted chronicle sheets are stored: `modules/pfs-chronicle-generator/assets/chronicles/{System_Prefix}/`.
- **Layouts_Directory**: The directory where layout JSON files are stored: `modules/pfs-chronicle-generator/assets/layouts/{System_Prefix}/`.
- **Blueprints_Directory**: The directory containing Blueprint JSON files: `Blueprints/{System_Prefix}/`.
- **Scenario_Info**: The parsed metadata for a scenario (season number, scenario number, name), extracted using the existing `extract_scenario_info` function from the chronicle_extractor package.
- **Season_Subdirectory**: A subdirectory named `Season {N}` (under Scenarios_Directory) or `season{N}` (under Chronicles_Directory, Layouts_Directory, and Blueprints_Directory) where N is the season number.
- **Staging_Directory**: A temporary directory created by the Download_Workflow to hold a single PDF for processing by tools that expect directory-based input/output arguments.
- **Processing_Pipeline**: The ordered sequence of tool invocations for a single scenario PDF: scenario_renamer → chronicle_extractor → blueprint2layout → layout_generator → layout_visualizer.
- **Project_Root**: The working directory from which the Download_Workflow is invoked, expected to be the PFS Tools project root containing the `Scenarios/`, `Blueprints/`, and `modules/` directories.
- **Sanitized_Name**: The scenario name with spaces removed and unsafe filename characters stripped, produced by the existing `sanitize_name` function from the chronicle_extractor package.

## Requirements

### Requirement 1: CLI Entry Point

**User Story:** As a user, I want to run the download workflow from the command line, so that I can process newly downloaded scenario PDFs with a single command.

#### Acceptance Criteria

1. THE Download_Workflow SHALL be invocable as `python -m scenario_download_workflow`.
2. THE Download_Workflow SHALL accept an optional `--downloads-dir` argument specifying the Downloads_Directory, defaulting to `~/Downloads`.
3. THE Download_Workflow SHALL accept an optional `--project-dir` argument specifying the Project_Root, defaulting to the current working directory.
4. THE Download_Workflow SHALL accept an optional `--recent` argument specifying the Recency_Window as a human-readable duration string, defaulting to `1h` (1 hour). Supported suffixes SHALL be `m` (minutes), `h` (hours), and `d` (days). Examples: `30m`, `2h`, `1d`.
5. THE Download_Workflow SHALL accept an optional `--non-interactive` flag that processes all discovered PDFs without prompting for confirmation.
6. WHEN invoked with valid arguments, THE Download_Workflow SHALL exit with code 0 when at least one PDF is processed successfully.
7. WHEN no Downloaded_PDFs are found, THE Download_Workflow SHALL print an informational message to stdout and exit with code 0.
8. IF the `--recent` value cannot be parsed as a valid duration, THEN THE Download_Workflow SHALL print a descriptive error to stderr and exit with a non-zero exit code.

### Requirement 2: PDF Discovery

**User Story:** As a user, I want the tool to find PDF files I downloaded recently, so that I only see recent scenario downloads and not old files.

#### Acceptance Criteria

1. THE Download_Workflow SHALL scan the Downloads_Directory for files with a `.pdf` extension (case-insensitive).
2. THE Download_Workflow SHALL filter discovered PDFs to only those whose filesystem modification time is within the Recency_Window of the current time.
3. THE Download_Workflow SHALL skip subdirectories within the Downloads_Directory (no recursive scanning).
4. THE Download_Workflow SHALL sort discovered PDFs alphabetically by filename.
5. WHEN no PDF files within the Recency_Window are found, THE Download_Workflow SHALL print a message to stdout listing the Downloads_Directory path and the Recency_Window duration.

### Requirement 3: Interactive Confirmation

**User Story:** As a user, I want to be prompted for each discovered PDF, so that I can choose which scenarios to process and skip unrelated PDFs.

#### Acceptance Criteria

1. WHEN running in interactive mode (default), THE Download_Workflow SHALL display each Downloaded_PDF's filename and prompt the user with a yes/no question.
2. WHEN the user responds with "y" or "yes" (case-insensitive), THE Download_Workflow SHALL process that PDF through the Processing_Pipeline.
3. WHEN the user responds with "n" or "no" (case-insensitive), THE Download_Workflow SHALL skip that PDF and proceed to the next one.
4. WHEN the user responds with "q" or "quit" (case-insensitive), THE Download_Workflow SHALL stop processing and skip all remaining PDFs.
5. WHEN the `--non-interactive` flag is provided, THE Download_Workflow SHALL process all discovered PDFs without prompting.

### Requirement 4: Game System Detection

**User Story:** As a user, I want the tool to automatically detect whether a PDF is a Pathfinder or Starfinder scenario, so that files are routed to the correct directory trees without manual input.

#### Acceptance Criteria

1. WHEN processing a Downloaded_PDF, THE Download_Workflow SHALL open the PDF and read the text content of the first page.
2. WHEN the first page text contains "Pathfinder Society" (case-insensitive), THE Download_Workflow SHALL classify the Game_System as `pfs`.
3. WHEN the first page text contains "Starfinder Society" (case-insensitive), THE Download_Workflow SHALL classify the Game_System as `sfs`.
4. IF the first page text contains neither "Pathfinder Society" nor "Starfinder Society", THEN THE Download_Workflow SHALL print a warning to stderr identifying the filename and skip that PDF.
5. THE Download_Workflow SHALL derive the System_Prefix as `pfs2` for Pathfinder scenarios and `sfs2` for Starfinder scenarios.

### Requirement 5: Scenario Info Extraction

**User Story:** As a user, I want the tool to extract the season number, scenario number, and name from the PDF, so that files are placed in the correct season subdirectories with correct filenames.

#### Acceptance Criteria

1. WHEN processing a Downloaded_PDF, THE Download_Workflow SHALL extract Scenario_Info by delegating to the existing `extract_scenario_info` function from the chronicle_extractor package.
2. THE Download_Workflow SHALL provide the first page text, interior page texts (pages 3-5 when available), and last page text to the extraction function.
3. IF the extraction function returns no Scenario_Info, THEN THE Download_Workflow SHALL print a warning to stderr identifying the filename and skip that PDF.
4. THE Download_Workflow SHALL use the extracted season number to determine the Season_Subdirectory for all downstream tool invocations.

### Requirement 6: Scenario Renaming (Step 1)

**User Story:** As a user, I want the downloaded PDF renamed and filed into the Scenarios directory, so that my scenario collection stays organized.

#### Acceptance Criteria

1. THE Download_Workflow SHALL invoke the scenario_renamer tool to rename and copy the Downloaded_PDF.
2. THE Download_Workflow SHALL set the scenario_renamer's output directory to `{Project_Root}/Scenarios/PFS` for Pathfinder scenarios and `{Project_Root}/Scenarios/SFS` for Starfinder scenarios.
3. THE Download_Workflow SHALL create a Staging_Directory containing only the single Downloaded_PDF as input to the scenario_renamer.
4. IF the Scenarios_Directory or its Season_Subdirectory does not exist, THEN THE Download_Workflow SHALL create the directory (including parent directories).
5. WHEN the scenario_renamer completes, THE Download_Workflow SHALL verify that the expected output file exists in the Scenarios_Directory before proceeding.
6. IF the scenario_renamer fails or the expected output file is not found, THEN THE Download_Workflow SHALL print an error to stderr identifying the filename and the step that failed, and skip the remaining pipeline steps for that PDF.

### Requirement 7: Chronicle Extraction (Step 2)

**User Story:** As a user, I want the chronicle sheet extracted from the scenario PDF and placed in the correct chronicles directory, so that the chronicle generator module can use it.

#### Acceptance Criteria

1. THE Download_Workflow SHALL invoke the chronicle_extractor tool to extract the chronicle page from the renamed scenario PDF.
2. THE Download_Workflow SHALL set the chronicle_extractor's input directory to a Staging_Directory containing the renamed scenario PDF from Step 1.
3. THE Download_Workflow SHALL set the chronicle_extractor's output directory to `{Project_Root}/{Chronicles_Directory}/season{N}` where N is the season number, or `bounties` for bounties, or `quests` for quests.
4. WHEN the chronicle_extractor completes, THE Download_Workflow SHALL verify that the expected chronicle PDF exists in the output directory before proceeding.
5. IF the chronicle_extractor fails or the expected output file is not found, THEN THE Download_Workflow SHALL print an error to stderr and skip the remaining pipeline steps for that PDF.

### Requirement 8: Blueprint to Layout Conversion (Step 3)

**User Story:** As a user, I want the season-level base blueprint converted to a layout JSON and to see which blueprint my new scenario resolves to, so that the chronicle generator has the structural layout data it needs.

#### Acceptance Criteria

1. THE Download_Workflow SHALL invoke the blueprint2layout tool using the season-level base blueprint id pattern (e.g., `pfs2.season{N}-layout-*` or `sfs2.season{N}-layout-*`), not a scenario-specific blueprint id.
2. THE Download_Workflow SHALL set the blueprint2layout's `--blueprints-dir` to `{Project_Root}/Blueprints`.
3. THE Download_Workflow SHALL set the blueprint2layout's `--output-dir` to `{Project_Root}/{Layouts_Directory}`.
4. WHEN the blueprint2layout completes successfully, THE Download_Workflow SHALL print an informational message to stdout identifying which blueprint the new scenario resolves to (e.g., "Scenario 7-06 resolves to blueprint pfs2.season7-layout-s7-00").
5. IF no matching season-level base blueprint is found, THEN THE Download_Workflow SHALL print a warning to stderr indicating that no blueprint exists for the scenario's system and season, and skip this step without failing the pipeline.
6. WHEN the blueprint2layout completes successfully, THE Download_Workflow SHALL print the output layout file path to stdout.

### Requirement 9: Layout Generation (Step 4)

**User Story:** As a user, I want a leaf layout JSON generated from the chronicle PDF, so that the scenario's item lines and checkboxes are captured in the layout.

#### Acceptance Criteria

1. THE Download_Workflow SHALL invoke the layout_generator tool for the extracted chronicle PDF.
2. THE Download_Workflow SHALL pass the chronicle PDF path as the positional `pdf_path` argument.
3. THE Download_Workflow SHALL pass `--metadata-file {Project_Root}/chronicle_properties.toml` to the layout_generator.
4. THE Download_Workflow SHALL pass `--layouts-dir {Project_Root}/{Layouts_Directory}` to the layout_generator when the layouts directory differs from the metadata file's `layouts_dir` property.
5. WHEN the layout_generator completes successfully, THE Download_Workflow SHALL print the output layout file path to stdout.
6. IF the layout_generator fails, THEN THE Download_Workflow SHALL print an error to stderr and skip the remaining pipeline steps for that PDF.

### Requirement 10: Layout Visualization (Step 5)

**User Story:** As a user, I want a data-mode visualization generated for the new layout, so that I can immediately preview how the chronicle sheet looks with example data.

#### Acceptance Criteria

1. THE Download_Workflow SHALL invoke the layout_visualizer tool for the new scenario's layout.
2. THE Download_Workflow SHALL set the layout_visualizer's `--mode` to `data`.
3. THE Download_Workflow SHALL set the layout_visualizer's `--layout-root` to `{Project_Root}/{Layouts_Directory}` (the root layouts directory, not the system-specific subdirectory).
4. THE Download_Workflow SHALL construct the `--layout-id` to match the scenario's layout id (e.g., `pfs2.s{season}-{scenario}`).
5. THE Download_Workflow SHALL set the layout_visualizer's `--output-dir` to a visualization output directory (e.g., `{Project_Root}/debug_clips/layout_visualizer`).
6. WHEN the layout_visualizer completes successfully, THE Download_Workflow SHALL print the output PNG file path to stdout.
7. IF the layout_visualizer fails, THEN THE Download_Workflow SHALL print an error to stderr (this is the last step, so no further steps are skipped).

### Requirement 11: Staging Directory Management

**User Story:** As a developer, I want temporary staging directories created and cleaned up automatically, so that the existing tools can operate on their expected directory-based input/output pattern without leaving temporary files behind.

#### Acceptance Criteria

1. THE Download_Workflow SHALL create Staging_Directories using Python's `tempfile` module.
2. THE Download_Workflow SHALL copy (not move) the Downloaded_PDF into the Staging_Directory before invoking each tool that requires directory-based input.
3. THE Download_Workflow SHALL clean up all Staging_Directories after the Processing_Pipeline completes for each PDF, regardless of success or failure.
4. IF a Staging_Directory cannot be created, THEN THE Download_Workflow SHALL print an error to stderr and skip that PDF.

### Requirement 12: Processing Feedback

**User Story:** As a user, I want clear progress messages as each step runs, so that I can follow along and troubleshoot failures.

#### Acceptance Criteria

1. WHEN beginning processing of a Downloaded_PDF, THE Download_Workflow SHALL print the filename and detected Game_System to stdout.
2. WHEN beginning each step of the Processing_Pipeline, THE Download_Workflow SHALL print a step label (e.g., "Step 1/5: Renaming scenario...") to stdout.
3. WHEN a step completes successfully, THE Download_Workflow SHALL print a success message including the output file path to stdout.
4. WHEN a step fails, THE Download_Workflow SHALL print an error message to stderr identifying the step name, the filename, and the error details.
5. WHEN all PDFs have been processed, THE Download_Workflow SHALL print a summary indicating the number of PDFs processed successfully and the number skipped or failed.

### Requirement 13: Directory Structure Routing

**User Story:** As a user, I want Pathfinder scenarios routed to PFS/pfs2 directories and Starfinder scenarios routed to SFS/sfs2 directories, so that the project's existing directory conventions are maintained.

#### Acceptance Criteria

1. WHEN the Game_System is `pfs`, THE Download_Workflow SHALL route the renamed scenario PDF to `{Project_Root}/Scenarios/PFS/Season {N}/`.
2. WHEN the Game_System is `sfs`, THE Download_Workflow SHALL route the renamed scenario PDF to `{Project_Root}/Scenarios/SFS/Season {N}/`.
3. WHEN the Game_System is `pfs`, THE Download_Workflow SHALL route the extracted chronicle to `{Project_Root}/modules/pfs-chronicle-generator/assets/chronicles/pfs2/season{N}/`.
4. WHEN the Game_System is `sfs`, THE Download_Workflow SHALL route the extracted chronicle to `{Project_Root}/modules/pfs-chronicle-generator/assets/chronicles/sfs2/season{N}/`.
5. WHEN the Scenario_Info indicates a quest (season=0), THE Download_Workflow SHALL route files to the `Quests/` or `quests/` subdirectories instead of a season subdirectory.
6. WHEN the Scenario_Info indicates a bounty (season=-1), THE Download_Workflow SHALL route files to the `Bounties/` or `bounties/` subdirectories instead of a season subdirectory.

### Requirement 14: Error Handling

**User Story:** As a user, I want the tool to handle errors gracefully and continue processing remaining PDFs, so that one bad file does not block the entire batch.

#### Acceptance Criteria

1. IF a Downloaded_PDF cannot be opened by PyMuPDF, THEN THE Download_Workflow SHALL print a descriptive error to stderr identifying the file and skip that PDF.
2. IF a tool invocation raises an exception, THEN THE Download_Workflow SHALL catch the exception, print a descriptive error to stderr, clean up Staging_Directories, and continue processing remaining PDFs.
3. IF a tool invocation returns a non-zero exit code, THEN THE Download_Workflow SHALL treat the step as failed and print the tool's stderr output.
4. THE Download_Workflow SHALL print all error and warning messages to stderr.
5. THE Download_Workflow SHALL exit with code 0 when at least one PDF is processed successfully, and exit with code 1 when no PDFs are processed successfully (excluding PDFs skipped by user choice).

### Requirement 15: Reuse of Shared Logic

**User Story:** As a developer, I want the download workflow to import and reuse existing extraction and tool invocation logic, so that naming and routing logic is maintained in a single place.

#### Acceptance Criteria

1. THE Download_Workflow SHALL import `extract_scenario_info` and `ScenarioInfo` from the chronicle_extractor.parser module for scenario metadata extraction.
2. THE Download_Workflow SHALL import `sanitize_name` from the chronicle_extractor.filename module for filename construction.
3. THE Download_Workflow SHALL invoke downstream tools by calling their `main` functions directly (as Python function calls) rather than spawning subprocesses, to keep the workflow within a single Python process.
4. THE Download_Workflow SHALL NOT duplicate the scenario info extraction, filename sanitization, or file filtering logic already present in the existing tools.

### Requirement 16: Tool Invocation Strategy

**User Story:** As a developer, I want each downstream tool invoked with the correct arguments for single-file processing, so that the workflow correctly orchestrates tools designed for batch directory processing.

#### Acceptance Criteria

1. WHEN invoking the scenario_renamer, THE Download_Workflow SHALL pass `--input-dir` pointing to a Staging_Directory containing only the single Downloaded_PDF, and `--output-dir` pointing to the appropriate Scenarios_Directory.
2. WHEN invoking the chronicle_extractor, THE Download_Workflow SHALL pass `--input-dir` pointing to a Staging_Directory containing the renamed scenario PDF, and `--output-dir` pointing to the appropriate Chronicles_Directory.
3. WHEN invoking the blueprint2layout, THE Download_Workflow SHALL pass `--blueprints-dir`, `--blueprint-id`, and `--output-dir` arguments matching the scenario's system prefix and season.
4. WHEN invoking the layout_generator, THE Download_Workflow SHALL pass the chronicle PDF path directly as the positional argument, along with `--metadata-file` and optionally `--layouts-dir`.
5. WHEN invoking the layout_visualizer, THE Download_Workflow SHALL pass `--layout-root`, `--layout-id`, `--output-dir`, and `--mode data` arguments.

### Requirement 17: Utility-Specific README

**User Story:** As a developer, I want a README.md in the scenario_download_workflow utility's subdirectory, so that I can understand how to use this utility independently.

#### Acceptance Criteria

1. THE Download_Workflow project SHALL include a README.md in the scenario_download_workflow utility's subdirectory.
2. THE README SHALL describe the purpose of the Download_Workflow utility and the five-step Processing_Pipeline.
3. THE README SHALL document the command-line arguments accepted by the Download_Workflow (`--downloads-dir`, `--project-dir`, `--recent`, `--non-interactive`).
4. THE README SHALL include at least one usage example showing a complete command invocation.
5. THE README SHALL note the dependency on the five existing PFS Tools utilities.

### Requirement 18: Top-Level README Update

**User Story:** As a developer, I want the top-level README updated to include the new utility, so that the project index stays current.

#### Acceptance Criteria

1. WHEN the Download_Workflow is added to the project, THE Top_Level_README SHALL be updated to include the Download_Workflow in the utilities table with a relative link to the utility's README.
