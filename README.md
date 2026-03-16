# chronicle2layout

Extract checkboxes and text from PDF chronicle sheets (Pathfinder Society) and generate layout JSON files describing form field positions.

The generated layout JSON is consumed by the PFS Chronicle Generator Foundry VTT module to render filled chronicle sheets.

## Module Structure

```
src/
├── chronicle2layout.py    CLI entry point, text extraction
├── shared_utils.py        Shared utilities (layout file resolution, canvas transforms, image rendering)
├── item_segmenter.py      Item segmentation using parenthesis-based heuristics
├── checkbox_extractor.py  Checkbox detection and label extraction
├── layout_generator.py    Layout JSON assembly
├── clip_canvas.py         Canvas region clipping utility
├── generate_layouts.py    Batch processing across seasons
└── yaml2json.py           YAML to JSON converter

tools/
├── build_season4_layout.py          Build Season 4 layout from template
├── extract_season4_canvases.py      Extract canvas regions from Season 4 PDFs
├── extract_season4_content.py       Extract content from Season 4 chronicle sheets
└── season4_template.json            Template data for Season 4 layout generation
```

## Install

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Single Chronicle

Generate a layout JSON for one PDF:

```bash
cd src
python chronicle2layout.py /path/to/chronicle.pdf \
  --parent pfs2.season6 \
  --id pfs2.s6-07 \
  --description "6-07 Rotten Apples" \
  --layout-dir ../../layouts \
  --output output.json
```

The script prints JSON to stdout (or writes to `--output`). Key CLI options:

- `--parent` — Parent layout ID for canvas coordinate lookup
- `--id` — Layout ID for the output JSON
- `--description` — Scenario description
- `--layout-dir` — Base layouts directory
- `--region` — Manual region as `x0,y0,x1,y1` percentages (overrides canvas lookup)
- `--item-canvas` — Canvas name for item extraction (default: `items`)
- `--checkbox-canvas` — Canvas name for checkbox detection (default: `summary`)
- `--default-chronicle` — Default path to the blank chronicle PDF
- `--debug-dir` — Directory for debug output

### Batch Processing

Generate layouts for all chronicles in one or more seasons:

```bash
cd src
python generate_layouts.py --season 6 7
python generate_layouts.py --season 4 --scenarios 01 02 08
```

Options:

- `--season` / `-s` — Season number(s) to process (default: all)
- `--scenarios` / `-n` — Filter to specific scenario numbers
- `--base-dir` — Project root directory (default: auto-detected)
- `--python` — Python executable for subprocess calls (default: current interpreter)

### Utilities

Clip a canvas region from a PDF:

```bash
cd src
python clip_canvas.py --pdf /path/to/chronicle.pdf \
  --layout-dir ../../layouts --parent pfs2.season5 \
  --canvas items --output clipped.png
```

Convert YAML layout files to JSON:

```bash
cd src
python yaml2json.py
```

### Tools (Season 4)

The `tools/` directory contains scripts for Season 4 chronicle processing:

- `extract_season4_canvases.py` — Extract canvas regions from Season 4 PDFs
- `extract_season4_content.py` — Detect grey boxes and extract text content
- `build_season4_layout.py` — Assemble Season 4 layout JSON from template

## Running Tests

```bash
source .venv/bin/activate
python -m pytest
```

## License

MIT
