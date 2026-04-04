"""Public API for the blueprint2layout package.

Exports generate_layout, the main entry point that converts a Blueprint
JSON file and a chronicle PDF into a layout dictionary conforming to
LAYOUT_FORMAT.md.
"""

from pathlib import Path

from blueprint2layout.blueprint import build_blueprint_index, load_blueprint_with_inheritance
from blueprint2layout.detection import detect_structures
from blueprint2layout.output import assemble_layout
from blueprint2layout.pdf_preparation import prepare_page
from blueprint2layout.resolver import resolve_canvases


def generate_layout(
    blueprint_path: str | Path,
    pdf_path: str | Path,
    blueprints_dir: str | Path | None = None,
) -> dict:
    """Generate a layout dictionary from a Blueprint and chronicle PDF.

    Runs the complete pipeline: PDF preparation, structural detection,
    Blueprint loading with inheritance, canvas resolution, parent-relative
    conversion, and layout assembly.

    Args:
        blueprint_path: Path to the target Blueprint JSON file.
        pdf_path: Path to the chronicle PDF file.
        blueprints_dir: Directory to scan for Blueprint files when
            resolving parent references. Defaults to the directory
            containing blueprint_path.

    Returns:
        The layout dictionary ready for JSON serialization.

    Raises:
        FileNotFoundError: If blueprint_path or pdf_path does not exist.
        ValueError: If the PDF is invalid or Blueprint has errors.

    Requirements: chronicle-blueprints 15.1, 15.2, 15.3, 15.4, 15.5
    """
    blueprint_path = Path(blueprint_path)
    pdf_path = Path(pdf_path)

    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if blueprints_dir is None:
        blueprints_dir = blueprint_path.parent
    else:
        blueprints_dir = Path(blueprints_dir)

    grayscale, rgb = prepare_page(str(pdf_path))
    detection = detect_structures(grayscale, rgb)

    blueprint_index = build_blueprint_index(blueprints_dir)
    blueprint, inherited_canvases = load_blueprint_with_inheritance(
        blueprint_path, blueprint_index
    )

    resolved = resolve_canvases(inherited_canvases, blueprint.canvases, detection)

    return assemble_layout(blueprint, resolved, resolved)
