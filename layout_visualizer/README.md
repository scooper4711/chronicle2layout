# Layout Visualizer

Renders visual overlays on chronicle PDFs to debug and verify layout
definitions. Draws canvas regions, content field positions, or example
data values onto the chronicle page and saves the result as a PNG.

## Usage

```bash
python -m layout_visualizer [options]
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--layout-root` | Yes | — | Root directory containing layout JSON files. |
| `--layout-id` | Yes | — | Layout id or shell-style wildcard (e.g. `pfs2.b*`). |
| `--output-dir` | No | `.` | Directory for output PNG files. |
| `--watch` | No | off | Watch layout files and auto-regenerate on changes. |
| `--mode` | No | `canvases` | What to visualize (see below). |

### Modes

| Mode | Description |
|------|-------------|
| `canvases` | Draws colored rectangles for each canvas region. |
| `fields` | Draws content field positions within their canvases. |
| `data` | Renders example parameter values as styled text. |

### Examples

Visualize canvas regions for a single layout:

```bash
python -m layout_visualizer \
  --layout-root modules/pfs-chronicle-generator/assets/layouts \
  --layout-id pfs2.s1-02 \
  --output-dir debug_clips/layout_visualizer
```

Visualize all layouts matching a wildcard:

```bash
python -m layout_visualizer \
  --layout-root modules/pfs-chronicle-generator/assets/layouts \
  --layout-id 'pfs2.*' \
  --output-dir debug_clips/layout_visualizer
```

Watch mode with field overlay:

```bash
python -m layout_visualizer \
  --watch \
  --mode fields \
  --layout-root modules/pfs-chronicle-generator/assets/layouts \
  --layout-id 'pfs2.*' \
  --output-dir debug_clips/layout_visualizer
```

## How It Works

1. Builds a layout index by scanning `--layout-root` for JSON files.
2. Resolves the chronicle PDF from the layout's
   `defaultChronicleLocation` field (walking the inheritance chain).
3. Renders the PDF page at 150 DPI.
4. Draws the selected overlay (canvases, fields, or data).
5. Writes the result as a PNG to `--output-dir`.

In watch mode, monitors all layout files in the inheritance chain and
re-renders automatically when any file changes.

## Testing

```bash
python -m pytest tests/layout_visualizer/ -v
```
