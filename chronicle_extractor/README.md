# Chronicle Extractor

A Python CLI utility that extracts chronicle sheet pages from Pathfinder Society (PFS) scenario PDFs. It reads each PDF's first page to identify the scenario number and name, then extracts the last page (the chronicle sheet) as a separate PDF organized into season-based subdirectories.

## Usage

```bash
python -m chronicle_extractor --input-dir <path> --output-dir <path>
```

### Arguments

| Argument       | Required | Description                                              |
|----------------|----------|----------------------------------------------------------|
| `--input-dir`  | Yes      | Directory containing PFS scenario PDFs to process.       |
| `--output-dir` | Yes      | Base directory for saving extracted chronicle PDFs.       |

- If `--input-dir` does not exist, the tool exits with code 1 and prints an error to stderr.
- If `--output-dir` does not exist, it is created automatically (including parent directories).

### Example

```bash
python -m chronicle_extractor --input-dir "Scenarios/Season 1" --output-dir chronicles
```

This processes all scenario PDFs in `Scenarios/Season 1/`, extracts the last page from each, and saves them under `chronicles/Season 1/` with filenames like `1-07-FloodedKingsCourtChronicle.pdf`.

## How It Works

1. Scans the input directory for `.pdf` files (non-recursive).
2. Skips map PDFs (filenames ending with "Map" or "Maps") and non-file entries.
3. Reads the first page of each PDF to find the scenario number (`#X-YY`) and name.
4. Extracts the last page as a new single-page PDF.
5. Saves to `output-dir/Season {X}/{X}-{YY}-{SanitizedName}Chronicle.pdf`.

## Dependencies

- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF text extraction and page manipulation
- [pytest](https://docs.pytest.org/) — test runner
- [hypothesis](https://hypothesis.readthedocs.io/) — property-based testing

Install via:

```bash
pip install -r requirements.txt
```
