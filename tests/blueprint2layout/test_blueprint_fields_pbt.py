"""Property-based tests for extended Blueprint parsing with parameters, fields, and styles.

Uses Hypothesis to verify universal correctness properties across
randomly generated inputs.

Validates: Requirements 1.2, 1.4, 2.1, 2.2, 2.3, 2.4, 3.2, 3.4, 6.8
"""

from hypothesis import given, settings
from hypothesis import strategies as st
import pytest

from blueprint2layout.blueprint import (
    _merge_field_styles,
    _merge_parameters,
    parse_blueprint,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for parameter definition values (simple dicts with string keys/values)
_param_definition = st.fixed_dictionaries(
    {"type": st.just("text")},
    optional={"description": st.text(min_size=1, max_size=30)},
)

# Strategy for a single parameter group (dict of param definitions)
_param_group = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=_param_definition,
    min_size=1,
    max_size=5,
)

# Strategy for a full parameters dict (dict of groups)
_parameters_dict = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=_param_group,
    min_size=1,
    max_size=4,
)

# Strategy for defaultChronicleLocation strings
_chronicle_location = st.text(min_size=1, max_size=80)

# Strategy for field style definition dicts (simple property bundles)
_style_definition = st.fixed_dictionaries(
    {},
    optional={
        "font": st.text(min_size=1, max_size=20),
        "fontsize": st.integers(min_value=6, max_value=72),
        "fontweight": st.sampled_from(["bold", "normal"]),
        "align": st.sampled_from(["CM", "LB", "LM", "RB"]),
        "color": st.text(min_size=1, max_size=10),
    },
)

# Strategy for field_styles dicts (style name → definition)
_field_styles_dict = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
        min_size=1,
        max_size=15,
    ),
    values=_style_definition,
    min_size=1,
    max_size=5,
)

# Strategy for non-dict values (used in Property 14)
_non_dict_values = st.one_of(
    st.integers(),
    st.text(min_size=1, max_size=10),
    st.lists(st.integers(), max_size=3),
    st.just(True),
    st.just(None),
)

# Strategy for non-string values (used in Property 14)
_non_string_values = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.dictionaries(keys=st.text(max_size=5), values=st.text(max_size=5), max_size=2),
    st.lists(st.integers(), max_size=3),
    st.just(True),
)


def _minimal_blueprint_data(bp_id: str = "test.bp", **extras) -> dict:
    """Build a minimal Blueprint JSON dict with optional extras."""
    return {"id": bp_id, "canvases": [], **extras}


# ---------------------------------------------------------------------------
# Property 1: Pass-through properties round-trip
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 1: Pass-through properties round-trip


class TestPassThroughRoundTrip:
    """**Validates: Requirements 1.2, 3.2**

    For any valid Blueprint with parameters and/or defaultChronicleLocation,
    the parsed Blueprint SHALL contain those values exactly as declared.
    """

    @given(params=_parameters_dict)
    @settings(max_examples=100)
    def test_parameters_round_trip(self, params: dict) -> None:
        """Parsed parameters match the input exactly."""
        data = _minimal_blueprint_data(parameters=params)
        result = parse_blueprint(data)

        assert result.parameters == params

    @given(location=_chronicle_location)
    @settings(max_examples=100)
    def test_default_chronicle_location_round_trip(self, location: str) -> None:
        """Parsed defaultChronicleLocation matches the input exactly."""
        data = _minimal_blueprint_data(defaultChronicleLocation=location)
        result = parse_blueprint(data)

        assert result.default_chronicle_location == location

    @given(params=_parameters_dict, location=_chronicle_location)
    @settings(max_examples=100)
    def test_both_properties_round_trip(self, params: dict, location: str) -> None:
        """Both properties survive parsing together."""
        data = _minimal_blueprint_data(
            parameters=params,
            defaultChronicleLocation=location,
        )
        result = parse_blueprint(data)

        assert result.parameters == params
        assert result.default_chronicle_location == location


# ---------------------------------------------------------------------------
# Property 2: Parameter merging preserves all definitions with child-wins override
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 2: Parameter merging preserves all definitions


class TestParameterMergingProperty:
    """**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

    For any parent and child parameter dicts, the merged result SHALL
    contain every group from both, and within shared groups, child's
    definition wins.
    """

    @given(parent=_parameters_dict, child=_parameters_dict)
    @settings(max_examples=100)
    def test_all_groups_present(self, parent: dict, child: dict) -> None:
        """Merged result contains every group from both parent and child."""
        result = _merge_parameters(parent, child)

        assert result is not None
        for group in parent:
            assert group in result
        for group in child:
            assert group in result

    @given(parent=_parameters_dict, child=_parameters_dict)
    @settings(max_examples=100)
    def test_all_params_within_shared_groups(
        self, parent: dict, child: dict,
    ) -> None:
        """Within shared groups, all params from both appear in result."""
        result = _merge_parameters(parent, child)
        assert result is not None

        shared_groups = set(parent) & set(child)
        for group in shared_groups:
            for param_name in parent[group]:
                assert param_name in result[group]
            for param_name in child[group]:
                assert param_name in result[group]

    @given(parent=_parameters_dict, child=_parameters_dict)
    @settings(max_examples=100)
    def test_child_wins_for_shared_params(
        self, parent: dict, child: dict,
    ) -> None:
        """For shared params within shared groups, child's value is used."""
        result = _merge_parameters(parent, child)
        assert result is not None

        shared_groups = set(parent) & set(child)
        for group in shared_groups:
            shared_params = set(parent[group]) & set(child[group])
            for param_name in shared_params:
                assert result[group][param_name] == child[group][param_name]

    @given(parent=_parameters_dict, child=_parameters_dict)
    @settings(max_examples=100)
    def test_parent_only_params_preserved(
        self, parent: dict, child: dict,
    ) -> None:
        """Params only in parent are preserved in shared groups."""
        result = _merge_parameters(parent, child)
        assert result is not None

        shared_groups = set(parent) & set(child)
        for group in shared_groups:
            parent_only = set(parent[group]) - set(child[group])
            for param_name in parent_only:
                assert result[group][param_name] == parent[group][param_name]


# ---------------------------------------------------------------------------
# Property 7: Field style merging is child-overrides-parent
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 7: Field style merging is child-overrides-parent


class TestFieldStyleMergingProperty:
    """**Validates: Requirements 6.8**

    For any parent and child field_styles dicts, child definitions
    override parent for the same name, and all names from both appear.
    """

    @given(parent=_field_styles_dict, child=_field_styles_dict)
    @settings(max_examples=100)
    def test_all_style_names_present(self, parent: dict, child: dict) -> None:
        """Merged result contains all style names from both dicts."""
        result = _merge_field_styles(parent, child)

        assert result is not None
        for name in parent:
            assert name in result
        for name in child:
            assert name in result

    @given(parent=_field_styles_dict, child=_field_styles_dict)
    @settings(max_examples=100)
    def test_child_overrides_parent_for_same_name(
        self, parent: dict, child: dict,
    ) -> None:
        """For shared style names, child's definition wins."""
        result = _merge_field_styles(parent, child)
        assert result is not None

        shared_names = set(parent) & set(child)
        for name in shared_names:
            assert result[name] == child[name]

    @given(parent=_field_styles_dict, child=_field_styles_dict)
    @settings(max_examples=100)
    def test_parent_only_styles_preserved(
        self, parent: dict, child: dict,
    ) -> None:
        """Styles only in parent are preserved unchanged."""
        result = _merge_field_styles(parent, child)
        assert result is not None

        parent_only = set(parent) - set(child)
        for name in parent_only:
            assert result[name] == parent[name]


# ---------------------------------------------------------------------------
# Property 14: Invalid root property types raise errors
# ---------------------------------------------------------------------------
# Feature: blueprint-fields, Property 14: Invalid root property types raise errors


class TestInvalidRootPropertyTypes:
    """**Validates: Requirements 1.4, 3.4**

    For any non-dict parameters or non-string defaultChronicleLocation,
    parse_blueprint raises ValueError.
    """

    @given(bad_params=_non_dict_values)
    @settings(max_examples=100)
    def test_non_dict_parameters_raises(self, bad_params: object) -> None:
        """Non-dict parameters value raises ValueError."""
        data = _minimal_blueprint_data(parameters=bad_params)
        with pytest.raises(ValueError, match="parameters"):
            parse_blueprint(data)

    @given(bad_location=_non_string_values)
    @settings(max_examples=100)
    def test_non_string_chronicle_location_raises(
        self, bad_location: object,
    ) -> None:
        """Non-string defaultChronicleLocation raises ValueError."""
        data = _minimal_blueprint_data(defaultChronicleLocation=bad_location)
        with pytest.raises(ValueError, match="defaultChronicleLocation"):
            parse_blueprint(data)
