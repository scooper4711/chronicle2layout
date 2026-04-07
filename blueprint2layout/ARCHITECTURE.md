# Blueprint to Layout — Architecture

## Overview

Converts declarative Blueprint JSON files into layout JSON files by
combining blueprint definitions with pixel-based structural detection
on chronicle PDFs. Detects lines, bars, grey boxes, and rules, then
resolves canvas edge references to produce parent-relative percentage
coordinates.

## Module Map

```
blueprint2layout/
├── __init__.py         Public API (generate_layout)
├── __main__.py         CLI entry point, watch mode, wildcard matching
├── blueprint.py        Blueprint JSON parsing and validation
├── converter.py        Absolute → parent-relative coordinate conversion
├── detection.py        Pixel-based structural element detection
├── field_resolver.py   Content field edge resolution and scoping
├── models.py           Data classes (DetectionResult, CanvasEntry, etc.)
├── output.py           Layout JSON assembly and file writing
├── pdf_preparation.py  PDF rendering, text/image redaction
└── resolver.py         Edge value resolution (numeric, line ref, canvas ref)

shared/
├── layout_index.py     JSON index building and inheritance chain walking
```

## Data Flow

```
Blueprint JSON + Chronicle PDF
    │
    ├─── blueprint.py ────────────────────────────────────┐
    │    Parses blueprint, validates edge values,         │
    │    loads inheritance chain via shared.layout_index  │
    │                                                     │
    ├─── pdf_preparation.py ──────────────────────────────┐
    │    Opens PDF last page, redacts text and images,    │
    │    renders at 150 DPI → grayscale + RGB arrays      │
    │                                                     │
    ├─── detection.py ────────────────────────────────────┐
    │    Scans pixel arrays for structural elements:      │
    │    ┌──────────────────────────────────────────┐     │
    │    │ h_thin  — horizontal thin lines (≤5px)   │     │
    │    │ h_bar   — horizontal thick bars (>5px)   │     │
    │    │ h_rule  — grey horizontal rules          │     │
    │    │ v_thin  — vertical thin lines (≤5px)     │     │
    │    │ v_bar   — vertical thick bars (>5px)     │     │
    │    │ grey_box — grey filled rectangles        │     │
    │    └──────────────────────────────────────────┘     │
    │    Also extracts vector h_rules from PDF if         │
    │    too thin to survive rasterization.               │
    │                                                     │
    ├─── resolver.py ─────────────────────────────────────┐
    │    Resolves each canvas edge value:                 │
    │    - Numeric literal → pass through                 │
    │    - Line reference (h_bar[0]) → detected position  │
    │    - Canvas reference (main.left) → resolved canvas │
    │    Supports .left/.right/.top/.bottom suffixes      │
    │    for secondary axis access.                       │
    │                                                     │
    ├─── field_resolver.py ───────────────────────────────┐
    │    Resolves content field positions within canvases.│
    │    Scopes detection results to the parent canvas.   │
    │    Handles @-prefixed references for scoped lookup. │
    │                                                     │
    ├─── converter.py ────────────────────────────────────┐
    │    Converts absolute page percentages to            │
    │    parent-relative percentages.                     │
    │                                                     │
    └─── output.py ───────────────────────────────────────┐
         Assembles the final layout dict, copies pass-    │
         through properties, writes formatted JSON.       │
```

## Detection Pipeline Detail

```
grayscale image
    │
    ├─ detect_horizontal_black_lines()
    │    Row-by-row scan for black pixel runs >5% width.
    │    Groups consecutive rows, classifies by thickness:
    │    ≤5px → h_thin, >5px → h_bar
    │
    ├─ detect_vertical_black_lines()
    │    Column-by-column scan, same grouping/classification.
    │    ≤5px → v_thin, >5px → v_bar
    │
    ├─ detect_grey_rules()
    │    Scans for grey pixel runs, deduplicates against
    │    black lines to avoid double-counting.
    │
    ├─ detect_grey_boxes()
    │    Flood-fill on grey mask to find rectangular regions.
    │
    └─ extract_vector_h_rules() (optional, from PDF)
         Extracts thin vector lines from PDF drawing ops
         that don't survive rasterization.
```

## Key Design Decisions

- **Pixel detection over PDF parsing**: Chronicle layouts vary across
  seasons. Pixel analysis adapts to any visual layout without needing
  PDF structure knowledge.
- **Inheritance chain**: Blueprints inherit canvases from parents,
  allowing shared structure (e.g., `pfs2` root) with per-season
  overrides.
- **Parent-relative coordinates**: Output coordinates are relative to
  the parent canvas, not the page. This makes layouts composable.
- **Watch mode**: Monitors all files in the inheritance chain and
  re-generates when any change is detected.

## Dependencies

- `PyMuPDF` — PDF rendering and vector line extraction
- `NumPy` — image array manipulation for detection
- `shared.layout_index` — JSON index and inheritance chain utilities
