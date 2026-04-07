# Layout Generator

Generates leaf layout JSON files from chronicle PDFs and a TOML metadata
file. Scans chronicle PDFs, matches them against regex rules in the TOML
to determine the parent layout, resolves canvas regions from the parent
layout inheritance chain, and writes per-chronicle layout files.

## Usage

```bash
python -m layout_generator [options] <pdf_path>
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `pdf_path` | Yes | — | Path to a single chronicle PDF or a directory of PDFs. |
| `--metadata-file` | No | `chronicle_properties.toml` | Path to the TOML metadata file. |
| `--layouts-dir` | No | from TOML | Root directory containing parent layout files. |
| `--output-dir` | No | `--layouts-dir` | Directory for generated layout JSON files. |
| `--item-canvas` | No | `items` | Canvas name for item extraction. |
| `--checkbox-canvas` | No | `summary` | Canvas name for checkbox detection. |

### Examples

Generate layouts for all chronicles in a directory:

```bash
python -m layout_generator \
  --metadata-file chronicle_properties.toml \
  modules/pfs-chronicle-generator/assets/chronicles
```

Generate a layout for a single chronicle PDF:

```bash
python -m layout_generator \
  --metadata-file chronicle_properties.toml \
  modules/pfs-chronicle-generator/assets/chronicles/pfs2/season3/3-04-TheDevil-WroughtDisappearanceChronicle.pdf
```

## How It Works

1. Loads the TOML metadata file containing regex-based matching rules.
2. For each chronicle PDF, finds the first matching rule to determine
   the parent layout id and output filename.
3. Resolves canvas coordinates by walking the parent layout inheritance
   chain via `shared.layout_index`.
4. Extracts item positions and checkbox locations from the PDF.
5. Writes a leaf layout JSON file with resolved coordinates.

## Testing

```bash
python -m pytest tests/layout_generator/ -v
```
