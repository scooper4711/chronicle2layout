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
| `aspectratio` | string | no | Page aspect ratio (e.g., `"603:783"` for US Letter). Passed through to the output layout. Inherited from parent if not declared. |
| `defaultChronicleLocation` | string | no | Foundry VTT module path to the chronicle PDF. Passed through to the output layout. |
| `parameters` | object | no | Parameter groups matching the LAYOUT_FORMAT.md parameter schema. Merged with parent parameters (child overrides parent). |
| `field_styles` | object | no | Named reusable bundles of styling/positioning properties for fields. Merged with parent styles (child overrides parent). |
| `fields` | array | no | Ordered array of field entries that bind parameters to positioned regions. |
| `canvases` | array | yes | Ordered array of canvas entries. |

Properties `id`, `parent`, `description`, `flags`, `aspectratio`, and `defaultChronicleLocation` are pass-through: they appear in the output layout exactly as written in the Blueprint.

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

### Secondary axis reference

A string of the form `category[index].edge` that resolves to a detected element's secondary axis position.

```json
"left": "h_rule[0].left",
"right": "h_rule[0].right",
"top": "v_thin[1].top"
```

Horizontal lines support `.left` (x position) and `.right` (x2 position). Vertical lines support `.top` (y position) and `.bottom` (y2 position). Grey boxes support all four edges.

| Category | Valid secondary edges |
|----------|---------------------|
| `h_thin`, `h_bar`, `h_rule` | `.left` → x, `.right` → x2 |
| `v_thin`, `v_bar` | `.top` → y, `.bottom` → y2 |
| `grey_box` | `.left` → x, `.right` → x2, `.top` → y, `.bottom` → y2 |

### Canvas-scoped reference (`@` prefix)

A string prefixed with `@` that uses canvas-local indexing instead of global indexing. Only available on field edge values (not canvas edge values).

```json
"bottom": "@h_rule[0]",
"left": "@h_rule[0].left",
"right": "@grey_box[1].right"
```

When a field references `@h_rule[0]`, the tool filters the detection result to only elements that fall within the field's canvas bounds (both x and y overlap), then uses index 0 within that filtered set. This means `@h_rule[0]` in one canvas may refer to a completely different global element than `@h_rule[0]` in another canvas.

This is useful when the same type of structural element appears many times across the page but you only care about the ones in your canvas. Without `@`, you'd need to count through all elements globally to find the right index.

The `@` prefix works with plain line references, secondary axis references, and em offset expressions:

```json
"bottom": "@h_rule[0]",
"left": "@h_rule[0].left",
"top": "@h_rule[0] - 1em"
```

### Em offset expression (fields only)

A string of the form `"<base_ref> +/- <N>em"` that offsets a resolved position by N times the field's font size. Only available on field edge values.

```json
"top": "@h_rule[0] - 1em",
"left": "@h_rule[2].left + 1em"
```

The offset is computed as: `offset_percentage = N × fontsize / page_dimension × 100`, where `page_dimension` is the page height (from `aspectratio`) for top/bottom edges and the page width for left/right edges.

The base reference can be any valid edge value type: line reference, secondary axis reference, canvas reference, or canvas-scoped reference.

## Parameters

The optional `parameters` property declares user-fillable fields using the same schema as LAYOUT_FORMAT.md parameters. Parameters are passed through to the output layout's `parameters` section.

```json
"parameters": {
  "Event Info": {
    "event": { "type": "text", "description": "Event name", "example": "PaizoCon" },
    "date": { "type": "text", "description": "Session date", "example": "27.06.2020" }
  },
  "Player Info": {
    "char": { "type": "text", "description": "Character name", "example": "Stormageddon" }
  }
}
```

When a child Blueprint has a parent with parameters, they are merged: groups from both are included, and within shared groups, the child's parameter definitions override the parent's.

## Field Styles

The optional `field_styles` property defines reusable bundles of styling and positioning properties that fields can reference.

```json
"field_styles": {
  "defaultfont": {
    "font": "Helvetica",
    "fontsize": 14
  },
  "player_infoline": {
    "styles": ["defaultfont"],
    "canvas": "main",
    "align": "CM"
  }
}
```

Styles can reference other styles via their own `styles` array, forming a composition chain. Resolution is depth-first: base styles are applied first, then more specific styles, then the field's own direct properties. Circular references are detected and raise an error.

Style properties that can be inherited: `canvas`, `type`, `font`, `fontsize`, `fontweight`, `align`, `color`, `linewidth`, `size`, `lines`, `left`, `right`, `top`, `bottom`.

Field styles inherit from parent Blueprints: a child's `field_styles` are merged with the parent's, with child definitions overriding parent definitions for the same style name.

## Field Entries

The optional `fields` property is an ordered array of field entries. Each field binds a parameter (or static value) to a positioned region within a canvas.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | yes | Unique field name within the Blueprint (including inherited fields) |
| `canvas` | string | after styles | Canvas this field renders in. May be inherited from a style. |
| `type` | string | after styles | Element type: `text`, `multiline`, `line`, or `rectangle`. May be inherited from a style. |
| `param` | string | no | Parameter name this field renders. Output value becomes `"param:<name>"`. |
| `value` | string | no | Static text value. Mutually exclusive with `param`. |
| `styles` | string[] | no | List of field style names to inherit properties from. |
| `trigger` | string | no | Wraps the output element in a trigger for conditional rendering. |
| `left` | edge value | no | Left edge. Supports all edge value types including `@` and em offsets. |
| `right` | edge value | no | Right edge. |
| `top` | edge value | no | Top edge. Defaults to `bottom - 1em` when omitted (requires `bottom` and `fontsize`). |
| `bottom` | edge value | no | Bottom edge. |
| `font` | string | no | Font family. |
| `fontsize` | number | no | Font size in points. |
| `fontweight` | string | no | Font weight (e.g., `"bold"`). |
| `align` | string | no | Alignment code (e.g., `"CM"`, `"LB"`). |
| `color` | string | no | Color for line/rectangle elements. |
| `linewidth` | number | no | Line width for line elements. |
| `size` | number | no | Size for checkbox-like elements. |
| `lines` | number | no | Number of lines for multiline elements. |

### Top edge default

When a field omits `top` but has both `bottom` and an effective `fontsize` (from direct property or styles), the tool computes `top = bottom - 1em`. This is convenient for single-line text fields that sit just above a structural line.

### Field output

Each field produces a content element in the output layout with all properties inlined (no presets). Fields with a `trigger` property are wrapped in a trigger element. Content elements appear in the same order as the fields array.

### Field bounds validation

After resolving a field's edges, the tool validates that all edges fall within the field's canvas bounds. If any edge is outside the canvas, a descriptive error is raised listing the elements of the referenced type that do fall within the canvas — helping you find the correct index.

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
6. Parameters are merged through the chain (child overrides parent at the individual parameter level within groups).
7. Field styles are merged through the chain (child definitions override parent for the same style name).
8. Field names must be unique across the chain (a child cannot redefine a parent's field name).
9. The `aspectratio` is inherited from the nearest ancestor that declares it.
10. Only the child's own fields produce content elements in the output.

## Resolution Order

Canvases resolve strictly in array order. When resolving canvas N:
- Numeric literals are used directly.
- Line references look up the detected element by category and index.
- Canvas references can only refer to canvases 0 through N-1 (plus any inherited canvases).

This makes resolution deterministic and cycle-free without needing a dependency graph.

## Output

The tool produces a layout.json conforming to [LAYOUT_FORMAT.md](LAYOUT_FORMAT.md). Output sections appear in this order: `id`, `parent`, `description`, `flags`, `aspectratio`, `defaultChronicleLocation`, `parameters`, `canvas`, `content`. Sections with no value are omitted.

Canvas coordinates are parent-relative percentages (0–100 relative to the parent canvas), rounded to one decimal place. Field coordinates are similarly parent-relative within their canvas.

When a Blueprint defines no fields, the output contains only the sections it would have produced before fields were added (backward compatible).

### Detection enhancements

The tool also extracts thin vector lines directly from the PDF's drawing commands. Lines with a stroke width ≤ 1pt that are too thin to survive rasterization at 150 DPI are added to the `h_rule` category. This ensures that fine structural lines (like field separators) are available for referencing even when they're invisible in the raster image.

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

## Full Example with Fields

A Blueprint with parameters, field styles, and fields:

```json
{
  "id": "pfs2.b1",
  "parent": "pfs2",
  "description": "#B1: The Whitefang Wyrm",
  "parameters": {
    "Event Info": {
      "event": { "type": "text", "description": "Event name", "example": "PaizoCon" }
    },
    "Player Info": {
      "char": { "type": "text", "description": "Character name", "example": "Stormageddon" }
    }
  },
  "field_styles": {
    "defaultfont": { "font": "Helvetica", "fontsize": 14 }
  },
  "fields": [
    {
      "name": "event",
      "param": "event",
      "type": "text",
      "canvas": "session_info",
      "styles": ["defaultfont"],
      "align": "LB",
      "left": "@h_rule[0].left",
      "right": "@h_rule[0].right",
      "bottom": "@h_rule[0]"
    },
    {
      "name": "xp_gained",
      "param": "xp_gained",
      "type": "text",
      "canvas": "rewards",
      "styles": ["defaultfont"],
      "align": "CM",
      "left": "@grey_box[0].left",
      "right": "@grey_box[0].right",
      "top": "@grey_box[0].bottom",
      "bottom": "@grey_box[1].top"
    }
  ],
  "canvases": [
    { "name": "main", "parent": "page", "left": "v_bar[0]", "right": "v_thin[2]", "top": "h_thin[2]", "bottom": "h_thin[8]" },
    { "name": "session_info", "parent": "main", "left": "main.left", "right": "main.right", "top": "notes.bottom", "bottom": "main.bottom" },
    { "name": "rewards", "parent": "main", "left": "v_bar[1]", "right": "main.right", "top": "h_bar[1]", "bottom": "h_thin[7]" }
  ]
}
```

The `event` field uses `@h_rule[0]` — the first grey rule within the `session_info` canvas — as its bottom edge, with the top auto-computed as 1em above. The `xp_gained` field fills the white space between two grey box labels in the rewards area.
