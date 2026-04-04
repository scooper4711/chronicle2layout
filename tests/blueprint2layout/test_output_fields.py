"""Unit tests for extended layout assembly with parameters and content.

Tests assemble_layout and _generate_content_element from
blueprint2layout.output, verifying parameters pass-through,
defaultChronicleLocation, content element generation from resolved
fields, trigger wrapping, key ordering, backward compatibility,
and styling property filtering.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.7, 9.8, 9.9, 11.1, 11.4
"""

import pytest

from blueprint2layout.models import Blueprint, CanvasEntry, ResolvedCanvas, ResolvedField
from blueprint2layout.output import assemble_layout, _generate_content_element


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_blueprint(**overrides) -> Blueprint:
    """Create a minimal Blueprint with sensible defaults."""
    defaults = {
        "id": "test.bp",
        "canvases": [
            CanvasEntry(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0),
        ],
    }
    defaults.update(overrides)
    return Blueprint(**defaults)


def _make_resolved_page() -> dict[str, ResolvedCanvas]:
    """Return a single-page resolved canvas dict."""
    page = ResolvedCanvas(name="page", left=0.0, right=100.0, top=0.0, bottom=100.0)
    return {"page": page}


# ---------------------------------------------------------------------------
# 1. assemble_layout with merged_parameters
# ---------------------------------------------------------------------------


def test_assemble_layout_includes_parameters_section():
    """Output contains 'parameters' when merged_parameters is provided."""
    blueprint = _make_blueprint()
    resolved = _make_resolved_page()
    params = {
        "Event Info": {
            "event": {"type": "text", "description": "Event name"},
        },
    }

    layout = assemble_layout(blueprint, resolved, resolved, merged_parameters=params)

    assert "parameters" in layout
    assert layout["parameters"] is params


# ---------------------------------------------------------------------------
# 2. assemble_layout with defaultChronicleLocation
# ---------------------------------------------------------------------------


def test_assemble_layout_includes_default_chronicle_location():
    """Output contains 'defaultChronicleLocation' from Blueprint."""
    blueprint = _make_blueprint(
        default_chronicle_location="modules/pfs2e-chronicles/chronicles/s5/",
    )
    resolved = _make_resolved_page()

    layout = assemble_layout(blueprint, resolved, resolved)

    assert layout["defaultChronicleLocation"] == "modules/pfs2e-chronicles/chronicles/s5/"


# ---------------------------------------------------------------------------
# 3. assemble_layout with resolved_fields produces content section
# ---------------------------------------------------------------------------


def test_assemble_layout_includes_content_from_resolved_fields():
    """Output contains 'content' array when resolved_fields is provided."""
    blueprint = _make_blueprint()
    resolved = _make_resolved_page()
    fields = [
        ResolvedField(
            name="char", canvas="page", type="text",
            param="char", x=1.0, y=2.0, x2=50.0, y2=5.0,
            font="Helvetica", fontsize=14,
        ),
    ]

    layout = assemble_layout(blueprint, resolved, resolved, resolved_fields=fields)

    assert "content" in layout
    assert len(layout["content"]) == 1
    assert layout["content"][0]["value"] == "param:char"


# ---------------------------------------------------------------------------
# 4. _generate_content_element with param field
# ---------------------------------------------------------------------------


def test_generate_content_element_param_field():
    """Content element for a param field has value 'param:<name>'."""
    field = ResolvedField(
        name="char", canvas="main", type="text",
        param="char", x=1.0, y=2.0, x2=50.0, y2=5.0,
    )

    element = _generate_content_element(field)

    assert element["value"] == "param:char"
    assert element["type"] == "text"
    assert element["canvas"] == "main"


# ---------------------------------------------------------------------------
# 5. _generate_content_element with value field
# ---------------------------------------------------------------------------


def test_generate_content_element_static_value():
    """Content element for a value field has the static text as value."""
    field = ResolvedField(
        name="label", canvas="page", type="text",
        value="Hello World", x=0.0, y=0.0, x2=100.0, y2=10.0,
    )

    element = _generate_content_element(field)

    assert element["value"] == "Hello World"
    assert element["type"] == "text"


# ---------------------------------------------------------------------------
# 6. _generate_content_element with trigger wraps in trigger element
# ---------------------------------------------------------------------------


def test_generate_content_element_trigger_wrapping():
    """Field with trigger produces a trigger wrapper element."""
    field = ResolvedField(
        name="society_id", canvas="main", type="text",
        param="societyid", x=1.0, y=2.0, x2=50.0, y2=5.0,
        trigger="societyid",
    )

    element = _generate_content_element(field)

    assert element["type"] == "trigger"
    assert element["trigger"] == "param:societyid"
    assert "content" in element
    assert len(element["content"]) == 1
    inner = element["content"][0]
    assert inner["value"] == "param:societyid"
    assert inner["type"] == "text"
    assert inner["canvas"] == "main"


# ---------------------------------------------------------------------------
# 7. Output key ordering
# ---------------------------------------------------------------------------


def test_output_key_ordering():
    """Output keys appear in the specified order."""
    blueprint = _make_blueprint(
        parent="parent.bp",
        description="Test layout",
        flags=["hidden"],
        aspectratio="603:783",
        default_chronicle_location="modules/chronicles/",
    )
    resolved = _make_resolved_page()
    params = {"Group": {"p1": {"type": "text"}}}
    fields = [
        ResolvedField(
            name="f1", canvas="page", type="text",
            param="p1", x=0.0, y=0.0, x2=100.0, y2=10.0,
        ),
    ]

    layout = assemble_layout(
        blueprint, resolved, resolved,
        resolved_fields=fields, merged_parameters=params,
    )

    expected_order = [
        "id", "parent", "description", "flags", "aspectratio",
        "defaultChronicleLocation", "parameters", "canvas", "content",
    ]
    actual_keys = list(layout.keys())
    assert actual_keys == expected_order


# ---------------------------------------------------------------------------
# 8. Backward compatibility: no parameters/fields -> same output as before
# ---------------------------------------------------------------------------


def test_backward_compatibility_canvas_only():
    """Canvas-only Blueprint produces output without parameters, content, or defaultChronicleLocation."""
    blueprint = _make_blueprint()
    resolved = _make_resolved_page()

    layout = assemble_layout(blueprint, resolved, resolved)

    assert "parameters" not in layout
    assert "content" not in layout
    assert "defaultChronicleLocation" not in layout
    assert "id" in layout
    assert "canvas" in layout


# ---------------------------------------------------------------------------
# 9. Only non-None styling properties are included
# ---------------------------------------------------------------------------


def test_only_non_none_styling_properties_included():
    """Content element omits styling properties that are None."""
    field = ResolvedField(
        name="char", canvas="page", type="text",
        param="char", x=1.0, y=2.0, x2=50.0, y2=5.0,
        font="Helvetica", fontsize=14,
    )

    element = _generate_content_element(field)

    assert element["font"] == "Helvetica"
    assert element["fontsize"] == 14
    assert "fontweight" not in element
    assert "align" not in element
    assert "color" not in element
    assert "linewidth" not in element
    assert "size" not in element
    assert "lines" not in element


# ---------------------------------------------------------------------------
# 10. Content elements include coordinates
# ---------------------------------------------------------------------------


def test_content_element_includes_coordinates():
    """Content element includes x, y, x2, y2 from resolved field."""
    field = ResolvedField(
        name="xp", canvas="page", type="text",
        param="xp", x=10.5, y=20.3, x2=45.0, y2=25.7,
    )

    element = _generate_content_element(field)

    assert element["x"] == pytest.approx(10.5)
    assert element["y"] == pytest.approx(20.3)
    assert element["x2"] == pytest.approx(45.0)
    assert element["y2"] == pytest.approx(25.7)


# ---------------------------------------------------------------------------
# 11. Content elements are in field declaration order
# ---------------------------------------------------------------------------


def test_content_elements_in_field_declaration_order():
    """Content elements appear in the same order as resolved fields."""
    blueprint = _make_blueprint()
    resolved = _make_resolved_page()
    fields = [
        ResolvedField(
            name="first", canvas="page", type="text",
            param="a", x=0.0, y=0.0, x2=50.0, y2=10.0,
        ),
        ResolvedField(
            name="second", canvas="page", type="text",
            param="b", x=0.0, y=10.0, x2=50.0, y2=20.0,
        ),
        ResolvedField(
            name="third", canvas="page", type="text",
            param="c", x=0.0, y=20.0, x2=50.0, y2=30.0,
        ),
    ]

    layout = assemble_layout(blueprint, resolved, resolved, resolved_fields=fields)

    assert len(layout["content"]) == 3
    assert layout["content"][0]["value"] == "param:a"
    assert layout["content"][1]["value"] == "param:b"
    assert layout["content"][2]["value"] == "param:c"
