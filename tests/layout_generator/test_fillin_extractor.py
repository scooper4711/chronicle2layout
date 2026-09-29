"""Tests for fill-in blank extraction.

Covers field naming from surrounding words, canvas assignment, and
leaf assembly with a Fill-ins parameter group.
"""

from pathlib import Path

import pytest

from layout_generator.fillin_extractor import derive_fillin_name, extract_fillins
from layout_generator.generator import generate_layout_json

CHRONICLES = Path("modules/pfs-chronicle-generator/assets/chronicles")

CASES = [
    (
        "pfs2/printables/Paizo+Printables+Sanctioning.pdf",
        "Adventure Completed",
    ),
    (
        "pfs2/season1/1-01-TheAbsalomInitiationChronicle.pdf",
        "task of level",
    ),
    (
        "sfs2/season1/1-07-SeizeandDestroyChronicle.pdf",
        "%",
    ),
    (
        "sfs2/season1/1-15-RuinsoftheWorldSoulChronicle.pdf",
        "note it here",
    ),
    (
        "sfs2/season1/1-23-PsychicEchoesChronicle.pdf",
        "kaylix cubs",
    ),
    (
        "sfs2/season1/1-25-TheHollowedShellChronicle.pdf",
        "audio logs",
    ),
    (
        "sfs2/season2/2-06-AnInsideJobChronicle.pdf",
        "adopted a pet",
    ),
]


def _pdf(name: str) -> Path:
    return CHRONICLES / name


class TestDeriveFillinName:
    """Naming from tokens around a run."""

    def test_forward_takes_two_words(self) -> None:
        assert derive_fillin_name(["rescued"], ["kaylix", "cubs."]) == "kaylix cubs"

    def test_forward_stops_at_closer(self) -> None:
        # Closer alone yields nothing forward; backward decides.
        assert (
            derive_fillin_name(["and", "note", "it", "here", "("], [")", "You"])
            == "note it here"
        )

    def test_backward_skips_opener(self) -> None:
        assert (
            derive_fillin_name(["and", "□", "adopted", "a", "pet", "("], [")", "or"])
            == "adopted a pet"
        )

    def test_empty_both_sides_returns_none(self) -> None:
        assert derive_fillin_name([], []) is None


class TestExtractFillins:
    """End-to-end extraction on the seven known chronicles."""

    @pytest.mark.parametrize("relpath,expected", CASES)
    def test_expected_name(self, relpath: str, expected: str) -> None:
        pdf = _pdf(relpath)
        if not pdf.exists():
            pytest.skip("chronicle PDF not available")
        fillins = extract_fillins(pdf, {"page": [0.0, 0.0, 100.0, 100.0]})
        names = [entry["name"] for entry in fillins]
        assert names == [expected]

    def test_canvas_and_fontsize_sane(self) -> None:
        pdf = _pdf(CASES[0][0])
        if not pdf.exists():
            pytest.skip("chronicle PDF not available")
        fillins = extract_fillins(pdf, {"summary": [5.0, 20.0, 80.0, 40.0]})
        assert len(fillins) == 1
        entry = fillins[0]
        assert entry["canvas"] == "summary"
        assert 6 <= entry["fontsize"] <= 20
        assert 0 <= entry["x"] < entry["x2"] <= 100
        assert 0 <= entry["y"] < entry["y2"] <= 100


class TestFillinsSection:
    """Leaf assembly gains a Fill-ins group and text elements."""

    def test_params_and_content(self, tmp_path: Path) -> None:
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        layout = generate_layout_json(
            pdf_path=pdf,
            scenario_id="pfs2.test",
            fillins=[
                {
                    "name": "kaylix cubs",
                    "canvas": "summary",
                    "x": 10.0,
                    "y": 20.0,
                    "x2": 40.0,
                    "y2": 25.0,
                    "fontsize": 10,
                },
            ],
        )
        assert layout["parameters"]["Fill-ins"]["kaylix cubs"]["type"] == "text"
        assert len(layout["content"]) == 1
        element = layout["content"][0]
        assert element["value"] == "param:kaylix cubs"
        assert element["type"] == "text"
        assert element["canvas"] == "summary"

    def test_no_fillins_no_section(self, tmp_path: Path) -> None:
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        layout = generate_layout_json(pdf_path=pdf, scenario_id="pfs2.test")
        assert "parameters" not in layout
