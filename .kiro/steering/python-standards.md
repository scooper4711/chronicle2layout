---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# Python Standards

## Virtual Environment

Python is installed under `chronicle2layout/.venv`. Activate it by sourcing the activate script — this only needs to be done once per terminal session:

```bash
source chronicle2layout/.venv/bin/activate
```

After activation, `python`, `python3`, `pip`, and `pip3` are all available on the PATH from `.venv/bin/`.

## Running Tests

Tests use `pytest` and `hypothesis` (property-based testing). Run from the `chronicle2layout` directory:

```bash
source .venv/bin/activate
python -m pytest
```

## Key Packages

The venv includes PyMuPDF (`fitz`), Pillow, numpy, pytest, and hypothesis.

## Documentation Standards

**Docstring Style**: Use Google-style docstrings for all modules, classes, and public functions.

**Module-Level Docstrings**:
- Every Python module must have a module-level docstring explaining its purpose
- List the key public functions/classes if the module exports multiple items

```python
"""Item segmentation for chronicle text extraction.

Splits extracted text lines into individual item entries using
parenthesis-based heuristics. An item is finalized when two complete
parenthesis groups have been seen or end-of-line is reached with
balanced parentheses.
"""
```

**Function Docstrings**:
- Every public function must have a docstring with a one-line summary
- Use Args/Returns/Raises sections for non-trivial signatures
- Include type information in the signature (type hints), not in the docstring

```python
def find_layout_file(layout_dir: str, layout_id: str) -> Path:
    """Resolve a layout ID to its JSON file path.

    Searches for the layout file by splitting the layout_id into
    season and scenario components, checking for .generated.json
    fallback when the primary file is missing.

    Args:
        layout_dir: Base directory containing layout JSON files.
        layout_id: Dot-separated layout identifier (e.g., "pfs2.season5").

    Returns:
        Path to the resolved layout JSON file.

    Raises:
        ValueError: If no matching layout file exists on disk.
    """
```

**Type Hints**:
- All function parameters and return types must have type hints
- Use `X | None` union syntax (Python 3.10+) or `Optional[X]` for optional parameters
- Use `list[T]`, `dict[K, V]`, `tuple[T, ...]` for container types
- Import `from __future__ import annotations` if needed for forward references

**Requirement Attribution**:
- When a function implements specific requirements from a spec, include a "Requirements:" line in the docstring
- Prefix requirement numbers with the spec/feature name
- Format: `Requirements: spec-name requirement-numbers`

```python
def segment_items(lines: list[dict]) -> list[dict]:
    """Split extracted text lines into individual item entries.

    Uses parenthesis-based heuristics to detect item boundaries
    in the token stream.

    Args:
        lines: List of text line dicts with 'text', 'top_left_pct',
            and 'bottom_right_pct' keys.

    Returns:
        List of segmented item dicts with 'text', 'y', and 'y2' keys.

    Requirements: refactor-chronicle2layout 2.2
    """
```

**Imports**:
- All imports must be at module level (no function-level imports unless there is a documented circular dependency)
- Group imports: stdlib, third-party, local — separated by blank lines
- Use `import re` at module level, not inside functions

**Named Constants**:
- Define named constants for magic numbers and threshold values
- Use UPPER_SNAKE_CASE for module-level constants
- Add a brief comment if the constant's purpose isn't obvious from its name

```python
MAX_PAREN_GROUPS_PER_ITEM: int = 2  # Finalize item after this many complete paren groups
Y_COORDINATE_GROUPING_TOLERANCE: float = 2.0
CHECKBOX_CHARS: list[str] = ['□', '☐', '☑', '☒']
```

## File Size and Complexity

The same principles from the TypeScript coding standards apply to Python code. SonarCloud enforces these on both languages.

**File Size Limit**:
- Production files SHOULD be kept under 300 lines
- Production files MUST be kept under 500 lines

**Cyclomatic Complexity**:
- Functions SHOULD maintain cyclomatic complexity below 5
- Functions MUST maintain cyclomatic complexity below 15
- Use early returns, guard clauses, and helper functions to reduce complexity
- Extract complex conditionals into well-named helper functions

**When high CCN is acceptable** (same nuance as TypeScript):
- Flat dictionary lookups, simple if/elif chains with straightforward cases
- Add a `# noqa` or SonarCloud suppression comment with an explanation

**How to Reduce Complexity in Python**:
1. Use early returns and guard clauses
2. Extract complex conditionals into helper functions
3. Use dictionary dispatch instead of long if/elif chains
4. Break large functions into smaller, single-purpose functions
5. Use comprehensions instead of nested loops where readable
