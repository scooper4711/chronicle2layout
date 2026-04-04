"""Property-based tests for extended layout assembly with parameters and content.

Uses Hypothesis to verify universal correctness properties for content
element generation, trigger wrapping, output scoping, backward
compatibility, JSON round-trip stability, and section ordering.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8,
    10.2, 11.1, 11.4, 13.6, 14.1, 14.2, 14.3
"""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from blueprint2layout.models import Blueprint, CanvasEntry, ResolvedCanvas, ResolvedField
from blueprint2layout.output import assemble_layout, _generate_content_element


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_percentage = st.floats(
    min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False,
)

_canvas_name = st.sampled_from(["page", "main", "sidebar"])

_field_type = st.sampled_from(["text", "multiline", "line", "rectangle"])

_font_name = st.sampled_from(["Helvetica", "Arial", "Courier", "Times"])

_fontsize = st.floats(
    min_value=6.0, max_value=72.0, allow_nan=False, allow_infinity=False,
)

_fontweight = st.sampled_from(["bold", "normal"])

_align = st.sampled_from(["CM", "LB", "LM", "RB", "RT", "CB"])

_color = st.sampled_from(["black", "red", "#333333"])

_linewidth = st.floats(
    min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False,
)

_size = st.floats(
    min_value=1.0, max_value=50.0, allow_nan=False, allow_infinity=False,
)

_lines_count = st.integers(min_value=1, max_value=10)

_param_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=15,
)

_static_value = st.text(min_size=1, max_size=30)

_trigger_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=15,
)


@st.composite
def resolved_field_with_param(draw):
    """Generate a ResolvedField with a param value and random styling."""
    return ResolvedField(
        name=draw(_param_name),
        canvas=draw(_canvas_name),
        type=draw(_field_type),
        param=draw(_param_name),
        x=draw(_percentage),
        y=draw(_percentage),
        x2=draw(_percentage),
        y2=draw(_percentage),
        font=draw(st.one_of(st.none(), _font_name)),
        fontsize=draw(st.one_of(st.none(), _fontsize)),
        fontweight=draw(st.one_of(st.none(), _fontweight)),
        align=draw(st.one_of(st.none(), _align)),
        color=draw(st.one_of(st.none(), _color)),
        linewidth=draw(st.one_of(st.none(), _linewidth)),
        size=draw(st.one_of(st.none(), _size)),
        lines=draw(st.one_of(st.none(), _lines_count)),
    )


@st.composite
def resolved_field_with_value(draw):
    """Generate a ResolvedField with a static value and random styling."""
    return ResolvedField(
        name=draw(_param_name),
        canvas=draw(_canvas_name),
        type=draw(_field_type),
        value=draw(_static_value),
        x=draw(_percentage),
        y=draw(_percentage),
        x2=draw(_percentage),
        y2=draw(_percentage),
        font=draw(st.one_of(st.none(), _font_name)),
        fontsize=draw(st.one_of(st.none(), _fontsize)),
        fontweight=draw(st.one_of(st.none(), _fontweight)),
        align=draw(st.one_of(st.none(), _align)),
        color=draw(st.one_of(st.none(), _color)),
        linewidth=draw(st.one_of(st.none(), _linewidth)),
        size=draw(st.one_of(st.none(), _size)),
        lines=draw(st.one_of(st.none(), _lines_count)),
    )


@st.composite
def resolved_field_any(draw):
    """Generate a ResolvedField with either param or value, no trigger."""
    return draw(st.one_of(resolved_field_with_param(), resolved_field_with_value()))


@st.composite
def resolved_field_with_trigger(draw):
    """Generate a ResolvedField with a trigger property set."""
    field = draw(resolved_field_with_param())
    trigger = draw(_trigger_name)
    return ResolvedField(
        name=field.name,
        canvas=field.canvas,
        type=field.type,
        param=field.param,
        x=field.x,
        y=field.y,
        x2=field.x2,
        y2=field.y2,
        font=field.font,
        fontsize=field.fontsize,
        fontweight=field.fontweight,
        align=field.align,
        color=field.color,
        linewidth=field.linewidth,
        size=field.size,
        lines=field.lines,
        trigger=trigger,
    )


# Strategy for parameter definition values
_param_definition = st.fixed_dictionaries(
    {"type": st.just("text")},
    optional={"description": st.text(min_size=1, max_size=30)},
)

_param_group = st.dictionaries(
    keys=st.text(min_size=1, max_size=15),
    values=_param_definition,
    min_size=1,
    max_size=3,
)

_parameters_dict = st.dictionaries(
    keys=st.text(min_size=1, max_size=15),
    values=_param_group,
    min_size=1,
    max_size=3,
)

_STYLING_KEYS = ("font", "fontsize", "fontweight", "align",
                 "color", "linewidth", "size", "lines")


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
    return {
        "page": ResolvedCanvas(
            name="page", left=0.0, right=100.0, top=0.0, bottom=100.0,
        ),
    }


# ---------------------------------------------------------------------------
# Property 9: Content element generation preserves field properties
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 9: Content element generation preserves field properties


class TestContentElementPreservesFieldProperties:
    """**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.8**

    For any ResolvedField, the generated content element SHALL contain
    the field's type, canvas, coordinates, and all non-None styling
    properties.
    """

    @given(field=resolved_field_with_param())
    @settings(max_examples=100)
    def test_param_field_value_and_type(self, field: ResolvedField) -> None:
        """Content element has value 'param:<name>' and correct type."""
        element = _generate_content_element(field)

        assert element["value"] == f"param:{field.param}"
        assert element["type"] == field.type

    @given(field=resolved_field_with_value())
    @settings(max_examples=100)
    def test_value_field_static_text(self, field: ResolvedField) -> None:
        """Content element has the static text as value."""
        element = _generate_content_element(field)

        assert element["value"] == field.value
        assert element["type"] == field.type

    @given(field=resolved_field_any())
    @settings(max_examples=100)
    def test_canvas_preserved(self, field: ResolvedField) -> None:
        """Content element contains the field's canvas name."""
        element = _generate_content_element(field)

        assert element["canvas"] == field.canvas

    @given(field=resolved_field_any())
    @settings(max_examples=100)
    def test_coordinates_preserved(self, field: ResolvedField) -> None:
        """Content element contains x, y, x2, y2 from the field."""
        element = _generate_content_element(field)

        assert element["x"] == field.x
        assert element["y"] == field.y
        assert element["x2"] == field.x2
        assert element["y2"] == field.y2

    @given(field=resolved_field_any())
    @settings(max_examples=100)
    def test_non_none_styling_properties_included(
        self, field: ResolvedField,
    ) -> None:
        """All non-None styling properties appear in the content element."""
        element = _generate_content_element(field)

        for key in _STYLING_KEYS:
            field_value = getattr(field, key)
            if field_value is not None:
                assert key in element
                assert element[key] == field_value
            else:
                assert key not in element

    @given(fields=st.lists(resolved_field_any(), min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_content_array_length_and_order(
        self, fields: list[ResolvedField],
    ) -> None:
        """assemble_layout content array matches field list length and order."""
        blueprint = _make_blueprint()
        resolved = _make_resolved_page()

        layout = assemble_layout(
            blueprint, resolved, resolved, resolved_fields=fields,
        )

        assert len(layout["content"]) == len(fields)
        for i, field in enumerate(fields):
            element = layout["content"][i]
            assert element["type"] == field.type


# ---------------------------------------------------------------------------
# Property 10: Trigger fields produce wrapper elements
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 10: Trigger fields produce wrapper elements


class TestTriggerFieldsProduceWrapperElements:
    """**Validates: Requirements 9.7**

    For any ResolvedField with a trigger, the generated element SHALL
    be a trigger wrapper.
    """

    @given(field=resolved_field_with_trigger())
    @settings(max_examples=100)
    def test_trigger_wrapper_structure(self, field: ResolvedField) -> None:
        """Trigger field produces a wrapper with type='trigger'."""
        element = _generate_content_element(field)

        assert element["type"] == "trigger"
        assert element["trigger"] == f"param:{field.trigger}"
        assert "content" in element
        assert len(element["content"]) == 1

    @given(field=resolved_field_with_trigger())
    @settings(max_examples=100)
    def test_trigger_inner_element_preserves_properties(
        self, field: ResolvedField,
    ) -> None:
        """Inner element inside trigger wrapper has correct field properties."""
        element = _generate_content_element(field)
        inner = element["content"][0]

        assert inner["value"] == f"param:{field.param}"
        assert inner["type"] == field.type
        assert inner["canvas"] == field.canvas
        assert inner["x"] == field.x
        assert inner["y"] == field.y
        assert inner["x2"] == field.x2
        assert inner["y2"] == field.y2


# ---------------------------------------------------------------------------
# Property 11: Output contains only child Blueprint's fields
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 11: Output contains only child Blueprint's fields


class TestOutputContainsOnlyChildFields:
    """**Validates: Requirements 10.2**

    The output content section SHALL contain elements only from the
    provided resolved_fields list.
    """

    @given(fields=st.lists(resolved_field_any(), min_size=0, max_size=5))
    @settings(max_examples=100)
    def test_content_length_matches_input_fields(
        self, fields: list[ResolvedField],
    ) -> None:
        """Content section length equals the resolved_fields list length."""
        blueprint = _make_blueprint()
        resolved = _make_resolved_page()

        layout = assemble_layout(
            blueprint, resolved, resolved, resolved_fields=fields,
        )

        if len(fields) == 0:
            assert "content" not in layout
        else:
            assert len(layout["content"]) == len(fields)


# ---------------------------------------------------------------------------
# Property 12: Canvas-only Blueprints produce backward-compatible output
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 12: Canvas-only Blueprints produce backward-compatible output


class TestCanvasOnlyBackwardCompatibility:
    """**Validates: Requirements 11.4, 13.6**

    When no parameters, fields, or defaultChronicleLocation are
    provided, the output SHALL not contain those keys.
    """

    @given(
        bp_id=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"), whitelist_characters="._",
            ),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_no_extra_keys_for_canvas_only_blueprint(self, bp_id: str) -> None:
        """Canvas-only Blueprint output has no parameters/content/defaultChronicleLocation."""
        blueprint = _make_blueprint(id=bp_id)
        resolved = _make_resolved_page()

        layout = assemble_layout(blueprint, resolved, resolved)

        assert "parameters" not in layout
        assert "content" not in layout
        assert "defaultChronicleLocation" not in layout
        assert "id" in layout
        assert "canvas" in layout

    @given(
        bp_id=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"), whitelist_characters="._",
            ),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_canvas_only_output_keys_are_minimal(self, bp_id: str) -> None:
        """Canvas-only Blueprint output contains only id and canvas keys."""
        blueprint = _make_blueprint(id=bp_id)
        resolved = _make_resolved_page()

        layout = assemble_layout(blueprint, resolved, resolved)

        assert set(layout.keys()) == {"id", "canvas"}


# ---------------------------------------------------------------------------
# Property 13: Output JSON round-trip stability
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 13: Output JSON round-trip stability


class TestOutputJsonRoundTripStability:
    """**Validates: Requirements 14.1, 14.2, 14.3**

    Serializing the output to JSON and deserializing back SHALL
    produce an equal dictionary.
    """

    @given(
        fields=st.lists(resolved_field_any(), min_size=1, max_size=3),
        params=_parameters_dict,
    )
    @settings(max_examples=100)
    def test_json_round_trip_with_params_and_content(
        self, fields: list[ResolvedField], params: dict,
    ) -> None:
        """Full layout with parameters and content survives JSON round-trip."""
        blueprint = _make_blueprint()
        resolved = _make_resolved_page()

        layout = assemble_layout(
            blueprint, resolved, resolved,
            resolved_fields=fields, merged_parameters=params,
        )

        serialized = json.dumps(layout)
        deserialized = json.loads(serialized)

        assert deserialized == layout

    @given(fields=st.lists(resolved_field_any(), min_size=1, max_size=3))
    @settings(max_examples=100)
    def test_json_round_trip_content_only(
        self, fields: list[ResolvedField],
    ) -> None:
        """Layout with content only survives JSON round-trip."""
        blueprint = _make_blueprint()
        resolved = _make_resolved_page()

        layout = assemble_layout(
            blueprint, resolved, resolved, resolved_fields=fields,
        )

        serialized = json.dumps(layout)
        deserialized = json.loads(serialized)

        assert deserialized == layout

    @given(
        fields=st.lists(resolved_field_any(), min_size=1, max_size=3),
        params=_parameters_dict,
    )
    @settings(max_examples=100)
    def test_all_values_are_builtin_types(
        self, fields: list[ResolvedField], params: dict,
    ) -> None:
        """All values in the output dict tree are Python built-in types."""
        blueprint = _make_blueprint()
        resolved = _make_resolved_page()

        layout = assemble_layout(
            blueprint, resolved, resolved,
            resolved_fields=fields, merged_parameters=params,
        )

        _assert_builtin_types(layout)


def _assert_builtin_types(value: object) -> None:
    """Recursively assert all values are Python built-in types."""
    assert isinstance(value, (dict, list, float, int, str, bool))
    if isinstance(value, dict):
        for k, v in value.items():
            assert isinstance(k, str)
            _assert_builtin_types(v)
    elif isinstance(value, list):
        for item in value:
            _assert_builtin_types(item)


# ---------------------------------------------------------------------------
# Property 17: Output section ordering
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 17: Output section ordering


_EXPECTED_KEY_ORDER = [
    "id", "parent", "description", "flags", "aspectratio",
    "defaultChronicleLocation", "parameters", "canvas", "content",
]


class TestOutputSectionOrdering:
    """**Validates: Requirements 11.1**

    The output keys SHALL appear in the specified order.
    """

    @given(
        fields=st.lists(resolved_field_any(), min_size=1, max_size=3),
        params=_parameters_dict,
        description=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
        parent=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
        flags=st.one_of(st.just([]), st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=2)),
        aspectratio=st.one_of(st.none(), st.just("603:783")),
        chronicle_location=st.one_of(st.none(), st.text(min_size=1, max_size=40)),
    )
    @settings(max_examples=100)
    def test_keys_appear_in_specified_order(
        self,
        fields: list[ResolvedField],
        params: dict,
        description: str | None,
        parent: str | None,
        flags: list[str],
        aspectratio: str | None,
        chronicle_location: str | None,
    ) -> None:
        """Output keys follow the canonical ordering."""
        blueprint = _make_blueprint(
            parent=parent,
            description=description,
            flags=flags,
            aspectratio=aspectratio,
            default_chronicle_location=chronicle_location,
        )
        resolved = _make_resolved_page()

        layout = assemble_layout(
            blueprint, resolved, resolved,
            resolved_fields=fields, merged_parameters=params,
        )

        actual_keys = list(layout.keys())
        # Filter expected order to only keys present in output
        expected_keys = [k for k in _EXPECTED_KEY_ORDER if k in actual_keys]

        assert actual_keys == expected_keys
