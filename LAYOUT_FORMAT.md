# Layout File Format

Layout files are JSON documents that describe the structure and content of a chronicle sheet. They use an inheritance model where scenario-specific layouts override properties from season-level base layouts, which in turn inherit from format-level layouts.

## File Format

All layout files in this project are JSON (`.json`).

## Inheritance Hierarchy

Layouts form a parent-child chain using the `parent` property. Each child inherits all properties from its parent and can override or extend them.

```
pfs2                              Root layout (aspect ratio only)
├── pfs2.layout1                  Format v1 (Season 1, early Season 2)
│   ├── pfs2.season1              Season 1 wrapper
│   │   ├── pfs2.s1-01           Scenario overrides
│   │   └── ...
│   └── pfs2.s2.oldLayout        Season 2 old-format wrapper
│       ├── pfs2.s2-01           Early S2 scenarios
│       └── ...
├── pfs2.layout2                  Format v2 (late Season 2)
│   └── pfs2.season2              Season 2 new-format wrapper
│       ├── pfs2.s2-05           Later S2 scenarios
│       └── ...
├── pfs2.layout3                  Format v3 (Season 3)
│   └── pfs2.season3              Season 3 wrapper
│       ├── pfs2.s3-01           Scenario overrides
│       └── ...
├── pfs2.season4a/b/c/d/e        Season 4 bases (5 PDF variants)
│   ├── pfs2.s4-01               Scenario overrides
│   └── ...
├── pfs2.season5                  Season 5 base
│   ├── pfs2.s5-01               Scenario overrides
│   └── ...
├── pfs2.season6                  Season 6 base
│   ├── pfs2.s6-01               Scenario overrides
│   └── ...
└── pfs2.season7                  Season 7 base
    ├── pfs2.s7-01               Scenario overrides
    └── ...
```

Season base layouts (e.g., `Season 5.json`) define the shared structure for all scenarios in that season: parameters, canvas regions, presets, and content. Individual scenario files only override what differs from the season base.

## Root Properties

- `id` (string, required): Unique identifier for the layout (e.g., `"pfs2.s7-01"`).
- `description` (string, required): Human-readable description.
- `parent` (string, optional): ID of the parent layout to inherit from.
- `flags` (array of strings, optional): Metadata flags. `"hidden"` prevents the layout from appearing in the UI directly (used for base/template layouts).
- `aspectratio` (string, optional): Aspect ratio of the PDF page (e.g., `"603:783"`).
- `defaultChronicleLocation` (string, optional): Path to the PDF chronicle file within the Foundry VTT module. Used by scenario layouts to locate the source PDF.

## `parameters`

Parameters define the user-fillable fields on the chronicle sheet. They are organized into named groups.

```json
"parameters": {
  "Group Name": {
    "param_name": {
      "type": "text|multiline|choice|societyid",
      "description": "Human-readable description",
      "example": "Example value"
    }
  }
}
```

### Parameter Types

- `text`: Single-line text input.
- `multiline`: Multi-line text input. Requires a `lines` property specifying the number of lines.
- `choice`: A set of selectable options. Requires a `choices` array. Choices can be numeric indices (e.g., `[1, 2, 3]`) or descriptive text strings (see below).
- `societyid`: A specialized type for Pathfinder Society IDs (e.g., `"123456-2001"`). Automatically parsed into sub-fields: `societyid.player`, `societyid.char`, and `societyid.char_without_first_digit`.

### Parameter Groups

Season 5+ layouts use these standard groups:

| Group | Parameters |
|-------|-----------|
| Event Info | `event`, `eventcode`, `date`, `gmid` |
| Player Info | `char`, `societyid` |
| Rewards | `starting_xp`, `xp_gained`, `total_xp`, `starting_gp`, `treasure_bundles_gp`, `income_earned`, `gp_gained`, `gp_spent`, `total_gp` |
| Checkboxes, Reputation and Items | `summary_checkbox`, `reputation`, `strikeout_item_lines` |
| Notes | `notes` |

Scenario layouts add their own parameter groups (typically `Items` and `Checkboxes`) that override the season base definitions with scenario-specific choices.

## `canvas`

Canvas regions define rectangular areas on the PDF page where content is drawn. Coordinates are percentages (0-100) relative to the parent canvas.

```json
"canvas": {
  "page": { "x": 0.0, "y": 0.0, "x2": 100.0, "y2": 100.0 },
  "main": { "parent": "page", "x": 6.2, "y": 10.5, "x2": 94.0, "y2": 95.4 },
  "rightbar": { "parent": "main", "x": 82.2, "y": 33, "x2": 99.8, "y2": 83 },
  "summary": { "parent": "main", "x": 0, "x2": 100, "y": 9, "y2": 31 },
  "items": { "parent": "main", "x": 0.5, "y": 50.8, "x2": 40, "y2": 83 },
  "notes": { "parent": "main", "x": 42, "y": 50.8, "x2": 77, "y2": 81.5 },
  "reputation": { "parent": "main", "x": 0.2, "y": 85.1, "x2": 99.8, "y2": 93.2 }
}
```

### Canvas Properties

- `parent` (string, optional): Name of the parent canvas. Coordinates are relative to this canvas. Defaults to the page.
- `x`, `y` (number): Top-left corner as percentage of parent.
- `x2`, `y2` (number): Bottom-right corner as percentage of parent.

### Standard Canvas Regions (Seasons 5-7)

| Canvas | Purpose |
|--------|---------|
| `page` | Full page (always 0-100) |
| `main` | Primary content area within page margins |
| `rightbar` | XP/GP reward fields on the right side |
| `summary` | Adventure summary area with checkboxes |
| `items` | Available items list |
| `notes` | Player notes area |
| `reputation` | Reputation tracking area |

## `presets`

Presets are reusable property bundles that can be applied to content elements. They reduce repetition by defining common styling and positioning once.

```json
"presets": {
  "defaultfont": {
    "font": "Helvetica",
    "fontsize": 14
  },
  "player.infoline": {
    "presets": ["defaultfont"],
    "canvas": "main",
    "y": 1.0,
    "y2": 4.0,
    "align": "CM"
  }
}
```

### Preset Properties

- `presets` (array of strings): Other presets to inherit from (composition).
- `canvas` (string): Which canvas region this preset targets.
- `font` (string): Font family.
- `fontsize` (number): Font size in points.
- `fontweight` (string): Font weight (e.g., `"bold"`).
- `align` (string): Alignment code (see Alignment Codes below).
- `x`, `y`, `x2`, `y2` (number): Position as percentage of the canvas.
- `color` (string): Color for lines and strikeouts.
- `linewidth` (number): Width for line and strikeout elements.
- `size` (number): Size for checkbox elements.
- `lines` (number): Number of lines for multiline elements.
- `dummy` (number): Placeholder property for presets that exist only to be overridden by scenario layouts (commonly `0`).

### Alignment Codes

Alignment is specified as a two-character string: horizontal position + vertical position.

| Character | Horizontal | Vertical |
|-----------|-----------|----------|
| `L` | Left | — |
| `C` | Center | Center |
| `R` | Right | — |
| `B` | — | Bottom |
| `M` | — | Middle |

Examples: `"LB"` = left-bottom, `"CM"` = center-middle, `"RB"` = right-bottom.

## `content`

Content is an array of elements to draw on the PDF. Elements are processed in order.

### Content Element Properties

- `type` (string, required): Element type (see below).
- `value` (string, optional): The value to render. Use `"param:name"` to reference a parameter.
- `presets` (array of strings, optional): Presets to apply.
- `canvas`, `x`, `y`, `x2`, `y2`, `font`, `fontsize`, `fontweight`, `align`, `color`, `linewidth`: Override preset values inline.

### Element Types

- `text`: Single line of text.
- `multiline`: Multiple lines of text. Uses `lines` to specify count.
- `trigger`: Conditional wrapper. Renders its `content` array only if the `trigger` parameter has a value.
- `choice`: Conditional branching based on a parameter value. The `choices` property references a parameter, and `content` is a map of choice values to content arrays.
- `strikeout`: A visual strikethrough mark (used for checkboxes and item lines).
- `checkbox`: A checkbox mark drawn at specific coordinates.
- `line`: A horizontal line (used for separators and item strikeouts).
- `rectangle`: A filled rectangle (used in older formats to mask areas).

## Season 1-4 Layout Structure

Seasons 1 through 4 use three distinct format versions (`layout1`, `layout2`, `layout3`) that evolved as the chronicle sheet design changed. Unlike seasons 5-7, these earlier seasons use a format-level base layout rather than a per-season base.

### Inheritance Model

Seasons 1-4 use an extra layer of indirection: format layouts define the full structure, and thin season wrappers point to them.

```
pfs2
├── pfs2.layout1                    Format v1 (full layout definition)
│   ├── pfs2.s1                     Season 1 wrapper (no overrides)
│   │   ├── pfs2.s1-01             Scenario (checkbox/boon coordinates)
│   │   └── ...
│   └── pfs2.s2.oldLayout          Season 2 old-format wrapper
│       ├── pfs2.s2-01             Early S2 scenarios
│       └── ...
├── pfs2.layout2                    Format v2 (full layout definition)
│   └── pfs2.s2                     Season 2 new-format wrapper
│       ├── pfs2.s2-05             Later S2 scenarios
│       └── ...
├── pfs2.layout3                    Format v3 (full layout definition)
│   └── pfs2.s3                     Season 3 wrapper (no overrides)
│       ├── pfs2.s3-01             Scenario (minimal or no overrides)
│       └── ...
└── pfs2.season4a/b/c/d/e          Season 4 bases (multiple variants)
    ├── pfs2.s4-01                  Scenario (text-based items)
    └── ...
```

Season wrappers (e.g., `s1.json`, `s2.newLayout.json`, `s3.json`) are typically just an `id`, `description`, and `parent` — they add no new properties. The format layouts (`layout1`, `layout2`, `layout3`) contain the full definitions.

### Season 2: Dual Layout Transition

Season 2 straddles two formats. Early scenarios (e.g., 2-01 through 2-04) use the v1 format via `pfs2.s2.oldLayout`, while later scenarios use the v2 format via `pfs2.s2`. The old layout wrapper also includes a `displayparent` property to group both under the same season in the UI.

```json
{
  "id": "pfs2.s2.oldLayout",
  "parent": "pfs2.layout1",
  "displayparent": "pfs2.s2",
  "flags": ["hidden"]
}
```

### Season 4: Multiple Base Variants

Season 4 is unique in having five separate base layouts (`Season4a.json` through `Season4e.json`), each covering different groups of scenarios. This was necessary because the underlying PDF chronicle sheets changed layout between scenario groups within the season. Each variant inherits directly from `pfs2` (not from a format layout) and defines its own canvas coordinates.

| Base Layout | Scenarios | Notes |
|-------------|-----------|-------|
| `pfs2.season4a` | 4-01, 4-02, 4-03, 4-08 | Larger boons area |
| `pfs2.season4b` | 4-04, 4-05 | Different boons/items split |
| `pfs2.season4c` | 4-06 | Single scenario, unique layout |
| `pfs2.season4d` | 4-07 | Single scenario, unique layout |
| `pfs2.season4e` | 4-09 through 4-17 | Most common S4 layout |

Despite the multiple bases, all Season 4 variants share the same parameter structure (matching the Season 5+ simplified set: Event Info, Player Info, Rewards, Reputation, Notes) and use text-based item choices — making Season 4 a transitional season between the old and new approaches.

### Format v1 (Season 1) — `layout1`

The most complex format, with the richest set of parameters and content areas.

#### Parameter Groups

| Group | Parameters |
|-------|-----------|
| Event Info | `event`, `eventcode`, `date`, `gm`, `gmid` |
| Player Info | `player`, `char`, `societyid`, `chronicle_nr` |
| Factions | `fac1_name`, `fac1_rep_gained`, `fac1_rep_total`, `fac2_*`, `fac3_*` |
| Boons, Items and Selections | `tier`, `summary_checkbox`, `strikeout_boons`, `strikeout_item_lines` |
| Rewards | `starting_xp`, `xp`, `final_xp`, `starting_gp`, `gp`, `income`, `items_sold`, `gp_spent`, `total_gp`, `starting_fame`, `fame`, `total_fame` |
| Items Sold / Conditions Gained | `list_items_sold`, `list_items_sold_price`, `items_sold_total_value` |
| Items Bought / Conditions Cleared | `list_items_bought`, `list_items_bought_price`, `items_bought_total_cost` |
| Notes | `notes` |
| Downtime | `downtime` |

#### Canvas Regions

| Canvas | Purpose |
|--------|---------|
| `page` | Full page |
| `main` | Primary content area |
| `rightbar` | XP/GP/Fame reward fields |
| `middlebox` | Container for items, sold, and bought sections |
| `items` | Available items list (inside middlebox) |
| `items_sold` | Items sold section (inside middlebox) |
| `items_bought` | Items bought section (inside middlebox) |
| `commentbox` | Notes and downtime area |

#### Key Features

- Tier-based items: A `tier` choice parameter (`"low"` / `"high"`) controls which item section is active. The inactive tier's area is struck out, and item strikeouts use tier-prefixed presets (`item.low.1`, `item.high.1`).
- Boon strikeouts: Up to 3 boons can be struck out, each with two strikeout lines (`boon.1`, `boon.1.2`).
- Faction tracking: Three rows of faction name, gained reputation, and total reputation.
- Fame tracking: Starting fame, gained fame, and total fame in the rightbar.
- Numeric checkbox/item indices: Checkboxes and items use numeric keys (`1`, `2`, `3`...).
- Nested choices: Item strikeouts are nested inside the tier choice, so the correct tier's items are struck out.

#### Scenario Overrides (Season 1)

Season 1 scenarios override preset coordinates for checkboxes and boons, and may add custom parameters:

```json
{
  "id": "pfs2.s1-01",
  "parent": "pfs2.s1",
  "parameters": {
    "Boons, Items and Selections": {
      "boon.societyconnections.task_level": {
        "type": "text",
        "description": "Task level for the \"Society Connections\" boon"
      }
    }
  },
  "presets": {
    "checkbox.1": { "x": 60.3, "y": 19.2 },
    "checkbox.2": { "x": 66.9, "y": 19.2 },
    "boon.1": { "x": 1.0, "y": 28.5, "x2": 79.0, "y2": 34.0 },
    "boon.2": { "x": 1.0, "y": 34.1, "x2": 79.0, "y2": 41.5 }
  },
  "content": [
    {
      "value": "param:boon.societyconnections.task_level",
      "type": "text",
      "presets": ["defaultfont"],
      "canvas": "main",
      "fontsize": 10,
      "x": 69.0, "y": 39.3, "x2": 73.3,
      "align": "CB"
    }
  ]
}
```

Checkbox and boon presets use `dummy: 0` in the base layout as placeholders — scenarios provide the actual `x`/`y` coordinates.

### Format v2 (Season 2) — `layout2`

A significant simplification from v1.

#### Parameter Groups

| Group | Parameters |
|-------|-----------|
| Event Info | `event`, `eventcode`, `date`, `gmid` |
| Player Info | `char`, `societyid` |
| Rewards | `xp`, `gp` |
| Checkboxes, Reputation and Items | `summary_checkbox`, `reputation`, `strikeout_item_lines`, `strikeout_keepsake_lines` |
| Items Sold / Conditions Gained | `list_items_sold`, `list_items_sold_price`, `items_sold_total_value` |
| Items Bought / Conditions Cleared | `list_items_bought`, `list_items_bought_price`, `items_bought_total_cost` |
| Notes | `notes` |
| Downtime | `downtime` |

#### What Changed from v1

- Dropped: `player`, `gm`, `chronicle_nr`, all faction fields, all fame fields, `tier`, `strikeout_boons`
- Simplified rewards: Just `xp` and `gp` (no starting/total tracking)
- Added: `strikeout_keepsake_lines` for keepsake items
- Kept: Items sold/bought sections, downtime, numeric indices for checkboxes/items

#### Canvas Regions

| Canvas | Purpose |
|--------|---------|
| `page` | Full page |
| `main` | Primary content area |
| `rightbar` | XP and GP fields (smaller, only 2 values) |
| `items_sold` | Items sold section |
| `items_bought` | Items bought section |
| `commentbox` | Notes and downtime area |

#### Scenario Overrides (Season 2)

Season 2 scenarios using the new layout are minimal — many have no overrides at all, or just provide checkbox coordinates:

```json
{
  "id": "pfs2.s2-10",
  "parent": "pfs2.s2",
  "presets": {
    "checkbox.1": { "x": 18.35, "y": 11.5 },
    "checkbox.2": { "x": 41.1, "y": 11.5 }
  }
}
```

### Format v3 (Seasons 3-4) — `layout3`

Expanded the reward tracking while keeping the items sold/bought structure.

#### Parameter Groups

| Group | Parameters |
|-------|-----------|
| Event Info | `event`, `eventcode`, `date`, `gmid` |
| Player Info | `char`, `societyid` |
| Rewards | `starting_xp`, `xp_gained`, `total_xp`, `starting_gp`, `gp_gained`, `gp_spent`, `total_gp` |
| Checkboxes, Reputation and Items | `summary_checkbox`, `reputation`, `strikeout_item_lines`, `strikeout_keepsake_lines` |
| Items Sold / Conditions Gained | `list_items_sold`, `list_items_sold_price`, `items_sold_total_value` |
| Items Bought / Conditions Cleared | `list_items_bought`, `list_items_bought_price`, `items_bought_total_cost` |
| Notes | `notes` |
| Downtime | `downtime` |

#### What Changed from v2

- Expanded rewards: Added `starting_xp`, `total_xp`, `starting_gp`, `gp_spent`, `total_gp` (renamed `xp` → `xp_gained`, `gp` → `gp_gained`)
- Kept: Items sold/bought, downtime, keepsakes, numeric indices

#### Canvas Regions

| Canvas | Purpose |
|--------|---------|
| `page` | Full page |
| `main` | Primary content area |
| `rightbar` | Full XP/GP reward fields (7 values) |
| `items_sold` | Items sold section |
| `items_bought` | Items bought section |
| `commentbox` | Notes and downtime area |

#### Scenario Overrides (Season 3)

Season 3 scenarios are extremely minimal — most have no overrides at all:

```json
{
  "id": "pfs2.s3-01",
  "description": "#3-01: Intro: Year of Shattered Sanctuaries",
  "parent": "pfs2.s3"
}
```

### Numeric vs Text-Based Choices (Seasons 1-3 vs 4+)

Seasons 1-3 use numeric indices for checkboxes and item strikeouts. The base layout defines placeholder presets (`checkbox.1`, `item.line.1`, etc.) with `dummy: 0`, and each scenario overrides them with actual coordinates:

```json
// Base layout defines placeholders
"checkbox.1": { "dummy": 0 },
"checkbox.2": { "dummy": 0 },
"item.line.1": { "y": 51.7, "y2": 51.7 },

// Scenario provides actual positions
"checkbox.1": { "x": 60.3, "y": 19.2 },
"checkbox.2": { "x": 66.9, "y": 19.2 }
```

Starting with Season 4 scenarios, the text-based choice system was adopted (same as seasons 5-7), where item choices use descriptive text and preset names are derived from that text.

## Season 5-7 Layout Structure

Seasons 5, 6, and 7 share a common architecture that differs significantly from earlier seasons (1-4).

### Season Base Layouts

Each season has a base layout file (`Season 5.json`, `Season 6.json`, `Season 7.json`) that inherits from `pfs2` and defines:

1. All standard parameters (Event Info, Player Info, Rewards, Notes, Reputation)
2. Canvas regions for the chronicle sheet
3. Presets for fonts, positioning, checkboxes, item strikeouts
4. Content elements for all shared fields (character name, society ID, XP/GP fields, event info, reputation, notes)

Season 6 and 7 base layouts are structurally identical. Season 5 is similar but lacks the `summary_checkbox` and `strikeout_item_lines` choice parameters in its base — those are defined only at the scenario level.

### Scenario Layouts

Individual scenario files (e.g., `5-08-ProtectingTheFirelight.json`) inherit from their season base and override only what's scenario-specific:

- `defaultChronicleLocation`: Path to the scenario's PDF file.
- `parameters`: Scenario-specific items and checkboxes with descriptive text choices.
- `presets`: Coordinate positions for each item line and checkbox on the specific PDF.
- `content`: Choice-driven content that maps item/checkbox text to their visual positions.

### Text-Based Choices (Seasons 5-7)

The most significant change from earlier seasons is how items and checkboxes are identified. Earlier formats used numeric indices (`1`, `2`, `3`...) while seasons 5-7 use descriptive text strings as choice keys:

```json
"strikeout_item_lines": {
  "type": "choice",
  "description": "Item line text to be struck out",
  "choices": [
    "minor healing potion (level 1, 4 gp)",
    "silver salve (level 2, 6 gp)",
    "hellknight breastplate (level 1, 10 gp; Pathfinder Treasure Vault 10)"
  ]
}
```

Similarly, checkboxes use descriptive text from the adventure summary:

```json
"summary_checkbox": {
  "type": "choice",
  "description": "Checkboxes in the adventure summary that should be selected",
  "choices": [
    "helped free her from the artifact's control",
    "destroyed the artifact and released her soul"
  ]
}
```

### Preset Naming Convention for Text-Based Choices

Preset names for text-based items and checkboxes are derived from the choice text by:

1. Replacing spaces and special characters with underscores
2. Truncating to approximately 55 characters

Item line presets use the prefix `item.line.`:
```json
"item.line.minor_healing_potion_level_1_4_gp": { "y": 7.4, "y2": 12.1 },
"item.line.hellknight_breastplate_level_1_10_gp;_Pathfinder": { "y": 35.5, "y2": 45.8 }
```

Checkbox presets use the prefix `checkbox.`:
```json
"checkbox.helped_free_her_from_the_artifact's_control": { "x": 58.197, "y": 19.028, "x2": 59.708, "y2": 27.993 }
```

### Item Strikeout Type

Seasons 5-7 use `"type": "strikeout"` for item lines (drawn within the `items` canvas), while earlier formats used `"type": "line"` (drawn within the `main` canvas). The strikeout type renders a thicker visual mark appropriate for crossing out item text.

### Scenarios Without Checkboxes

Some scenarios (particularly in Season 7) have no adventure summary checkboxes and only define item strikeouts. In these cases, the scenario layout omits the `Checkboxes` parameter group entirely.

## Format Evolution Summary

| Format | Seasons | Key Differences |
|--------|---------|----------------|
| v1 (`layout1`) | Season 1, early Season 2 | Player name, GM name, factions (3 rows), fame, boons, tier-based items (low/high), items sold/bought, downtime, chronicle number. Numeric indices for checkboxes/items |
| v2 (`layout2`) | Late Season 2 | Dropped player/GM names, factions, fame, boons, tiers, chronicle number. Added keepsakes. Simplified to XP gained + GP gained. Numeric indices |
| v3 (`layout3`) | Season 3 | Added starting/total XP and GP fields. Kept items sold/bought, downtime, keepsakes. Numeric indices |
| Season 4 | Season 4 | Transitional: dropped items sold/bought, downtime, keepsakes. Added treasure bundles, income earned. Multiple base variants per PDF layout. Text-based item choices |
| Season 5+ | Seasons 5-7 | Unified single base per season. Dedicated reputation and notes canvases. Text-based item/checkbox choices with per-scenario PDF coordinates. `defaultChronicleLocation` for Foundry VTT |

### What Season 5-7 Layouts Removed vs Earlier Formats

- Player name (`player`) and GM name (`gm`) fields
- Faction rows (`fac1_name`, `fac1_rep_gained`, etc.)
- Fame tracking (`starting_fame`, `fame`, `total_fame`)
- Boon strikeouts (`strikeout_boons`)
- Tier selection (`tier`) and tier-based item areas
- Items sold/bought sections with pricing columns
- Downtime activities
- Keepsake strikeouts
- Chronicle number

### What Season 5-7 Layouts Added

- `treasure_bundles_gp` and `income_earned` as separate reward fields with a computed GP Gained total line
- Dedicated `reputation` canvas and multiline field
- Dedicated `notes` canvas and multiline field
- `defaultChronicleLocation` for linking to Foundry VTT module PDFs
- Text-based choice keys for items and checkboxes with per-scenario PDF coordinates
- `checkbox` content type (distinct from `strikeout`)
