# Layout Generator — Architecture

## Overview

Generates leaf layout JSON files from chronicle PDFs and a TOML metadata
file. Matches each PDF against regex rules to find its parent layout,
resolves canvas coordinates from the inheritance chain, extracts item
positions and checkboxes, and writes per-chronicle layout files.

## Module Map

```
layout_generator/
├── __main__.py            CLI entry point, PDF collection, orchestration
├── generator.py           Layout JSON assembly (metadata + items + checkboxes)
├── metadata.py            TOML rule loading, regex matching, template substitution
├── text_extractor.py      PDF text extraction within canvas regions
├── item_segmenter.py      Groups extracted text lines into item entries
└── checkbox_extractor.py  Detects checkbox glyphs within canvas regions

shared/
├── layout_index.py        JSON index building and inheritance chain walking
```

## Data Flow

```
TOML metadata + Chronicle PDFs
    │
    ├─── metadata.py ─────────────────────────────────────┐
    │    load_metadata() parses the TOML file into        │
    │    MetadataConfig with ordered MetadataRule list.   │
    │    match_metadata() tests each PDF path against     │
    │    rules (first match wins), applies regex capture  │
    │    group substitution ($1, ${~2}, etc.) to produce  │
    │    MatchedMetadata (id, parent, description, path). │
    │                                                     │
    ├─── __main__.py ─────────────────────────────────────┐
    │    resolve_canvas_region()                          │
    │      Loads the parent layout's inheritance chain    │
    │      via shared.layout_index, composes absolute     │
    │      page coordinates for the target canvas by      │
    │      walking parent-relative → absolute conversion. │
    │                                                     │
    ├─── text_extractor.py ───────────────────────────────┐
    │    extract_text_lines()                             │
    │      Opens the PDF last page via PyMuPDF,           │
    │      filters words to the items canvas region,      │
    │      groups into lines by y-coordinate proximity.   │
    │                                                     │
    ├─── item_segmenter.py ───────────────────────────────┐
    │    segment_items()                                  │
    │      Parses text lines into structured item entries.│
    │      Detects headers, accumulates multi-line items, │
    │      cleans text (strips bullets, normalizes).      │
    │                                                     │
    ├─── checkbox_extractor.py ───────────────────────────┐
    │    detect_checkboxes()                              │
    │      Scans PDF text for checkbox Unicode glyphs     │
    │      (☐, ☑, ✓) within the summary canvas region .   │
    │      Returns region-relative percentage positions.  │
    │                                                     │
    └─── generator.py ────────────────────────────────────┐
         generate_layout_json()                           │
           Assembles the final layout dict:               │
           - metadata (id, parent, description)           │
           - items section with positions and text        │
           - checkboxes section with positions            │
           Writes formatted JSON to output path.          │
```

## TOML Rule Matching

Rules in `chronicle_properties.toml` are tested in order; first match
wins. Each rule contains:

- `pattern` — regex matched against the PDF's relative path
- `id` — output layout id (supports `$1`, `$2` substitution)
- `parent` — parent layout id for inheritance
- `description` — human-readable label (`${~N}` for CamelCase split)
- `default_chronicle_location` — path template for the chronicle PDF

## Key Design Decisions

- **First-match-wins**: Rule ordering in the TOML controls precedence.
  Specific overrides (e.g., single-chronicle rules) go before
  catch-all patterns.
- **Regex capture groups**: Template substitution (`$1`, `${~2}`)
  avoids needing a separate rule per chronicle.
- **Canvas-scoped extraction**: Text and checkbox extraction are
  limited to specific canvas regions, avoiding false positives from
  other page areas.
- **Inheritance chain resolution**: Leaf layouts reference a parent
  layout id. The generator walks the chain to compute absolute
  coordinates before extracting content.

## Dependencies

- `PyMuPDF` — PDF text extraction and glyph detection
- `shared.layout_index` — JSON index and inheritance chain utilities
