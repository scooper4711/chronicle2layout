# PFS Tools

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=bugs)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=scooper4711_chronicle2layout&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=scooper4711_chronicle2layout)

A collection of utilities for Pathfinder Society (PFS) organized play. Each tool lives in its own Python package directory with dedicated documentation.

## Utilities

| Utility | Description |
|---------|-------------|
| [Chronicle Extractor](chronicle_extractor/README.md) | Extracts chronicle sheet pages from PFS scenario PDFs into organized, per-season directories. |
| [Scenario Renamer](scenario_renamer/README.md) | Copies and renames PFS scenario PDFs and images into organized, per-season directories with descriptive filenames. |
| [Blueprint to Layout](blueprint2layout/README.md) | Converts declarative Blueprint JSON files + chronicle PDFs into layout.json files via pixel-based structural detection. |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
