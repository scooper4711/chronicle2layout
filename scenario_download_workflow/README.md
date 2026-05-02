# Scenario Download Workflow

Automates the end-to-end processing of newly downloaded Pathfinder Society
(PFS) and Starfinder Society (SFS) scenario PDFs. Scans your downloads
folder for recent PDFs, detects the game system, extracts scenario metadata,
then orchestrates the five existing PFS Tools utilities in sequence.

## How It Works

The workflow runs a five-step processing pipeline for each confirmed PDF:

1. **Scenario Renamer** — renames and files the PDF into `Scenarios/PFS/` or
   `Scenarios/SFS/` with a descriptive filename organized by season.

2. **Chronicle Extractor** — extracts the chronicle sheet page from the
   scenario PDF into the appropriate chronicles directory.

3. **Blueprint to Layout** — converts the season-level base blueprint to a
   layout JSON and reports which blueprint the new scenario resolves to.
   Skips gracefully if no blueprint exists for the season.

4. **Layout Generator** — generates a leaf layout JSON from the chronicle
   PDF and TOML metadata, capturing item lines and checkboxes.

5. **Layout Visualizer** — renders a data-mode preview PNG so you can
   immediately see how the chronicle sheet looks with example data.

The tool detects whether a scenario is Pathfinder or Starfinder by inspecting
the PDF's first page text for "Pathfinder Society" or "Starfinder Society"
headers, then routes files to the correct directory trees automatically.

## Usage

```bash
python -m scenario_download_workflow
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--downloads-dir` | Directory to scan for PDFs (default: `~/Downloads`) |
| `--project-dir` | PFS Tools project root (default: current directory) |
| `--recent` | Recency window for PDF discovery (default: `1h`). Supported suffixes: `m` (minutes), `h` (hours), `d` (days). |
| `--non-interactive` | Process all discovered PDFs without prompting |

### Examples

```bash
# Process PDFs downloaded in the last hour (default)
python -m scenario_download_workflow

# Scan a custom downloads folder with a 2-day recency window
python -m scenario_download_workflow \
  --downloads-dir /path/to/downloads \
  --recent 2d

# Process all recent PDFs without confirmation prompts
python -m scenario_download_workflow --non-interactive

# Specify a different project root
python -m scenario_download_workflow --project-dir /path/to/pfs-tools
```

### Interactive Mode

By default, the tool prompts for each discovered PDF:

```
Process PZO9507-06.pdf? [y/n/q]
```

- `y` / `yes` — process the PDF
- `n` / `no` — skip the PDF
- `q` / `quit` — stop processing and skip all remaining PDFs

Use `--non-interactive` to skip prompts and process everything.

## Syncing Assets

After processing scenarios, the generated layouts and chronicles live under
`modules/pfs-chronicle-generator/assets`. Two helper scripts push changes
to the sibling `../pfs-chronicle-generator` repo.

### Review changes

Compare JSON layout files and interactively view diffs for any that have
actual content changes:

```bash
./diff_assets.sh
```

### Push updated assets

Copy all new or changed files to the sibling repo. Files that are newer by
timestamp but identical in content are skipped.

```bash
./sync_assets.sh           # copy changed files
./sync_assets.sh --dry-run # preview what would be copied
```

## Dependencies

This utility orchestrates the five existing PFS Tools packages by calling
their `main()` functions directly (no subprocesses):

- `scenario_renamer` — PDF renaming and filing
- `chronicle_extractor` — chronicle sheet extraction and scenario info parsing
- `blueprint2layout` — blueprint-to-layout JSON conversion
- `layout_generator` — leaf layout JSON generation
- `layout_visualizer` — data-mode preview rendering

It also depends on `PyMuPDF` (`fitz`) for reading PDF text content.

All packages must be available on the Python path (they share the same
project root).

## Testing

```bash
python -m pytest tests/scenario_download_workflow/ -v
```
