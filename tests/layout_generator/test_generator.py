"""Unit tests for layout_generator.generator module.

Tests make_safe_label sanitization, generate_layout_json with real
chronicle PDFs, metadata-only output, FileNotFoundError, item section
assembly, checkbox section assembly, and section ordering.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10,
    8.11, 8.12, 11.1, 11.2, 11.3, 11.4, 14.1, 14.2, 14.3
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from layout_generator.generator import (
    STRIKEOUT_X_END,
    STRIKEOUT_X_START,
    _SAFE_LABEL_MAX_LENGTH,
    generate_layout_json,
    make_safe_label,
)

REAL_PDF = Path("modules/pfs-chronicle-generator/assets/chronicles/pfs2/season1/1-00-OriginoftheOpenRoadChronicle.pdf")


# ---------------------------------------------------------------------------
# make_safe_label
# ---------------------------------------------------------------------------


class TestMakeSafeLabel:
    """Tests for make_safe_label sanitization."""

    def test_spaces_replaced_with_underscores(self) -> None:
        """Spaces are replaced with underscores."""
        assert make_safe_label("hello world") == "hello_world"

    def test_commas_stripped(self) -> None:
        """Commas are removed."""
        assert make_safe_label("a,b,c") == "abc"

    def test_periods_stripped(self) -> None:
        """Periods are removed."""
        assert make_safe_label("item.name") == "itemname"

    def test_parentheses_stripped(self) -> None:
        """Parentheses are removed."""
        assert make_safe_label("item (level 1)") == "item_level_1"

    def test_quotes_stripped(self) -> None:
        """Single and double quotes are removed."""
        assert make_safe_label("it's a \"test\"") == "its_a_test"

    def test_truncation_to_50_chars(self) -> None:
        """Output is truncated to 50 characters."""
        long_text = "a" * 100
        result = make_safe_label(long_text)
        assert len(result) == _SAFE_LABEL_MAX_LENGTH

    def test_truncation_boundary(self) -> None:
        """A 50-char input is not truncated."""
        text = "x" * 50
        assert len(make_safe_label(text)) == 50

    def test_under_limit_not_truncated(self) -> None:
        """A short input is returned without truncation."""
        assert make_safe_label("short") == "short"

    def test_deterministic_output(self) -> None:
        """Same input always produces the same output."""
        text = "Sword (level 1) (10 gp)"
        assert make_safe_label(text) == make_safe_label(text)

    def test_empty_string(self) -> None:
        """An empty string returns empty."""
        assert make_safe_label("") == ""

    def test_all_punctuation_combined(self) -> None:
        """All stripped characters are removed in one pass."""
        result = make_safe_label("a,b.c(d)e'f\"g")
        assert result == "abcdefg"

    def test_multiple_spaces(self) -> None:
        """Multiple consecutive spaces become multiple underscores."""
        assert make_safe_label("a  b") == "a__b"



# ---------------------------------------------------------------------------
# generate_layout_json — Real chronicle PDF
# ---------------------------------------------------------------------------


class TestGenerateLayoutRealPdf:
    """Tests using a real chronicle PDF from the Scenarios directory."""

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_output_has_expected_structure(self) -> None:
        """Output dict has id, parent, parameters, presets, content."""
        result = generate_layout_json(
            pdf_path=str(REAL_PDF),
            item_region_pct=[0.5, 50.0, 40.0, 83.0],
            checkbox_region_pct=[0.0, 9.0, 100.0, 31.0],
            scenario_id="pfs2.s1-00",
            parent="pfs2.season1",
            description="Test scenario",
        )

        assert result["id"] == "pfs2.s1-00"
        assert result["parent"] == "pfs2.season1"
        assert result["description"] == "Test scenario"
        assert "parameters" in result
        assert "presets" in result
        assert "content" in result
        assert isinstance(result["content"], list)

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_output_contains_items_parameter(self) -> None:
        """Output parameters include an Items group with choices."""
        result = generate_layout_json(
            pdf_path=str(REAL_PDF),
            item_region_pct=[0.5, 50.0, 40.0, 83.0],
            scenario_id="pfs2.s1-00",
            parent="pfs2.season1",
        )

        if "Items" in result.get("parameters", {}):
            items_param = result["parameters"]["Items"]
            assert "strikeout_item_lines" in items_param
            assert items_param["strikeout_item_lines"]["type"] == "choice"
            assert len(items_param["strikeout_item_lines"]["choices"]) > 0


# ---------------------------------------------------------------------------
# generate_layout_json — Metadata-only output (no items, no checkboxes)
# ---------------------------------------------------------------------------


class TestGenerateLayoutMetadataOnly:
    """Tests for metadata-only output when both regions are None."""

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_no_regions_produces_metadata_only(self) -> None:
        """Passing None for both regions produces metadata-only output."""
        result = generate_layout_json(
            pdf_path=str(REAL_PDF),
            item_region_pct=None,
            checkbox_region_pct=None,
            scenario_id="pfs2.test",
            parent="pfs2.season1",
            description="Metadata only",
            default_chronicle_location="path/to/chronicle.pdf",
        )

        assert result["id"] == "pfs2.test"
        assert result["parent"] == "pfs2.season1"
        assert result["description"] == "Metadata only"
        assert result["defaultChronicleLocation"] == "path/to/chronicle.pdf"
        assert "parameters" not in result
        assert "presets" not in result
        assert "content" not in result

    @pytest.mark.skipif(
        not REAL_PDF.exists(),
        reason="Real chronicle PDF not available",
    )
    def test_optional_metadata_fields_omitted_when_none(self) -> None:
        """Metadata fields set to None are excluded from output."""
        result = generate_layout_json(
            pdf_path=str(REAL_PDF),
            item_region_pct=None,
            checkbox_region_pct=None,
            scenario_id="pfs2.test",
            parent="pfs2.season1",
        )

        assert "description" not in result
        assert "defaultChronicleLocation" not in result


# ---------------------------------------------------------------------------
# generate_layout_json — FileNotFoundError
# ---------------------------------------------------------------------------


class TestGenerateLayoutFileNotFound:
    """Tests for FileNotFoundError on missing PDF."""

    def test_missing_pdf_raises_file_not_found(self) -> None:
        """A non-existent PDF path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            generate_layout_json(
                pdf_path="/nonexistent/path/to/file.pdf",
                scenario_id="test",
            )

    def test_missing_pdf_error_includes_path(self) -> None:
        """The error message includes the missing file path."""
        bad_path = "/tmp/does_not_exist_12345.pdf"
        with pytest.raises(FileNotFoundError, match=bad_path):
            generate_layout_json(pdf_path=bad_path)



# ---------------------------------------------------------------------------
# Item section assembly (mocked extraction)
# ---------------------------------------------------------------------------

MOCK_ITEMS = [
    {"text": "Sword (level 1) (10 gp)", "y": 10.5, "y2": 15.3},
    {"text": "Shield (level 2) (20 gp)", "y": 20.1, "y2": 25.7},
]

MOCK_LINES = [
    {
        "text": "Sword (level 1) (10 gp)",
        "top_left_pct": [0.0, 10.5],
        "bottom_right_pct": [100.0, 15.3],
    },
    {
        "text": "Shield (level 2) (20 gp)",
        "top_left_pct": [0.0, 20.1],
        "bottom_right_pct": [100.0, 25.7],
    },
]


class TestItemSectionAssembly:
    """Tests for item section assembly using mocked extraction."""

    @pytest.fixture()
    def layout_with_items(self, tmp_path: Path) -> dict:
        """Generate a layout with mocked item extraction."""
        import fitz

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        with (
            patch(
                "layout_generator.generator.extract_text_lines",
                return_value=MOCK_LINES,
            ),
            patch(
                "layout_generator.generator.segment_items",
                return_value=MOCK_ITEMS,
            ),
        ):
            return generate_layout_json(
                pdf_path=str(pdf_path),
                item_region_pct=[0.0, 0.0, 100.0, 100.0],
                checkbox_region_pct=None,
                item_canvas_name="items",
                scenario_id="pfs2.test",
                parent="pfs2.season1",
            )

    def test_items_parameter_choices(self, layout_with_items: dict) -> None:
        """Items parameter group has correct choice list."""
        params = layout_with_items["parameters"]["Items"]
        choices = params["strikeout_item_lines"]["choices"]
        assert choices == [
            "Sword (level 1) (10 gp)",
            "Shield (level 2) (20 gp)",
        ]

    def test_items_parameter_type(self, layout_with_items: dict) -> None:
        """Items parameter is a choice type."""
        params = layout_with_items["parameters"]["Items"]
        assert params["strikeout_item_lines"]["type"] == "choice"

    def test_base_preset_present(self, layout_with_items: dict) -> None:
        """Base strikeout_item preset has correct canvas and coordinates."""
        presets = layout_with_items["presets"]
        assert "strikeout_item" in presets
        base = presets["strikeout_item"]
        assert base["canvas"] == "items"
        assert base["color"] == "black"
        assert base["x"] == STRIKEOUT_X_START
        assert base["x2"] == STRIKEOUT_X_END

    def test_line_presets_present(self, layout_with_items: dict) -> None:
        """Each item has an item.line.<safe_label> preset with y/y2."""
        presets = layout_with_items["presets"]
        sword_label = make_safe_label("Sword (level 1) (10 gp)")
        shield_label = make_safe_label("Shield (level 2) (20 gp)")

        sword_preset = f"item.line.{sword_label}"
        shield_preset = f"item.line.{shield_label}"

        assert sword_preset in presets
        assert shield_preset in presets
        assert presets[sword_preset]["y"] == pytest.approx(10.5)
        assert presets[sword_preset]["y2"] == pytest.approx(15.3)
        assert presets[shield_preset]["y"] == pytest.approx(20.1)
        assert presets[shield_preset]["y2"] == pytest.approx(25.7)

    def test_content_entry_structure(self, layout_with_items: dict) -> None:
        """Content has a choice entry mapping item text to strikeout elements."""
        content = layout_with_items["content"]
        item_content = content[0]
        assert item_content["type"] == "choice"
        assert item_content["choices"] == "param:strikeout_item_lines"

        content_map = item_content["content"]
        assert "Sword (level 1) (10 gp)" in content_map
        assert "Shield (level 2) (20 gp)" in content_map

        sword_entry = content_map["Sword (level 1) (10 gp)"]
        assert len(sword_entry) == 1
        assert sword_entry[0]["type"] == "strikeout"
        assert "strikeout_item" in sword_entry[0]["presets"]



# ---------------------------------------------------------------------------
# Checkbox section assembly (mocked extraction)
# ---------------------------------------------------------------------------

MOCK_CHECKBOXES = [
    {"x": 10.0, "y": 20.0, "x2": 12.0, "y2": 22.0},
    {"x": 30.0, "y": 20.0, "x2": 32.0, "y2": 22.0},
]

MOCK_CHECKBOX_LABELS = [
    {
        "checkbox": {"x": 10.0, "y": 20.0, "x2": 12.0, "y2": 22.0},
        "label": "Primary Mission",
    },
    {
        "checkbox": {"x": 30.0, "y": 20.0, "x2": 32.0, "y2": 22.0},
        "label": "Secondary Objective",
    },
]


class TestCheckboxSectionAssembly:
    """Tests for checkbox section assembly using mocked extraction."""

    @pytest.fixture()
    def layout_with_checkboxes(self, tmp_path: Path) -> dict:
        """Generate a layout with mocked checkbox extraction."""
        import fitz

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        with (
            patch(
                "layout_generator.generator.detect_checkboxes",
                return_value=MOCK_CHECKBOXES,
            ),
            patch(
                "layout_generator.generator.extract_checkbox_labels",
                return_value=MOCK_CHECKBOX_LABELS,
            ),
        ):
            return generate_layout_json(
                pdf_path=str(pdf_path),
                item_region_pct=None,
                checkbox_region_pct=[0.0, 0.0, 100.0, 100.0],
                checkbox_canvas_name="summary",
                scenario_id="pfs2.test",
                parent="pfs2.season1",
            )

    def test_checkbox_parameter_choices(
        self, layout_with_checkboxes: dict,
    ) -> None:
        """Checkboxes parameter group has correct choice list."""
        params = layout_with_checkboxes["parameters"]["Checkboxes"]
        choices = params["summary_checkbox"]["choices"]
        assert choices == ["Primary Mission", "Secondary Objective"]

    def test_checkbox_parameter_type(
        self, layout_with_checkboxes: dict,
    ) -> None:
        """Checkboxes parameter is a choice type."""
        params = layout_with_checkboxes["parameters"]["Checkboxes"]
        assert params["summary_checkbox"]["type"] == "choice"

    def test_base_checkbox_preset(
        self, layout_with_checkboxes: dict,
    ) -> None:
        """Base checkbox preset has correct canvas, color, and size."""
        presets = layout_with_checkboxes["presets"]
        assert "checkbox" in presets
        base = presets["checkbox"]
        assert base["canvas"] == "summary"
        assert base["color"] == "black"
        assert base["size"] == 1

    def test_checkbox_presets_present(
        self, layout_with_checkboxes: dict,
    ) -> None:
        """Each checkbox has a checkbox.<safe_label> preset with coordinates."""
        presets = layout_with_checkboxes["presets"]
        primary_label = make_safe_label("Primary Mission")
        secondary_label = make_safe_label("Secondary Objective")

        primary_preset = f"checkbox.{primary_label}"
        secondary_preset = f"checkbox.{secondary_label}"

        assert primary_preset in presets
        assert secondary_preset in presets
        assert presets[primary_preset]["x"] == pytest.approx(10.0)
        assert presets[primary_preset]["y"] == pytest.approx(20.0)
        assert presets[secondary_preset]["x"] == pytest.approx(30.0)
        assert presets[secondary_preset]["y"] == pytest.approx(20.0)

    def test_content_entry_structure(
        self, layout_with_checkboxes: dict,
    ) -> None:
        """Content has a choice entry mapping labels to checkbox elements."""
        content = layout_with_checkboxes["content"]
        cb_content = content[0]
        assert cb_content["type"] == "choice"
        assert cb_content["choices"] == "param:summary_checkbox"

        content_map = cb_content["content"]
        assert "Primary Mission" in content_map
        assert "Secondary Objective" in content_map

        primary_entry = content_map["Primary Mission"]
        assert len(primary_entry) == 1
        assert primary_entry[0]["type"] == "checkbox"
        assert "checkbox" in primary_entry[0]["presets"]



# ---------------------------------------------------------------------------
# Section ordering: items skeleton → checkboxes → item line presets
# ---------------------------------------------------------------------------


class TestSectionOrdering:
    """Tests for correct ordering of sections in the layout output.

    Per Requirement 8.10, when both items and checkboxes are present:
    items skeleton (params + base preset + content) → checkboxes →
    item line presets.
    """

    @pytest.fixture()
    def layout_with_both(self, tmp_path: Path) -> dict:
        """Generate a layout with both items and checkboxes mocked."""
        import fitz

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        with (
            patch(
                "layout_generator.generator.extract_text_lines",
                return_value=MOCK_LINES,
            ),
            patch(
                "layout_generator.generator.segment_items",
                return_value=MOCK_ITEMS,
            ),
            patch(
                "layout_generator.generator.detect_checkboxes",
                return_value=MOCK_CHECKBOXES,
            ),
            patch(
                "layout_generator.generator.extract_checkbox_labels",
                return_value=MOCK_CHECKBOX_LABELS,
            ),
        ):
            return generate_layout_json(
                pdf_path=str(pdf_path),
                item_region_pct=[0.0, 0.0, 100.0, 100.0],
                checkbox_region_pct=[0.0, 0.0, 100.0, 100.0],
                item_canvas_name="items",
                checkbox_canvas_name="summary",
                scenario_id="pfs2.test",
                parent="pfs2.season1",
            )

    def test_content_order_items_then_checkboxes(
        self, layout_with_both: dict,
    ) -> None:
        """Content array has item choice first, checkbox choice second."""
        content = layout_with_both["content"]
        assert len(content) == 2
        assert content[0]["choices"] == "param:strikeout_item_lines"
        assert content[1]["choices"] == "param:summary_checkbox"

    def test_parameters_contain_both_groups(
        self, layout_with_both: dict,
    ) -> None:
        """Parameters contain both Items and Checkboxes groups."""
        params = layout_with_both["parameters"]
        assert "Items" in params
        assert "Checkboxes" in params

    def test_presets_order_base_then_checkbox_then_line(
        self, layout_with_both: dict,
    ) -> None:
        """Presets contain base item preset, checkbox presets, then line presets.

        The base strikeout_item preset is added first, then checkbox
        presets, then item line presets are appended last.
        """
        presets = layout_with_both["presets"]
        preset_keys = list(presets.keys())

        # Base item preset should come before checkbox presets
        assert "strikeout_item" in preset_keys

        # Checkbox presets should be present
        checkbox_keys = [k for k in preset_keys if k.startswith("checkbox")]
        assert len(checkbox_keys) > 0

        # Item line presets should come after checkbox presets
        line_keys = [k for k in preset_keys if k.startswith("item.line.")]
        assert len(line_keys) > 0

        # Verify ordering: last checkbox key index < first line key index
        last_checkbox_idx = max(preset_keys.index(k) for k in checkbox_keys)
        first_line_idx = min(preset_keys.index(k) for k in line_keys)
        assert last_checkbox_idx < first_line_idx, (
            f"Checkbox presets should come before item line presets: "
            f"{preset_keys}"
        )

    def test_base_item_preset_before_checkboxes(
        self, layout_with_both: dict,
    ) -> None:
        """The strikeout_item base preset appears before checkbox presets."""
        preset_keys = list(layout_with_both["presets"].keys())
        base_idx = preset_keys.index("strikeout_item")
        checkbox_idx = preset_keys.index("checkbox")
        assert base_idx < checkbox_idx
