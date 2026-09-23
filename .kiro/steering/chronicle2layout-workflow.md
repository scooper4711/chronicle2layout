# chronicle2layout Project Workflow

## Project Overview

chronicle2layout is a collection of Python utilities for Pathfinder Society (PFS) and Starfinder Society (SFS) organized play. It processes scenario PDFs into structured layout JSON files consumed by the pfs-chronicle-generator FoundryVTT module.

## Game Systems

- **pfs2** — Pathfinder Society 2nd Edition (seasons 1-8, plus bounties, quests, intros)
- **sfs2** — Starfinder Society 2nd Edition (seasons 1-2)

## Utilities (Processing Pipeline)

These run in order when processing a new scenario:

1. **scenario_renamer** — Copies/renames scenario PDFs into organized `Scenarios/PFS/` or `Scenarios/SFS/` directories by season.
2. **chronicle_extractor** — Extracts the chronicle sheet (last page) from a scenario PDF into `modules/pfs-chronicle-generator/assets/chronicles/{system}/{season}/`.
3. **blueprint2layout** — Converts declarative Blueprint JSON into layout JSON via pixel detection of structural lines in the chronicle PDF.
4. **layout_generator** — Generates leaf layout JSON from chronicle PDFs using TOML metadata rules to match PDFs to parent layouts.
5. **layout_visualizer** — Renders debug PNG overlays (canvases, fields, or data mode) on chronicle PDFs for visual verification.
6. **scenario_download_workflow** — Orchestrates all five steps automatically for newly downloaded PDFs.

## Key Files and Directories

| Path | Purpose |
|------|---------|
| `chronicle_properties.toml` | Regex rules mapping chronicle PDFs to parent blueprint layouts |
| `Blueprints/` | Declarative blueprint JSON files defining canvas regions via structural line references |
| `Blueprints/pfs2/pfs2.blueprint.json` | Root PFS2 blueprint (defines `page` canvas and `aspectratio`) |
| `Blueprints/sfs2/sfs2.blueprint.json` | Root SFS2 blueprint |
| `Blueprints/{system}/season{N}/` | Season-specific blueprint files |
| `modules/pfs-chronicle-generator/assets/chronicles/` | Extracted chronicle sheet PDFs |
| `modules/pfs-chronicle-generator/assets/layouts/` | Generated layout JSON files |
| `BLUEPRINT_FORMAT.md` | Full specification of the blueprint file format |
| `LAYOUT_FORMAT.md` | Full specification of the output layout file format |

## Adding a New Season

1. Create `Blueprints/{system}/season{N}/s{N}-00.blueprint.json` — copy the previous season's catch-all blueprint and update the `id` and `description`.
2. Add a catch-all `[[rules]]` section to `chronicle_properties.toml` with the new season's pattern, id, parent, description, and default_chronicle_location.
3. Create output directories: `modules/pfs-chronicle-generator/assets/chronicles/{system}/season{N}/` and `modules/pfs-chronicle-generator/assets/layouts/{system}/season{N}/`.
4. When the first chronicle PDF arrives, run `blueprint2layout` to verify the blueprint resolves correctly. Adjust canvas edges if the new season's layout differs from the previous.

## Blueprint Concepts

- Blueprints are declarative — they reference detected structural elements (lines, bars, grey boxes) by category and index rather than hard-coding pixel coordinates.
- Inheritance: child blueprints reference a parent via `"parent": "pfs2"` and inherit its canvases.
- Edge values: numeric literals, line references (`h_bar[0]`, `v_thin[2]`), canvas references (`main.left`), or canvas-scoped references (`@h_rule[0]`).
- Detection categories: `h_thin`, `h_bar`, `h_rule`, `v_thin`, `v_bar`, `grey_box`.
- The `s{N}-00` blueprint is the catch-all for a season. Per-scenario overrides (like `s7-06`) handle chronicles with different structural layouts.

## TOML Rules Structure

Each `[[rules]]` entry in `chronicle_properties.toml` contains:
- `pattern` — regex anchored to `{system}/season{N}/` to match chronicle filenames
- `id` — the layout id using capture groups (e.g., `pfs2.s8-$1`)
- `parent` — references the season blueprint id (e.g., `pfs2.season8-layout-s8-00`)
- `description` — human-readable name with `${~N}` for CamelCase splitting
- `default_chronicle_location` — module path to the chronicle PDF

Rules are tested in order; the first matching pattern wins. Specific overrides must appear before catch-all rules for the same season.

## Common Commands

```bash
# Activate venv
source .venv/bin/activate

# Process a newly downloaded scenario end-to-end
python -m scenario_download_workflow

# Generate layouts from blueprints (single or wildcard)
python -m blueprint2layout --blueprints-dir Blueprints --blueprint-id "pfs2.season8*" --output-dir modules/pfs-chronicle-generator/assets/layouts/

# Generate leaf layouts from chronicle PDFs
python -m layout_generator --metadata-file chronicle_properties.toml modules/pfs-chronicle-generator/assets/chronicles

# Visualize layouts for debugging
python -m layout_visualizer --layout-root modules/pfs-chronicle-generator/assets/layouts --layout-id "pfs2.s8*" --mode fields --output-dir debug_clips/layout_visualizer

# Watch mode for iterative blueprint development
python -m blueprint2layout --blueprints-dir Blueprints --blueprint-id "pfs2.season8*" --watch --output-dir modules/pfs-chronicle-generator/assets/layouts/

# Sync generated assets to sibling pfs-chronicle-generator repo
./sync_assets.sh

# Run tests
python -m pytest tests/ -v

# Lint
ruff check .
ruff format --check .
```

## Sibling Repository Relationship

- chronicle2layout generates layouts and holds chronicle PDFs under `modules/pfs-chronicle-generator/assets/`.
- The sibling `../pfs-chronicle-generator` repo is the FoundryVTT module that consumes these assets at runtime.
- Use `./diff_assets.sh` to review changes and `./sync_assets.sh` to push updated assets to the sibling repo.
