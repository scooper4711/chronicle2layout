# Chronicle Extractor — Architecture

## Overview

Extracts the last page (chronicle sheet) from PFS scenario PDFs and
saves each as a standalone PDF in a season-based directory structure.

## Module Map

```
chronicle_extractor/
├── __main__.py      CLI entry point (parse_args, main)
├── extractor.py     Core extraction logic
├── filename.py      Output path and name sanitization
├── filters.py       PDF file classification (map vs scenario)
└── parser.py        Scenario number/name extraction from PDF text
```

## Data Flow

```
Scenario PDF
    │
    ▼
filters.is_scenario_pdf()     ← skip maps and non-PDFs
    │
    ▼
parser.extract_from_chronicle()
    │  Reads first-page text, regex-matches "#X-YY" pattern,
    │  collects the scenario name from subsequent lines.
    │  Returns ScenarioInfo(season, number, name).
    │
    ▼
filename.build_output_path()
    │  Sanitizes the name (strips punctuation, CamelCases),
    │  builds: output_dir/Season X/X-YY-NameChronicle.pdf
    │
    ▼
extractor.extract_last_page()
    │  Opens the PDF via PyMuPDF, copies the last page into
    │  a new single-page document, saves to output path.
    │
    ▼
Single-page chronicle PDF
```

## Key Design Decisions

- **Last page extraction**: Chronicle sheets are always the final page
  of a scenario PDF. This avoids needing to detect page content.
- **First-page parsing**: The scenario number and name appear on page 1
  in a consistent `#X-YY` format, making regex extraction reliable.
- **Non-recursive scan**: Only processes PDFs directly in `--input-dir`,
  not subdirectories. This matches the flat per-season input layout.

## Dependencies

- `PyMuPDF` — PDF reading, page extraction, text extraction
