# Blueprint File Format

## Philosophy

Layout files (see [LAYOUT_FORMAT.md](LAYOUT_FORMAT.md)) use hard-coded percentage coordinates for every canvas region. When a new chronicle sheet is released, an author must open the PDF, measure pixel positions, convert them to percentages, and type them into a JSON file. This is tedious, error-prone, and produces coordinates that are difficult to verify by reading the file alone.

Blueprints take a different approach: instead of hard-coding coordinates, the author declares which structural lines on the PDF define each canvas edge. The `blueprint2layout` tool detects those lines automatically by analyzing the PDF's pixel content, then resolves the references to produce the same percentage-based layout file.

This means a Blueprint like:

```json
{
  "name": "summary",
  "parent": "main",
  "left": "main.left",
  "right": "main.right",
  "top": "h_bar[0]",
  "bottom": "h_bar[1]"
}
```

reads as: "summary spans the full width of main, from the first thick horizontal bar to the second." The author doesn't need to know that `h_bar[0]` is at 19.9% — the tool figures that out from the PDF.

### Key principles

- Blueprints are declarative. They describe structure, not coordinates.
- Blueprints reference detected elements by category and index, making them readable and auditable.
- Blueprints support inheritance, so common definitions (like `page`) are written once.
- The output is a standard layout.json — downstream consumers don't know or care that it came from a Blueprint.

## File Convention

Blueprint files use the `.blueprint.json` extension to distinguish them from layout `.json` files. They are valid JSON and can be edited in any JSON-aware editor.

## Root Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | string | yes | Unique identifier, matching the layout inheritance scheme (e.g., `"pfs2"`, `"pfs2.b1"`) |
| `parent` | string | no | Id of the parent Blueprint. The parent's canvases are resolved first and available for canvas references. |
| `description` | string | no | Human-readable description. Passed through to the output layout. |
| `flags` | string[] | no | Metadata flags (e.g., `["hidden"]`). Passed through to the output layout. |
| `aspectratio` | string | no | Page aspect ratio (e.g., `"603:783"` for US Letter). Passed through to the output layout. |
| `canvases` | array | yes | Ordered array of canvas entries. |

Properties `id`, `parent`, `description`, `flags`, and `aspectratio` are pass-through: they appear in the output layout exactly as written in the Blueprint.

## Canvas Entries

Each entry in the `canvases` array defines a rectangular region on the chronicle page.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | yes | Unique canvas name (e.g., `"main"`, `"summary"`) |
| `parent` | string | no | Parent canvas name. Output coordinates will be relative to this canvas. |
| `left` | edge value | yes | Left edge position |
| `right` | edge value | yes | Right edge position |
| `top` | edge value | yes | Top edge position |
| `bottom` | edge value | yes | Bottom edge position |

## Edge Values

Each edge can be one of three types:

### Numeric literal

A number (int or float) representing an absolute page percentage.

```json
"left": 0,
"right": 100,
"top": 5.9
```

Used for fixed positions like the `page` canvas (`0` to `100`).

### Line reference

A string of the form `category[index]` that resolves to a detected structural line's position on its primary axis.

```json
"top": "h_bar[0]",
"left": "v_thin[2]"
```

The tool scans the chronicle PDF and detects six categories of structural elements:

| Category | What it detects | Sorted by | Resolves to |
|----------|----------------|-----------|-------------|
| `h_thin` | Horizontal thin lines (≤ 5px at 150 DPI) | y ascending | y position |
| `h_bar` | Horizontal thick bars (> 5px) | y ascending | y position |
| `h_rule` | Grey horizontal rules (grayscale 50–200) | y ascending | y position |
| `v_thin` | Vertical thin lines (≤ 5px) | x ascending | x position |
| `v_bar` | Vertical thick bars (> 5px) | x ascending | x position |
| `grey_box` | Grey filled rectangles (RGB 220–240) | y then x | not used as line reference |

Indices are zero-based. `h_bar[0]` is the first (topmost) thick horizontal bar. `v_thin[2]` is the third vertical thin line from the left.

### Canvas reference

A string of the form `canvas_name.edge` that resolves to an already-defined canvas's edge value.

```json
"left": "main.left",
"top": "summary.bottom",
"right": "rewards.left"
```

Valid edges are `left`, `right`, `top`, and `bottom`. The referenced canvas must appear earlier in the array (or be inherited from a parent Blueprint). Forward references are not allowed.

## Inheritance

Blueprints form a parent chain via the `parent` property, mirroring the layout inheritance model.

```
pfs2                          Root: defines page, aspectratio
├── pfs2.b1                   Bounties B1-B12: defines main + canvases
├── pfs2.b13                  Bounties B13+: different layout structure
└── pfs2.q14                  Quests Q14+: yet another structure
```

When a Blueprint has a parent:
1. The parent chain is resolved recursively (grandparent first, then parent).
2. All parent canvases are resolved before the child's canvases.
3. Child canvases can reference parent canvases via canvas references.
4. Only the child's own canvases appear in the output layout — parent canvases are resolved for reference but not emitted.
5. Canvas names must be unique across the entire inheritance chain.

## Resolution Order

Canvases resolve strictly in array order. When resolving canvas N:
- Numeric literals are used directly.
- Line references look up the detected element by category and index.
- Canvas references can only refer to canvases 0 through N-1 (plus any inherited canvases).

This makes resolution deterministic and cycle-free without needing a dependency graph.

## Output

The tool produces a layout.json conforming to [LAYOUT_FORMAT.md](LAYOUT_FORMAT.md). Canvas coordinates in the output are parent-relative percentages (0–100 relative to the parent canvas), rounded to one decimal place.

## Example

Given this root Blueprint:

```json
{
  "id": "pfs2",
  "description": "Pathfinder 2 Society Chronicle",
  "aspectratio": "603:783",
  "canvases": [
    { "name": "page", "left": 0, "right": 100, "top": 0, "bottom": 100 }
  ]
}
```

And this child Blueprint:

```json
{
  "id": "pfs2.b1",
  "parent": "pfs2",
  "description": "#B1: The Whitefang Wyrm",
  "canvases": [
    {
      "name": "main", "parent": "page",
      "left": "v_bar[0]", "right": "v_thin[2]",
      "top": "h_thin[2]", "bottom": "h_thin[8]"
    },
    {
      "name": "summary", "parent": "main",
      "left": "main.left", "right": "main.right",
      "top": "h_bar[0]", "bottom": "h_bar[1]"
    }
  ]
}
```

Running `python -m blueprint2layout b1.blueprint.json chronicle.pdf output.json` produces:

```json
{
  "id": "pfs2.b1",
  "parent": "pfs2",
  "description": "#B1: The Whitefang Wyrm",
  "canvas": {
    "main": { "x": 6.1, "y": 11.3, "x2": 93.9, "y2": 95.3, "parent": "page" },
    "summary": { "x": 0.0, "y": 6.4, "x2": 100.0, "y2": 30.4, "parent": "main" }
  }
}
```

The `page` canvas from the parent Blueprint is not in the output — it was resolved internally so that `main` could compute its parent-relative coordinates.
