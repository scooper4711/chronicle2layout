# Blueprint to Layout

Converts declarative Blueprint JSON files into layout.json files conforming to [LAYOUT_FORMAT.md](../LAYOUT_FORMAT.md). Takes a Blueprint and a chronicle PDF as inputs, detects structural elements (lines, bars, grey boxes) via pixel analysis, resolves canvas edge references, and outputs parent-relative percentage coordinates.

## Usage

### CLI

```bash
python -m blueprint2layout <blueprint.json> <chronicle.pdf> <output.json> [--blueprints-dir <dir>]
```

- `blueprint.json` — the Blueprint file describing canvas regions
- `chronicle.pdf` — the chronicle PDF to analyze
- `output.json` — where to write the layout
- `--blueprints-dir` — directory to scan for parent Blueprints (defaults to the Blueprint file's directory)

### Python API

```python
from blueprint2layout import generate_layout

layout = generate_layout("path/to/blueprint.json", "path/to/chronicle.pdf")
```

## Blueprint Format

Blueprint files use the `.blueprint.json` extension and contain:

```json
{
  "id": "pfs2.b1",
  "parent": "pfs2",
  "description": "#B1: The Whitefang Wyrm",
  "canvases": [
    {
      "name": "main",
      "parent": "page",
      "left": "v_bar[0]",
      "right": "v_thin[2]",
      "top": "h_thin[2]",
      "bottom": "h_thin[8]"
    }
  ]
}
```

### Edge Values

Each canvas edge can be:

- A numeric literal: `0`, `100`, `5.9`
- A line reference: `"h_bar[0]"`, `"v_thin[2]"` — resolves to the detected line's position
- A canvas reference: `"main.left"`, `"summary.bottom"` — resolves to an already-defined canvas edge

### Detection Categories

| Category | Description | Primary Axis |
|----------|-------------|-------------|
| `h_thin` | Horizontal thin lines (≤ 5px) | y |
| `h_bar` | Horizontal thick bars (> 5px) | y |
| `h_rule` | Grey horizontal rules | y |
| `v_thin` | Vertical thin lines (≤ 5px) | x |
| `v_bar` | Vertical thick bars (> 5px) | x |
| `grey_box` | Grey filled rectangles | — |

### Inheritance

Blueprints support inheritance via the `parent` property. A child Blueprint inherits all canvases from its parent chain and can reference them in its own canvas definitions.

### Pass-through Properties

These Blueprint properties are copied directly to the output layout: `id`, `parent`, `description`, `flags`, `aspectratio`.

## Pipeline

1. Strip text and images from the PDF's last page, render at 150 DPI
2. Detect structural elements (6 categories) via pixel analysis
3. Load the Blueprint with its inheritance chain
4. Resolve canvas edges (numeric, line reference, or canvas reference)
5. Convert absolute percentages to parent-relative percentages
6. Write the layout JSON

## Testing

```bash
python -m pytest tests/blueprint2layout/ -v
```
