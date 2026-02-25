# Chronicle Layout Generation Scripts

## Season 7 Quick Script

### Usage

```bash
./chronicle2layout/generate_s7_layout.sh <path-to-chronicle-pdf>
```

### Example

```bash
./chronicle2layout/generate_s7_layout.sh modules/pf2e-pfs07-year-of-battles-spark/assets/chronicles-1/710-chronicle-ShatteredBlades.pdf
```

This will automatically:
- Extract the scenario number and name from the filename
- Generate the proper layout ID (`pfs2.s7-XX`)
- Create a formatted description
- Output the layout to `layouts/pfs2/s7/7-XX-ScenarioName.json`

### Batch Processing

To generate layouts for multiple chronicles at once:

```bash
for pdf in modules/pf2e-pfs07-year-of-battles-spark/assets/chronicles-1/7??-chronicle-*.pdf; do
    ./chronicle2layout/generate_s7_layout.sh "$pdf"
done
```

### Filename Convention

The script expects chronicle PDFs to follow this naming pattern:
```
7XX-chronicle-ScenarioName.pdf
```

Where:
- `7XX` is the scenario number (e.g., `706`, `710`)
- `ScenarioName` is in PascalCase (e.g., `ShatteredBlades`, `BrastlewarkAtWarPart1`)

The script will automatically convert this to the appropriate output format.
