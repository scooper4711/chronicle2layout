"""Property-based tests for data-mode layout loading functions.

Uses Hypothesis to verify universal properties across randomized inputs.
Each property test runs a minimum of 100 iterations.

Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.5, 7.1-7.6
"""

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from layout_visualizer.layout_loader import (
    merge_parameters,
    merge_presets,
    resolve_entry_presets,
)


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

_identifier = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=12,
)

_param_def = st.fixed_dictionaries({
    "type": st.just("text"),
    "example": st.one_of(
        st.text(min_size=1, max_size=20),
        st.integers(min_value=-1000, max_value=1000),
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
    ),
})

_preset_props = st.dictionaries(
    keys=st.sampled_from(["font", "fontsize", "fontweight", "align", "canvas", "x", "y"]),
    values=st.one_of(
        st.text(min_size=1, max_size=10),
        st.integers(min_value=0, max_value=100),
    ),
    min_size=1,
    max_size=4,
)


def _chain_strategy(min_depth: int = 1, max_depth: int = 5):
    """Generate a list of layout dicts for a fake inheritance chain.

    Each layout has a ``parameters`` section with 1-3 groups, each
    containing 1-3 parameters, and a ``presets`` section with 1-3 presets.
    """
    param_group = st.dictionaries(keys=_identifier, values=_param_def, min_size=1, max_size=3)
    param_section = st.dictionaries(keys=_identifier, values=param_group, min_size=1, max_size=3)
    preset_section = st.dictionaries(keys=_identifier, values=_preset_props, min_size=1, max_size=3)

    layout = st.fixed_dictionaries({
        "parameters": param_section,
        "presets": preset_section,
    })

    return st.lists(layout, min_size=min_depth, max_size=max_depth)


def _make_chain(layouts: list[dict]) -> list[tuple[Path, dict]]:
    """Build a fake chain from a list of layout dicts."""
    return [(Path(f"/fake/{i}.json"), data) for i, data in enumerate(layouts)]


# ---------------------------------------------------------------------------
# Property 1: Inheritance merge with child override
# Feature: layout-data-mode, Property 1: Inheritance merge with child override
# ---------------------------------------------------------------------------

class TestInheritanceMergeWithChildOverride:
    """**Validates: Requirements 2.1, 2.2, 3.3**

    For any chain of layout dicts (length 1-5) where each dict has a
    parameters section and a presets section, merging from root to leaf
    shall produce a result containing every parameter/preset name from
    every layout in the chain, and when the same name appears in both
    a parent and a child, the child's definition shall be present.
    """

    @given(layouts=_chain_strategy())
    @settings(max_examples=100, deadline=None)
    def test_merged_parameters_contain_all_names_and_child_wins(
        self,
        layouts: list[dict],
    ) -> None:
        """All parameter names appear in the merge; child overrides parent.

        Feature: layout-data-mode, Property 1: Inheritance merge with child override
        """
        chain = _make_chain(layouts)
        merged = merge_parameters(chain)

        # Collect all parameter names across all layouts
        all_names: set[str] = set()
        for layout in layouts:
            for group in layout["parameters"].values():
                all_names.update(group.keys())

        assert set(merged.keys()) == all_names

        # For each name, the last layout defining it should win
        for name in all_names:
            last_def = None
            for layout in layouts:
                for group in layout["parameters"].values():
                    if name in group:
                        last_def = group[name]
            assert merged[name] == last_def

    @given(layouts=_chain_strategy())
    @settings(max_examples=100, deadline=None)
    def test_merged_presets_contain_all_names_and_child_wins(
        self,
        layouts: list[dict],
    ) -> None:
        """All preset names appear in the merge; child overrides parent.

        Feature: layout-data-mode, Property 1: Inheritance merge with child override
        """
        chain = _make_chain(layouts)
        merged = merge_presets(chain)

        all_names: set[str] = set()
        for layout in layouts:
            all_names.update(layout["presets"].keys())

        assert set(merged.keys()) == all_names

        for name in all_names:
            last_def = None
            for layout in layouts:
                if name in layout["presets"]:
                    last_def = layout["presets"][name]
            assert merged[name] == last_def


# ---------------------------------------------------------------------------
# Property 2: Preset resolution with inline override
# Feature: layout-data-mode, Property 2: Preset resolution with inline override
# ---------------------------------------------------------------------------

def _preset_chain_strategy():
    """Generate a preset dict with nested references up to depth 3.

    Returns a tuple of (presets_dict, entry_dict, expected_inline_keys).
    """
    prop_key = st.sampled_from(["font", "fontsize", "fontweight", "align", "x", "y"])
    prop_val = st.one_of(
        st.text(min_size=1, max_size=10),
        st.integers(min_value=0, max_value=100),
    )

    # Level 0 (deepest) preset — no nested references
    level0_props = st.dictionaries(keys=prop_key, values=prop_val, min_size=1, max_size=3)
    # Level 1 preset — references level 0
    level1_props = st.dictionaries(keys=prop_key, values=prop_val, min_size=1, max_size=3)
    # Level 2 preset — references level 1
    level2_props = st.dictionaries(keys=prop_key, values=prop_val, min_size=1, max_size=3)
    # Inline overrides on the entry
    inline_props = st.dictionaries(keys=prop_key, values=prop_val, min_size=0, max_size=3)

    return st.tuples(level0_props, level1_props, level2_props, inline_props)


class TestPresetResolutionWithInlineOverride:
    """**Validates: Requirements 3.1, 3.2**

    For any content entry with a presets array referencing a chain of
    preset definitions (including nested references up to depth 3),
    the resolved entry shall contain all properties from the preset
    chain as defaults, and every inline property shall override the
    corresponding preset value.
    """

    @given(data=_preset_chain_strategy())
    @settings(max_examples=100, deadline=None)
    def test_inline_overrides_preset_chain(
        self,
        data: tuple[dict, dict, dict, dict],
    ) -> None:
        """Inline entry properties override all preset chain values.

        Feature: layout-data-mode, Property 2: Preset resolution with inline override
        """
        level0_props, level1_props, level2_props, inline_props = data

        presets = {
            "level0": level0_props,
            "level1": {**level1_props, "presets": ["level0"]},
            "level2": {**level2_props, "presets": ["level1"]},
        }

        entry = {**inline_props, "type": "text", "presets": ["level2"]}

        resolved = resolve_entry_presets(entry, presets)

        # All inline properties must be present and win
        for key, value in inline_props.items():
            assert resolved[key] == value

        # All preset properties should be present as defaults
        # (unless overridden by inline or a later preset)
        expected: dict = {}
        expected.update(level0_props)
        expected.update(level1_props)
        expected.update(level2_props)
        expected.update(inline_props)
        expected["type"] = "text"

        for key, value in expected.items():
            assert resolved[key] == value


# ---------------------------------------------------------------------------
# Property 3: Example value stringification
# Feature: layout-data-mode, Property 3: Example value stringification
# ---------------------------------------------------------------------------

_example_value = st.one_of(
    st.text(min_size=1, max_size=30),
    st.integers(min_value=-10000, max_value=10000),
    st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False),
)


class TestExampleValueStringification:
    """**Validates: Requirements 2.3, 4.5**

    For any parameter definition with an example field whose value is
    an int, float, or string, the resolved example text shall equal
    ``str(example)``.
    """

    @given(example=_example_value)
    @settings(max_examples=100, deadline=None)
    def test_example_converted_to_str(
        self,
        tmp_path_factory,
        example,
    ) -> None:
        """The example value is always converted via str().

        Feature: layout-data-mode, Property 3: Example value stringification
        """
        import json

        from layout_visualizer.layout_loader import build_layout_index, load_data_content

        tmp_dir = tmp_path_factory.mktemp("stringify")
        layout_data = {
            "id": "test",
            "canvas": {"page": {"x": 0, "y": 0, "x2": 100, "y2": 100}},
            "parameters": {"G": {"p": {"type": "text", "example": example}}},
            "content": [{
                "value": "param:p",
                "type": "text",
                "canvas": "page",
                "x": 0, "y": 0, "x2": 50, "y2": 10,
                "font": "Helvetica", "fontsize": 12, "align": "LB",
            }],
        }
        layout_path = tmp_dir / "layout.json"
        layout_path.write_text(json.dumps(layout_data), encoding="utf-8")
        index = build_layout_index(tmp_dir)

        entries, _, _ = load_data_content(layout_path, index)

        assert len(entries) == 1
        assert entries[0].example_value == str(example)


# ---------------------------------------------------------------------------
# Property 6: Non-text type filtering
# Feature: layout-data-mode, Property 6: Non-text type filtering
# ---------------------------------------------------------------------------

_text_entry_type = st.sampled_from(["text", "multiline"])
_skip_entry_type = st.sampled_from(["checkbox", "strikeout", "line", "rectangle"])


def _content_entry_strategy(entry_type_st, param_name: str = "p"):
    """Generate a content entry dict with the given type strategy."""
    return entry_type_st.map(lambda t: {
        "value": f"param:{param_name}",
        "type": t,
        "canvas": "page",
        "x": 0, "y": 0, "x2": 50, "y2": 10,
        "font": "Helvetica", "fontsize": 12, "align": "LB",
        **({"lines": 2} if t == "multiline" else {}),
    })


def _mixed_content_strategy():
    """Generate a mixed content array with text and non-text entries.

    Returns (content_list, expected_text_count).
    """
    text_entries = st.lists(
        _content_entry_strategy(_text_entry_type),
        min_size=1, max_size=5,
    )
    skip_entries = st.lists(
        _content_entry_strategy(_skip_entry_type),
        min_size=1, max_size=5,
    )
    return st.tuples(text_entries, skip_entries)


class TestNonTextTypeFiltering:
    """**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

    For any content array containing entries of types checkbox,
    strikeout, line, and rectangle intermixed with text and multiline
    entries, the extracted data content entries shall contain only the
    text and multiline entries.
    """

    @given(data=_mixed_content_strategy())
    @settings(max_examples=100, deadline=None)
    def test_only_text_and_multiline_survive(
        self,
        tmp_path_factory,
        data: tuple[list[dict], list[dict]],
    ) -> None:
        """Non-text types are filtered out; text/multiline are kept.

        Feature: layout-data-mode, Property 6: Non-text type filtering
        """
        import json

        from layout_visualizer.layout_loader import build_layout_index, load_data_content

        text_entries, skip_entries = data
        all_content = text_entries + skip_entries

        tmp_dir = tmp_path_factory.mktemp("filter")
        layout_data = {
            "id": "test",
            "canvas": {"page": {"x": 0, "y": 0, "x2": 100, "y2": 100}},
            "parameters": {"G": {"p": {"type": "text", "example": "val"}}},
            "content": all_content,
        }
        layout_path = tmp_dir / "layout.json"
        layout_path.write_text(json.dumps(layout_data), encoding="utf-8")
        index = build_layout_index(tmp_dir)

        entries, _, _ = load_data_content(layout_path, index)

        assert len(entries) == len(text_entries)
        for entry in entries:
            assert entry.entry_type in {"text", "multiline"}


# ---------------------------------------------------------------------------
# Property 7: Nested content extraction from trigger and choice
# Feature: layout-data-mode, Property 7: Nested content extraction from trigger and choice
# ---------------------------------------------------------------------------

def _make_text_entry(param_name: str) -> dict:
    """Create a minimal text content entry referencing a parameter."""
    return {
        "value": f"param:{param_name}",
        "type": "text",
        "canvas": "page",
        "x": 0, "y": 0, "x2": 50, "y2": 10,
        "font": "Helvetica", "fontsize": 12, "align": "LB",
    }


def _nested_content_strategy():
    """Generate content arrays with trigger/choice wrappers around text entries.

    Returns (content_list, expected_param_names).
    """
    # Number of top-level text entries
    top_count = st.integers(min_value=0, max_value=3)
    # Number of text entries inside a trigger
    trigger_count = st.integers(min_value=0, max_value=3)
    # Number of choice branches, each with 0-2 text entries
    choice_branch_counts = st.lists(
        st.integers(min_value=0, max_value=2),
        min_size=0, max_size=3,
    )

    return st.tuples(top_count, trigger_count, choice_branch_counts)


class TestNestedContentExtraction:
    """**Validates: Requirements 7.5, 7.6**

    For any content array containing trigger entries (with nested
    content arrays) and choice entries (with nested content maps),
    the extracted data content entries shall include all text and
    multiline entries found at any nesting depth.
    """

    @given(data=_nested_content_strategy())
    @settings(max_examples=100, deadline=None)
    def test_all_nested_text_entries_extracted(
        self,
        tmp_path_factory,
        data: tuple[int, int, list[int]],
    ) -> None:
        """Text entries inside triggers and choices are all extracted.

        Feature: layout-data-mode, Property 7: Nested content extraction from trigger and choice
        """
        import json

        from layout_visualizer.layout_loader import build_layout_index, load_data_content

        top_count, trigger_count, choice_branch_counts = data

        param_counter = [0]
        all_param_names: list[str] = []
        content: list[dict] = []

        def next_param() -> str:
            name = f"p{param_counter[0]}"
            param_counter[0] += 1
            all_param_names.append(name)
            return name

        # Top-level text entries
        for _ in range(top_count):
            content.append(_make_text_entry(next_param()))

        # Trigger with nested text entries
        if trigger_count > 0:
            trigger_content = [_make_text_entry(next_param()) for _ in range(trigger_count)]
            content.append({
                "type": "trigger",
                "trigger": "some_param",
                "content": trigger_content,
            })

        # Choice with branches
        if choice_branch_counts:
            choice_content: dict[str, list] = {}
            for i, branch_count in enumerate(choice_branch_counts):
                branch = [_make_text_entry(next_param()) for _ in range(branch_count)]
                choice_content[f"option_{i}"] = branch
            content.append({
                "type": "choice",
                "choices": "some_param",
                "content": choice_content,
            })

        # Build parameters for all referenced names
        params = {name: {"type": "text", "example": f"val_{name}"} for name in all_param_names}

        tmp_dir = tmp_path_factory.mktemp("nested")
        layout_data = {
            "id": "test",
            "canvas": {"page": {"x": 0, "y": 0, "x2": 100, "y2": 100}},
            "parameters": {"G": params},
            "content": content,
        }
        layout_path = tmp_dir / "layout.json"
        layout_path.write_text(json.dumps(layout_data), encoding="utf-8")
        index = build_layout_index(tmp_dir)

        entries, _, _ = load_data_content(layout_path, index)

        extracted_names = {e.param_name for e in entries}
        assert extracted_names == set(all_param_names)
        assert len(entries) == len(all_param_names)
