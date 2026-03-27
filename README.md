# PFS Tools

A collection of utilities for Pathfinder Society (PFS) organized play. Each tool lives in its own Python package directory with dedicated documentation.

## Utilities

| Utility | Description |
|---------|-------------|
| [Chronicle Extractor](chronicle_extractor/README.md) | Extracts chronicle sheet pages from PFS scenario PDFs into organized, per-season directories. |
| [Scenario Renamer](scenario_renamer/README.md) | Copies and renames PFS scenario PDFs and images into organized, per-season directories with descriptive filenames. |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
