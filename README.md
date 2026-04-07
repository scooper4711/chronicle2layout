# PFS Tools

[![CI](https://github.com/scooper4711/chronicle2layout/actions/workflows/ci.yml/badge.svg)](https://github.com/scooper4711/chronicle2layout/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/scooper4711/chronicle2layout)](https://github.com/scooper4711/chronicle2layout/blob/main/LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/scooper4711/chronicle2layout)](https://github.com/scooper4711/chronicle2layout/commits/main)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=bugs)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)

A collection of utilities for Pathfinder Society (PFS) organized play.
Each tool lives in its own Python package with dedicated documentation.

## Utilities

| Utility | Description |
|---------|-------------|
| [Chronicle Extractor](chronicle_extractor/README.md) | Extracts chronicle sheets from scenario PDFs by season. |
| [Scenario Renamer](scenario_renamer/README.md) | Copies and renames scenario PDFs and images. |
| [Blueprint to Layout](blueprint2layout/README.md) | Converts Blueprint JSON into layout JSON via pixel detection. |
| [Layout Generator](layout_generator/README.md) | Generates filled chronicle PDFs from layouts and player data. |
| [Layout Visualizer](layout_visualizer/README.md) | Renders canvas overlays on chronicle PDFs for debugging. |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Suggested Workflow

When working on blueprint layouts, run these in separate terminals:

1. **Blueprint → Layout** (watch mode) — regenerates layout JSON
   whenever a blueprint file changes:

   ```bash
   python -m blueprint2layout \
     --blueprints-dir Blueprints \
     --blueprint-id 'pfs2.*' \
     --watch \
     --output-dir modules/pfs-chronicle-generator/assets/layouts/
   ```

2. **Layout Visualizer** (watch mode) — re-renders debug PNGs
   whenever a layout file changes. Valid modes are `fields`, `canvases`, and `data`.

   ```bash
   python -m layout_visualizer \
     --watch \
     --mode fields \
     --layout-root modules/pfs-chronicle-generator/assets/layouts \
     --layout-id 'pfs2.*' \
     --output-dir debug_clips/layout_visualizer
   ```

3. **Layout Generator** — run as needed to produce the leaf layout
   files from chronicle PDFs and the TOML metadata:

   ```bash
   python -m layout_generator \
     --metadata-file chronicle_properties.toml \
     modules/pfs-chronicle-generator/assets/chronicles
   ```

## Testing

```bash
python -m pytest tests/ -v
```

## Pre-Push Checklist

1. Run the linter — no errors
2. Run the full test suite — all tests pass
