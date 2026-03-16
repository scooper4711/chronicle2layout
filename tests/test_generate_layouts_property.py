"""Property-based tests for generate_layouts.derive_paths.

Uses Hypothesis to generate random valid Path objects and verifies that
derive_paths correctly derives MODULES_DIR, LAYOUTS_DIR, and DEBUG_DIR
as the expected subdirectories of the given base directory.

**Validates: Requirements 6.2**
"""

import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# Allow imports from the src/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from generate_layouts import derive_paths

# ---------------------------------------------------------------------------
# Hypothesis strategies for generating valid path components
# ---------------------------------------------------------------------------

# Restrict to characters that are valid in directory names across platforms
PATH_COMPONENT_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789_-"

path_component = st.text(
    alphabet=PATH_COMPONENT_ALPHABET,
    min_size=1,
    max_size=12,
)

# Generate a path with 1-4 directory segments
valid_path = st.lists(path_component, min_size=1, max_size=4).map(
    lambda parts: Path(*parts)
)


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

class TestDerivePathsProperty:
    """Property 3: Base directory path derivation.

    For any valid base_dir Path, derive_paths returns the expected
    subdirectory paths for modules, layouts, and debug.

    **Validates: Requirements 6.2**
    """

    @given(base_dir=valid_path)
    @settings(max_examples=100)
    def test_modules_dir_is_base_dir_slash_modules(self, base_dir: Path) -> None:
        """MODULES_DIR is always base_dir / "modules"."""
        modules_dir, _, _ = derive_paths(base_dir)
        assert modules_dir == base_dir / "modules"

    @given(base_dir=valid_path)
    @settings(max_examples=100)
    def test_layouts_dir_is_base_dir_slash_layouts_pfs2(self, base_dir: Path) -> None:
        """LAYOUTS_DIR is always base_dir / "layouts" / "pfs2"."""
        _, layouts_dir, _ = derive_paths(base_dir)
        assert layouts_dir == base_dir / "layouts" / "pfs2"

    @given(base_dir=valid_path)
    @settings(max_examples=100)
    def test_debug_dir_is_base_dir_slash_debug(self, base_dir: Path) -> None:
        """DEBUG_DIR is always base_dir / "debug"."""
        _, _, debug_dir = derive_paths(base_dir)
        assert debug_dir == base_dir / "debug"

    @given(base_dir=valid_path)
    @settings(max_examples=100)
    def test_all_derived_paths_are_children_of_base_dir(self, base_dir: Path) -> None:
        """All three derived paths start with the base_dir prefix."""
        modules_dir, layouts_dir, debug_dir = derive_paths(base_dir)
        base_parts = base_dir.parts
        assert modules_dir.parts[:len(base_parts)] == base_parts
        assert layouts_dir.parts[:len(base_parts)] == base_parts
        assert debug_dir.parts[:len(base_parts)] == base_parts
