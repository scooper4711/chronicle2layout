# Requirements Document

## Introduction

A Python command-line utility that extracts chronicle pages from Pathfinder Society (PFS) scenario PDF files. The utility reads the first page of each PDF to identify the scenario number (e.g., #1-07) and name, then extracts the last page (the chronicle sheet) as a separate PDF. Output files are organized into season-based subdirectories with sanitized filenames.

## Glossary

- **Chronicle_Extractor**: The Python command-line utility that processes scenario PDFs and extracts chronicle pages.
- **Scenario_PDF**: A Pathfinder Society scenario PDF file containing game content with a chronicle sheet as the last page.
- **PFS_Scenario_Number**: A scenario identifier in the format `#X-YY` where X is the season number and YY is the zero-padded scenario number within that season (e.g., #1-07, #2-12).
- **Scenario_Name**: The title of the scenario as printed on the first page of the Scenario_PDF, following the PFS_Scenario_Number.
- **Chronicle_Page**: The last page of a Scenario_PDF, containing the chronicle sheet used for tracking player rewards.
- **Season_Directory**: A subdirectory under the output directory named `Season X` where X is the season number extracted from the PFS_Scenario_Number.
- **Sanitized_Name**: The Scenario_Name with spaces removed and problematic filename characters (single quotes, colons, semicolons, question marks, slashes, backslashes, asterisks, angle brackets, pipes, double quotes) stripped out.
- **Map_PDF**: A PDF file whose stem (filename without extension) ends with "Map" or "Maps" (case-insensitive), which contains map images rather than scenario content.
- **Utility_README**: A README.md file located in the Chronicle_Extractor utility's subdirectory, documenting usage, examples, and configuration specific to that utility.
- **Top_Level_README**: A README.md file at the project root that serves as an index linking to each utility's Utility_README.
- **Requirements_File**: A `requirements.txt` file at the project root listing Python package dependencies needed by the project's virtual environment.

## Requirements

### Requirement 1: CLI Argument Parsing

**User Story:** As a user, I want to specify input and output directories via command-line arguments, so that I can control where scenario PDFs are read from and where chronicle PDFs are saved.

#### Acceptance Criteria

1. THE Chronicle_Extractor SHALL accept a required `--input-dir` command-line argument specifying the directory containing Scenario_PDFs.
2. THE Chronicle_Extractor SHALL accept a required `--output-dir` command-line argument specifying the base directory for saving extracted Chronicle_Pages.
3. IF the `--input-dir` path does not exist, THEN THE Chronicle_Extractor SHALL exit with a non-zero exit code and print a descriptive error message to stderr.
4. IF the `--output-dir` path does not exist, THEN THE Chronicle_Extractor SHALL create the directory (including parent directories).

### Requirement 2: File Filtering

**User Story:** As a user, I want the utility to skip non-PDF files and map PDFs, so that only actual scenario PDFs are processed.

#### Acceptance Criteria

1. THE Chronicle_Extractor SHALL process only files with a `.pdf` extension (case-insensitive).
2. THE Chronicle_Extractor SHALL skip any file whose stem (filename without the `.pdf` extension) ends with "Map" or "Maps" (case-insensitive).
3. THE Chronicle_Extractor SHALL skip non-file entries (directories, symlinks) in the input directory.

### Requirement 3: Scenario Number and Name Extraction

**User Story:** As a user, I want the utility to automatically identify the PFS scenario number and name from each PDF, so that chronicle files are named correctly without manual input.

#### Acceptance Criteria

1. WHEN a Scenario_PDF is opened, THE Chronicle_Extractor SHALL read the text content of the first page to locate the PFS_Scenario_Number.
2. WHEN the first page text contains a PFS_Scenario_Number in the format `#X-YY`, THE Chronicle_Extractor SHALL extract the season number (X) and the scenario number (YY).
3. WHEN the first page text contains a PFS_Scenario_Number, THE Chronicle_Extractor SHALL extract the Scenario_Name that follows the PFS_Scenario_Number on the same line or subsequent text.
4. IF the first page does not contain a recognizable PFS_Scenario_Number, THEN THE Chronicle_Extractor SHALL skip the file and log a warning message to stderr.

### Requirement 4: Chronicle Page Extraction

**User Story:** As a user, I want the last page of each scenario PDF extracted as a separate PDF, so that I have standalone chronicle sheets for my players.

#### Acceptance Criteria

1. WHEN a valid PFS_Scenario_Number is extracted, THE Chronicle_Extractor SHALL extract the last page of the Scenario_PDF as a new single-page PDF document.
2. THE Chronicle_Extractor SHALL save the extracted Chronicle_Page to the Season_Directory corresponding to the season number from the PFS_Scenario_Number.
3. IF the Season_Directory does not exist, THEN THE Chronicle_Extractor SHALL create the Season_Directory before saving.

### Requirement 5: Output Filename Construction

**User Story:** As a user, I want chronicle files named with the scenario number and a sanitized scenario name, so that files are easy to identify and compatible with all operating systems.

#### Acceptance Criteria

1. THE Chronicle_Extractor SHALL construct the output filename in the format `{season}-{scenario}-{Sanitized_Name}Chronicle.pdf` (e.g., `1-07-FloodedKingsCourtChronicle.pdf`).
2. THE Chronicle_Extractor SHALL remove spaces from the Scenario_Name when constructing the Sanitized_Name.
3. THE Chronicle_Extractor SHALL strip the following characters from the Scenario_Name: single quotes (`'`), colons (`:`), semicolons (`;`), question marks (`?`), forward slashes (`/`), backslashes (`\`), asterisks (`*`), angle brackets (`<`, `>`), pipes (`|`), and double quotes (`"`).
4. THE Chronicle_Extractor SHALL preserve the original letter casing of the Scenario_Name in the Sanitized_Name.

### Requirement 6: Processing Feedback

**User Story:** As a user, I want to see what the utility is doing as it processes files, so that I can verify it is working correctly and troubleshoot issues.

#### Acceptance Criteria

1. WHEN a Chronicle_Page is successfully extracted, THE Chronicle_Extractor SHALL print the output file path to stdout.
2. WHEN a file is skipped due to filtering rules, THE Chronicle_Extractor SHALL print a skip message to stderr indicating the filename and reason.
3. WHEN a file is skipped because no PFS_Scenario_Number is found, THE Chronicle_Extractor SHALL print a warning to stderr indicating the filename.
4. IF an error occurs while reading or writing a PDF, THEN THE Chronicle_Extractor SHALL print an error message to stderr and continue processing remaining files.

### Requirement 7: Recursive Directory Traversal

**User Story:** As a user, I want the utility to process scenario PDFs from the input directory only (not subdirectories), so that I can point it at a single season folder.

#### Acceptance Criteria

1. THE Chronicle_Extractor SHALL process files in the immediate input directory only, without recursing into subdirectories.

### Requirement 8: Utility-Specific README

**User Story:** As a developer, I want a README.md in the chronicle-extractor utility's subdirectory, so that I can understand how to use, configure, and contribute to this specific utility independently of other utilities in the project.

#### Acceptance Criteria

1. THE Chronicle_Extractor project SHALL include a Utility_README in the Chronicle_Extractor utility's subdirectory.
2. THE Utility_README SHALL describe the purpose of the Chronicle_Extractor utility.
3. THE Utility_README SHALL document the command-line arguments accepted by the Chronicle_Extractor (`--input-dir` and `--output-dir`).
4. THE Utility_README SHALL include at least one usage example showing a complete command invocation.
5. THE Utility_README SHALL list the Python package dependencies required by the Chronicle_Extractor.

### Requirement 9: Top-Level README

**User Story:** As a developer, I want a top-level README.md at the project root that links to each utility's README, so that I have a single entry point for discovering all utilities in the project.

#### Acceptance Criteria

1. THE project SHALL include a Top_Level_README at the project root.
2. THE Top_Level_README SHALL describe the overall purpose of the project.
3. THE Top_Level_README SHALL contain a section listing all available utilities with a relative link to each utility's Utility_README.
4. THE Top_Level_README SHALL include the Chronicle_Extractor as the first listed utility.

### Requirement 10: Python Dependency Manifest

**User Story:** As a developer, I want a requirements.txt at the project root listing all Python package dependencies, so that I can reproduce the virtual environment reliably.

#### Acceptance Criteria

1. THE project SHALL include a Requirements_File at the project root.
2. THE Requirements_File SHALL list PyMuPDF as a dependency (the package providing the `fitz` module for PDF processing).
3. THE Requirements_File SHALL list pytest as a dependency (the test runner).
4. THE Requirements_File SHALL list hypothesis as a dependency (the property-based testing library).
5. WHEN a developer runs `pip install -r requirements.txt` inside the project virtual environment, THE pip installer SHALL install all packages listed in the Requirements_File.
