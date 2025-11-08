# Checkbox Finder

This small tool finds checkboxes on a single-page PDF and reports their center locations as percentages of page width/height.

Features:
- First attempts to read AcroForm checkbox field rectangles (fast and exact when present).
- If no AcroForm checkboxes are found, falls back to image-based detection using PyMuPDF + OpenCV to find square contours.

Install

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Usage

```bash
python -m src.chronicle2layout /path/to/single_page.pdf
```

The script prints JSON to stdout with a list of checkboxes. Each checkbox entry contains:
- `x_pct` — X position of the checkbox center as percentage (0 = left, 100 = right)
- `y_pct` — Y position of the checkbox center as percentage (0 = bottom, 100 = top)
- `method` — `acroform` or `image` indicating how it was found

Notes and assumptions

- Works best on single-page PDFs. If a multi-page PDF is provided, the script processes the first page.
- For image-based detection, the algorithm looks for roughly square shapes. It may detect other square elements depending on the form layout. You can tune thresholds in the script.
- Coordinates use PDF-style origin (0,0) at bottom-left so `y_pct=0` is bottom of the page and `y_pct=100` is top.

License: MIT
