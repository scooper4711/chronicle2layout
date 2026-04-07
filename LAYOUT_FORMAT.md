# Layout File Format

Layout files are JSON documents that describe the structure and content of a PFS2 chronicle sheet. They use an inheritance model where scenario-specific layouts override properties from season-level base layouts, which in turn inherit from the root `pfs2` layout.

## Inheritance

Every layout can declare a `parent`. A child inherits all properties from its parent and can override or extend them. The chain always starts at `pfs2.json`, which defines the page aspect ratio, shared parameters, and the `page` canvas.

```
pfs2                                  Root (aspect ratio, shared parameters, page canvas)
├── season1-layout-s1-00              Season 1 base (may have variants: s1-15, s1-16, …)
│   ├── pfs2.s1-00                    Scenario override
│   └── ...
├── season4-layout-s4-00              Season 4 base (variants: s4-02, s4-04, s4-06, s4-07)
│   ├── pfs2.s4-01                    Scenario override
│   └── ...
├── season7-layout-s7-00              Season 7 base
│   ├── pfs2.s7-01                    Scenario override
│   └── ...
├── bounty-layout-b1                  Bounty base (variants: b1, b13)
│   ├── pfs2.b1                       Bounty override
│   └── ...
└── ...
```

A season may have multiple base layouts when the underlying PDF chronicle sheets changed layout between scenario groups within the season. For example, Season 1 has `s1-00`, `s1-15`, `s1-16`, etc., and Season 4 has `s4-00`, `s4-02`, `s4-04`, `s4-06`, `s4-07`. Each scenario points to whichever base matches its PDF.

Base layouts use `"flags": ["hidden"]` so they don't appear in the UI directly.

## File Organization

Layouts live under `modules/pfs-chronicle-generator/assets/layouts/pfs2/`, organized by category:

```
pfs2/
├── pfs2.json                         Root layout
├── season1/
│   ├── season1-layout-s1-00.json     Base layout(s)
│   ├── season1-layout-s1-15.json
│   ├── pfs2.s1-00.json               Scenario layouts
│   ├── pfs2.s1-01.json
│   └── ...
├── season7/
│   ├── season7-layout-s7-00.json
│   ├── pfs2.s7-01.json
│   └── ...
├── bounties/
│   ├── bounty-layout-b1.json
│   ├── pfs2.b1.json
│   └── ...
└── quests/
    └── ...
```

## Root Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | string | Unique identifier (e.g. `"pfs2.s7-01"`) |
| `description` | string | Human-readable name (e.g. `"7-01 Enough is Enough"`) |
| `parent` | string | ID of the parent layout to inherit from |
| `flags` | string[] | Metadata flags. `"hidden"` hides the layout from the UI |
| `aspectratio` | string | Page aspect ratio (e.g. `"603:783"`). Set on the root layout |
| `defaultChronicleLocation` | string | Path to the PDF chronicle file within the Foundry VTT module |

## Parameters

Parameters define the user-fillable fields on the chronicle sheet, organized into named groups.

```json
"parameters": {
  "Group Name": {
    "param_name": {
      "type": "text",
      "description": "Human-readable description",
      "example": "Example value"
    }
  }
}
```

### Parameter Types

| Type | Description | Extra Properties |
|------|-------------|-----------------|
| `text` | Single-line text input | — |
| `multiline` | Multi-line text input | `lines`: number of lines |
| `choice` | Selectable options | `choices`: array of values |
| `societyid` | PFS Society ID (e.g. `"123456-2001"`) | Parsed into sub-fields |

### Standard Parameter Groups

The root `pfs2` layout defines these groups, inherited by all seasons:

| Group | Parameters |
|-------|-----------|
| Event Info | `event`, `eventcode`, `date`, `gmid` |
| Player Info | `char`, `societyid` |
| Rewards | `starting_xp`, `xp_gained`, `total_xp`, `starting_gp`, `treasure_bundles_gp`, `income_earned`, `gp_gained`, `gp_spent`, `total_gp` |
| Checkboxes, Reputation and Items | `summary_checkbox`, `reputation`, `strikeout_item_lines` |
| Notes | `notes` |

Season base layouts may extend Player Info with `char_number` and `char_number_short` fields. Scenario layouts typically add an `Items` group that overrides `strikeout_item_lines` with scenario-specific text-based choices.

## Canvas

Canvas regions define rectangular areas on the PDF page. Coordinates are percentages (0–100) relative to the parent canvas.

```json
"canvas": {
  "page": { "x": 0.0, "y": 0.0, "x2": 100.0, "y2": 100.0 },
  "main": { "parent": "page", "x": 6.1, "y": 11.3, "x2": 93.9, "y2": 95.3 },
  "items": { "parent": "main", "x": 2.4, "y": 44.3, "x2": 32.1, "y2": 83.0 }
}
```

| Property | Description |
|----------|-------------|
| `parent` | Name of the parent canvas (defaults to `page`) |
| `x`, `y` | Top-left corner as percentage of parent |
| `x2`, `y2` | Bottom-right corner as percentage of parent |

Common canvas regions across seasons include `page`, `main`, `character_info`, `reputation`, `summary`, `items`, `rewards`, `notes`, and `session_info`. The exact set and coordinates vary by season base layout.

## Presets

Presets are reusable property bundles applied to content elements. They reduce repetition by defining common styling and positioning once.

```json
"presets": {
  "defaultfont": {
    "font": "Helvetica",
    "fontsize": 14
  },
  "strikeout_item": {
    "canvas": "items",
    "color": "black",
    "x": 0.5,
    "x2": 95
  },
  "item.line.bag_of_holding_type_II_level_7;_300_gp": {
    "y": 3.1,
    "y2": 7.1
  }
}
```

Supported preset properties: `presets` (compose other presets), `canvas`, `font`, `fontsize`, `fontweight`, `align`, `x`, `y`, `x2`, `y2`, `color`, `linewidth`, `size`, `lines`, `dummy`.

Presets can inherit from other presets via the `presets` array. A preset with `"dummy": 0` is a placeholder intended to be overridden by a child layout.

### Alignment Codes

Two-character string: horizontal + vertical position.

| Horizontal | Vertical |
|-----------|----------|
| `L` (left) | `T` (top) |
| `C` (center) | `M` (middle) |
| `R` (right) | `B` (bottom) |

Examples: `"LB"` = left-bottom, `"CM"` = center-middle.

## Content

Content is an ordered array of elements to draw on the PDF.

```json
"content": [
  {
    "value": "param:char",
    "type": "text",
    "canvas": "character_info",
    "x": 35.9, "y": 31.5, "x2": 64.0, "y2": 52.3,
    "font": "Helvetica",
    "fontsize": 14,
    "fontweight": "bold",
    "align": "LB"
  }
]
```

### Element Types

| Type | Description |
|------|-------------|
| `text` | Single line of text |
| `multiline` | Multiple lines of text (uses `lines` property) |
| `trigger` | Conditional wrapper — renders its `content` array only if the `trigger` parameter has a value |
| `choice` | Conditional branching — `choices` references a parameter, `content` maps choice values to content arrays |
| `strikeout` | Visual strikethrough mark (used for item lines and checkboxes) |
| `checkbox` | Checkbox mark at specific coordinates |
| `line` | Horizontal line |
| `rectangle` | Filled rectangle |

### Content Element Properties

Each element can use: `type`, `value` (use `"param:name"` to reference a parameter), `presets`, `canvas`, `x`, `y`, `x2`, `y2`, `font`, `fontsize`, `fontweight`, `align`, `color`, `linewidth`.

## How Seasons Are Structured

### Season Base Layout

A season base layout inherits from `pfs2`, is flagged `"hidden"`, and defines the full structure shared by all scenarios in that season (or scenario group): parameters, canvas regions, presets, and content elements for placing fields on the PDF.

Example (Season 7 base — `season7-layout-s7-00.json`):

```json
{
  "id": "pfs2.season7-layout-s7-00",
  "parent": "pfs2",
  "description": "Layout for Season 7 Chronicles",
  "flags": ["hidden"],
  "defaultChronicleLocation": "...",
  "parameters": { ... },
  "canvas": { ... },
  "content": [ ... ]
}
```

When the PDF layout changes mid-season, multiple base layouts exist. Each covers a group of scenarios that share the same PDF structure. For example, Season 4 has five base variants (`s4-00`, `s4-02`, `s4-04`, `s4-06`, `s4-07`), each with different canvas coordinates matching different PDF layouts.

### Scenario Layout

A scenario layout inherits from its season base and overrides only what's scenario-specific. Many scenarios are minimal — just an `id`, `parent`, `description`, and `defaultChronicleLocation`:

```json
{
  "id": "pfs2.s7-01",
  "parent": "pfs2.season7-layout-s7-00",
  "description": "7-01 Enough is Enough",
  "defaultChronicleLocation": "modules/pfs-chronicle-generator/assets/chronicles/pfs2/season7/7-01-EnoughisEnoughChronicle.pdf"
}
```

Scenarios that have purchasable items add an `Items` parameter group with text-based choices, presets for each item line's position, and content elements that map choices to strikeouts:

```json
{
  "id": "pfs2.s1-02",
  "parent": "pfs2.season1-layout-s1-00",
  "description": "1-02 The Mosquito Witch",
  "defaultChronicleLocation": "...",
  "parameters": {
    "Items": {
      "strikeout_item_lines": {
        "type": "choice",
        "description": "Item line text to be struck out",
        "choices": [
          "potion of invisibility (level 4; 20 gp)",
          "animal staff (level 4; 90 gp)"
        ]
      }
    }
  },
  "presets": {
    "strikeout_item": { "canvas": "items", "color": "black", "x": 0.5, "x2": 95 },
    "item.line.potion_of_invisibility_level_4;_20_gp": { "y": 55.4, "y2": 58.9 },
    "item.line.animal_staff_level_4;_90_gp": { "y": 60.1, "y2": 63.6 }
  },
  "content": [
    {
      "type": "choice",
      "choices": "param:strikeout_item_lines",
      "content": {
        "potion of invisibility (level 4; 20 gp)": [
          { "type": "strikeout", "presets": ["strikeout_item", "item.line.potion_of_invisibility_level_4;_20_gp"] }
        ],
        "animal staff (level 4; 90 gp)": [
          { "type": "strikeout", "presets": ["strikeout_item", "item.line.animal_staff_level_4;_90_gp"] }
        ]
      }
    }
  ]
}
```

### Item Line Preset Naming

Preset names for text-based item choices are derived from the choice text: spaces and special characters become underscores, truncated to ~55 characters, prefixed with `item.line.`.

### Bounties and Quests

Bounties and quests follow the same pattern — a hidden base layout per PDF format, with individual scenario files inheriting from it. They live in their own subdirectories (`bounties/`, `quests/`).
