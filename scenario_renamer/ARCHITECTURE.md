# Scenario Renamer — Architecture

## Overview

Copies and renames PFS scenario PDFs and associated images (maps,
handouts) into an organized directory tree with descriptive filenames.
Uses a two-pass strategy: PDFs first (to build a lookup table), then
images (to resolve names from the lookup).

## Module Map

```
scenario_renamer/
├── __main__.py      CLI entry point (parse_args, main)
├── classifier.py    Categorizes files as scenario PDFs, images, or other
├── filename.py      Output filename and subdirectory construction
├── image_parser.py  Extracts scenario ids from image filenames
└── processor.py     Orchestrates the two-pass copy/rename pipeline
```

## Data Flow

```
Input directory (recursive scan)
    │
    ▼
classifier.classify_file()
    │  Categorizes each file as:
    │  - scenario_pdf  (has scenario number pattern)
    │  - image         (jpg/png/webp with PZOPFS code or N-XX pattern)
    │  - other         (copied as-is)
    │
    ├─── Pass 1: Scenario PDFs ──────────────────────────┐
    │                                                     │
    │  processor.process_scenario_pdf()                   │
    │    ├─ Opens PDF via chronicle_extractor              │
    │    ├─ Extracts ScenarioInfo (season, number, name)  │
    │    ├─ Copies PDF with descriptive filename           │
    │    └─ Adds entry to lookup: (season, number) → name │
    │                                                     │
    ├─── Pass 2: Images ─────────────────────────────────┐
    │                                                     │
    │  processor.process_scenario_image()                  │
    │    ├─ image_parser.extract_image_scenario_id()       │
    │    │    Parses PZOPFS codes or N-XX patterns         │
    │    ├─ Resolves name from lookup table                │
    │    └─ Copies with descriptive filename + suffix      │
    │                                                     │
    └─── Other files: copied as-is preserving rel path ──┘
```

## Key Design Decisions

- **Two-pass strategy**: PDFs are processed first so the lookup table
  is fully populated before images need to resolve scenario names.
- **Reuses chronicle_extractor**: Scenario metadata extraction is
  delegated to `chronicle_extractor.parser` to avoid duplication.
- **PZOPFS code parsing**: Paizo product codes (e.g., `PZOPFS0409`)
  encode season and scenario number, enabling image attribution
  without opening the associated PDF.

## Dependencies

- `chronicle_extractor` — scenario info extraction and name sanitization
- `PyMuPDF` — PDF text extraction (via chronicle_extractor)
