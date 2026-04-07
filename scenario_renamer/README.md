# Scenario Renamer

Copies and renames Pathfinder Society (PFS) scenario PDFs and associated
image files (maps, handouts) into an organized directory structure with
descriptive filenames.

## How It Works

The utility uses a two-pass strategy:

1. **Pass 1 — Scenario PDFs**: Opens each PDF, extracts the scenario number
   and name using the `chronicle_extractor` package, copies the full PDF with
   a descriptive filename (e.g., `1-01-TheAbsalomInitiation.pdf`), and builds
   a lookup table mapping (season, scenario) pairs to names.

2. **Pass 2 — Scenario Images**: Parses PZOPFS codes or season-number patterns
   from image filenames, resolves the scenario name from the lookup table, and
   copies with a descriptive filename preserving the original suffix
   (e.g., `PZOPFS0409 A-Nighttime Ambush.jpg` →
   `4-09-PerilousExperimentA-NighttimeAmbush.jpg`).

Files that can't be attributed to a scenario are copied as-is, preserving
their relative path.

## Usage

```bash
python -m scenario_renamer --input-dir Scenarios --output-dir PFS
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--input-dir`  | Directory containing scenario PDFs and images (recursive) |
| `--output-dir` | Base directory for renamed output files (created if missing) |

### Example

```bash
# Process all seasons, quests, and bounties in one go
python -m scenario_renamer --input-dir Scenarios --output-dir PFS
```

Output structure:
```
PFS/
├── Season 1/
│   ├── 1-01-TheAbsalomInitiation.pdf
│   ├── 1-01-TheAbsalomInitiationMaps.pdf
│   └── ...
├── Season 4/
│   ├── 4-09-PerilousExperimentA-NighttimeAmbush.jpg
│   └── ...
├── Quests/
│   └── Q14-TheSwordlordsChallenge.pdf
└── Bounties/
    └── B1-TheWhitefangWyrm.pdf
```

## Dependencies

This utility depends on the `chronicle_extractor` package for:
- `ScenarioInfo` and `extract_scenario_info` — scenario metadata extraction from PDF text
- `sanitize_name` — filename sanitization
- `is_map_pdf` — map PDF detection

Both packages must be available on the Python path (they share the same
project root).

## Testing

```bash
python -m pytest tests/scenario_renamer/ -v
```
