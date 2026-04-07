# Layout Visualizer — Architecture

## Overview

Renders visual overlays on chronicle PDFs to debug and verify layout
definitions. Supports three modes: canvas region outlines, content
field positions, and example data rendering. Outputs PNG files and
optionally watches for file changes to auto-regenerate.

## Module Map

```
layout_visualizer/
├── __main__.py              CLI entry point, watch mode, wildcard matching
├── coordinate_resolver.py   Canvas/field → pixel coordinate resolution
├── data_renderer.py         Renders example text values onto the page
├── layout_loader.py         Layout index, inheritance, field extraction
├── models.py                Data classes (CanvasRegion, PixelRect, etc.)
├── overlay_renderer.py      Draws colored rectangles and labels on pixmaps
└── pdf_renderer.py          Renders chronicle PDF pages via PyMuPDF

shared/
├── layout_index.py          JSON index building and inheritance chain walking
```

## Data Flow

```
Layout JSON + Chronicle PDF
    │
    ├─── layout_loader.py ────────────────────────────────┐
    │    build_layout_index()                             │
    │      Scans layout root for JSON files, builds       │
    │      id → path map.                                 │
    │    load_layout_with_inheritance()                   │
    │      Walks the parent chain, merges canvases        │
    │      root-first.                                    │
    │    resolve_default_chronicle_location()             │
    │      Finds defaultChronicleLocation in the chain.   │
    │                                                     │
    ├─── pdf_renderer.py ─────────────────────────────────┐
    │    render_pdf_page()                                │
    │      Opens the chronicle PDF, renders the last      │
    │      page at 150 DPI as a PyMuPDF Pixmap.           │
    │                                                     │
    ├─── coordinate_resolver.py ──────────────────────────┐
    │    resolve_canvas_pixels()                          │
    │      Topologically sorts canvases by dependency,    │
    │      resolves each edge to pixel coordinates.       │
    │    resolve_field_pixels()                           │
    │      Resolves content field edges to pixel rects.   │
    │    assign_colors()                                  │
    │      Assigns distinct colors to each canvas.        │
    │                                                     │
    ├─── overlay_renderer.py ─────────────────────────────┐
    │    draw_overlays()                                  │
    │      Draws semi-transparent colored rectangles      │
    │      with labels for each canvas or field region.   │
    │                                                     │
    ├─── data_renderer.py (data mode only) ───────────────┐
    │    draw_data_text()                                 │
    │      Renders example parameter values as styled     │
    │      text at the resolved field positions.          │
    │                                                     │
    └─── Output ──────────────────────────────────────────┐
         Writes PNG to output_dir, preserving the layout  │
         directory structure as subdirectories.           │
```

## Visualization Modes

| Mode | What it draws | Use case |
|------|--------------|----------|
| `canvases` | Colored rectangles for each canvas region | Verify canvas boundaries |
| `fields` | Rectangles for content field positions | Check field placement |
| `data` | Styled text at field positions | Preview filled output |

## Watch Mode

When `--watch` is enabled:

1. Builds a dependency map: each target layout → all files in its
   inheritance chain.
2. Records file modification times.
3. Polls every second for changes.
4. Re-renders only the affected layouts when a dependency changes.

## Key Design Decisions

- **Topological sort**: Canvases can reference other canvases as edges.
  Sorting by dependency ensures references are resolved before use.
- **Inheritance-aware watching**: Changes to a parent layout trigger
  re-rendering of all child layouts that inherit from it.
- **Fuzzy id matching**: `--layout-id` supports shell-style wildcards,
  and unrecognized ids show close matches via `difflib`.
- **Subdirectory mirroring**: Output PNGs mirror the layout directory
  structure, keeping debug output organized by season/type.

## Dependencies

- `PyMuPDF` — PDF rendering and text insertion (data mode)
- `shared.layout_index` — JSON index and inheritance chain utilities
