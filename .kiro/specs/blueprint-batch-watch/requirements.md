# Requirements Document

## Introduction

The blueprint2layout CLI currently accepts three positional arguments (blueprint path, chronicle PDF path, output path) to convert a single Blueprint into a layout JSON file. This feature refactors the CLI to use named arguments mirroring the layout_visualizer's pattern: a `--blueprints-dir` root directory, a `--blueprint-id` with wildcard support, and automatic chronicle PDF resolution from the Blueprint's `defaultChronicleLocation` field. It also adds a `--watch` mode that monitors Blueprint files for changes and auto-regenerates layouts, enabling a two-process workflow where blueprint2layout watches Blueprints and layout_visualizer watches layouts.

## Glossary

- **Blueprint_CLI**: The `blueprint2layout` command-line tool, invocable as `python -m blueprint2layout`.
- **Blueprints_Directory**: The root directory containing `.blueprint.json` files, scanned recursively to build the Blueprint index.
- **Blueprint_Index**: A dictionary mapping Blueprint id strings to their file paths, built by scanning the Blueprints_Directory.
- **Blueprint_Id_Pattern**: A Blueprint id or shell-style wildcard pattern (e.g., `pfs2.bounty*`) used to select one or more Blueprints for processing.
- **Chronicle_PDF**: The Pathfinder Society chronicle sheet PDF file required for structural detection during layout generation.
- **Default_Chronicle_Location**: The `defaultChronicleLocation` field in a Blueprint JSON file, specifying the path to the Chronicle_PDF. Resolved by walking the inheritance chain.
- **Inheritance_Chain**: The ordered sequence of Blueprint files from root ancestor to target Blueprint, connected by `parent` references.
- **Watch_Mode**: An operating mode where the Blueprint_CLI monitors Blueprint files for changes and automatically regenerates layout JSON output, running continuously until interrupted by the user.
- **Output_Directory**: The directory where generated layout JSON files are written. Output filenames are derived automatically from the Blueprint id and Chronicle_PDF stem.

## Requirements

### Requirement 1: Named Argument CLI Interface

**User Story:** As a layout author, I want to specify a Blueprints directory and a Blueprint id pattern instead of individual file paths, so that I can process multiple Blueprints in one invocation without manually specifying each file.

#### Acceptance Criteria

1. THE Blueprint_CLI SHALL accept a required `--blueprints-dir` argument specifying the path to the Blueprints_Directory.
2. THE Blueprint_CLI SHALL accept a required `--blueprint-id` argument specifying a Blueprint_Id_Pattern.
3. THE Blueprint_CLI SHALL accept an optional `--output-dir` argument specifying the Output_Directory, defaulting to the current working directory.
4. THE Blueprint_CLI SHALL accept an optional `--watch` flag for enabling Watch_Mode.
5. THE Blueprint_CLI SHALL remain invocable as `python -m blueprint2layout`.

### Requirement 2: Blueprint Id Wildcard Matching

**User Story:** As a layout author, I want to use shell-style wildcards in the Blueprint id argument, so that I can generate layouts for multiple Blueprints matching a pattern in one command.

#### Acceptance Criteria

1. WHEN the Blueprint_Id_Pattern contains wildcard characters (`*`, `?`, or `[`), THE Blueprint_CLI SHALL match the pattern against all ids in the Blueprint_Index using shell-style glob matching.
2. WHEN the Blueprint_Id_Pattern contains no wildcard characters, THE Blueprint_CLI SHALL treat the pattern as a literal Blueprint id and verify the id exists in the Blueprint_Index.
3. WHEN no Blueprint ids match the Blueprint_Id_Pattern, THE Blueprint_CLI SHALL print an error message identifying the unmatched pattern to stderr and exit with a non-zero status code.
4. THE Blueprint_CLI SHALL return matched Blueprint ids in sorted order.

### Requirement 3: Automatic Chronicle PDF Resolution

**User Story:** As a layout author, I want the chronicle PDF resolved automatically from the Blueprint's `defaultChronicleLocation` field, so that I do not need to specify the PDF path manually for each Blueprint.

#### Acceptance Criteria

1. WHEN generating a layout for a Blueprint, THE Blueprint_CLI SHALL resolve the Chronicle_PDF path from the Blueprint's Default_Chronicle_Location field.
2. WHEN the target Blueprint does not define a Default_Chronicle_Location, THE Blueprint_CLI SHALL walk the Inheritance_Chain from child to root and use the first Default_Chronicle_Location found.
3. IF no Default_Chronicle_Location is found anywhere in the Inheritance_Chain, THEN THE Blueprint_CLI SHALL print an error message identifying the Blueprint id to stderr and exit with a non-zero status code.
4. IF the resolved Chronicle_PDF file does not exist on disk, THEN THE Blueprint_CLI SHALL print an error message identifying the missing file path and the Blueprint id to stderr and exit with a non-zero status code.

### Requirement 4: Automatic Output Path Derivation

**User Story:** As a layout author, I want output files placed in a subdirectory structure mirroring the Blueprints directory, so that the output directory stays organized when processing many Blueprints.

#### Acceptance Criteria

1. THE Blueprint_CLI SHALL derive the output filename by taking the Blueprint id, stripping the prefix up to and including the first dot (`.`), and appending `.json`. For example, a Blueprint with id `pfs2.bounty-layout-b13` produces the filename `bounty-layout-b13.json`.
2. WHEN a Blueprint file is located in a subdirectory relative to the Blueprints_Directory, THE Blueprint_CLI SHALL create the same subdirectory structure under the Output_Directory and write the output file there.
3. WHEN a Blueprint file is located directly in the Blueprints_Directory (no subdirectory), THE Blueprint_CLI SHALL write the output file directly to the Output_Directory.

### Requirement 5: Batch Layout Generation

**User Story:** As a layout author, I want to generate layouts for all matched Blueprints in a single invocation, so that I can update multiple layouts at once.

#### Acceptance Criteria

1. WHEN multiple Blueprint ids match the Blueprint_Id_Pattern, THE Blueprint_CLI SHALL generate a layout JSON file for each matched Blueprint.
2. THE Blueprint_CLI SHALL print a status message to stdout for each layout file generated, identifying the output path.
3. WHEN all layouts are generated successfully, THE Blueprint_CLI SHALL exit with status code 0.

### Requirement 6: Watch Mode

**User Story:** As a layout author, I want the CLI to watch Blueprint files for changes and auto-regenerate layouts, so that I can edit Blueprints and see updated layouts without re-running the command.

#### Acceptance Criteria

1. WHEN the `--watch` flag is provided, THE Blueprint_CLI SHALL generate layouts for all matched Blueprints once and then continue running, monitoring Blueprint files for modifications.
2. WHEN any monitored Blueprint file is modified while in Watch_Mode, THE Blueprint_CLI SHALL regenerate all matched layouts.
3. WHILE in Watch_Mode, THE Blueprint_CLI SHALL monitor all Blueprint files in the Inheritance_Chain of every matched Blueprint, so that changes to parent Blueprints trigger regeneration.
4. WHILE in Watch_Mode, THE Blueprint_CLI SHALL print a message to stdout each time a change is detected and regeneration begins.
5. WHILE in Watch_Mode, THE Blueprint_CLI SHALL continue running until the user sends an interrupt signal (Ctrl+C / SIGINT).
6. WHEN the user sends an interrupt signal in Watch_Mode, THE Blueprint_CLI SHALL exit cleanly with status code 0.
7. IF a regeneration fails due to an error in a modified Blueprint file, THEN THE Blueprint_CLI SHALL print the error to stderr and continue watching.

### Requirement 7: Error Handling

**User Story:** As a layout author, I want clear error messages when something goes wrong, so that I can diagnose and fix issues.

#### Acceptance Criteria

1. IF the Blueprints_Directory path does not exist or is not a directory, THEN THE Blueprint_CLI SHALL print an error message identifying the invalid path to stderr and exit with a non-zero status code.
2. IF a Blueprint file contains invalid JSON, THEN THE Blueprint_CLI SHALL print an error message describing the parse failure to stderr and exit with a non-zero status code.
3. IF a Blueprint references a parent id that does not exist in the Blueprint_Index, THEN THE Blueprint_CLI SHALL print an error message identifying the missing parent id to stderr and exit with a non-zero status code.
4. THE Blueprint_CLI SHALL print all error messages to stderr.

### Requirement 8: Documentation Update

**User Story:** As a layout author, I want the README to reflect the new CLI interface, so that I know how to use the batch and watch features.

#### Acceptance Criteria

1. THE `blueprint2layout/README.md` SHALL be updated to document the new named-argument CLI interface (`--blueprints-dir`, `--blueprint-id`, `--output-dir`, `--watch`).
2. THE README SHALL include usage examples showing batch generation and watch mode.
3. THE README SHALL remove or replace any documentation of the old positional-argument interface.
