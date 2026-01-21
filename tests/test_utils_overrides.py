"""Unit tests for ``r2x_core.utils.overrides.override_dictionary``."""

from r2x_core.utils.overrides import override_dictionary


def test_override_dictionary_adds_new_keys_without_mutating_base():
    base = {"a": 1}
    overrides = {"b": 2}
    result = override_dictionary(base, overrides=overrides)

    assert result == {"a": 1, "b": 2}
    assert base == {"a": 1}


def test_override_dictionary_replaces_scalars():
    base = {"a": 1}
    overrides = {"a": 3}
    result = override_dictionary(base, overrides=overrides)

    assert result["a"] == 3


def test_override_dictionary_merges_list_with_shorter_override():
    base = {"items": [1, 2, 3]}
    overrides = {"items": [9]}
    result = override_dictionary(base, overrides=overrides)

    assert result["items"] == [9, 2, 3]


def test_override_dictionary_merges_list_with_longer_override():
    base = {"items": [1]}
    overrides = {"items": [9, 10]}
    result = override_dictionary(base, overrides=overrides)

    assert result["items"] == [9, 10]


def test_override_dictionary_merges_nested_dicts_and_lists():
    base = {"nested": {"choices": ["a", "b"], "value": 1}}
    overrides = {"nested": {"choices": ["x"], "value": 2}}
    result = override_dictionary(base, overrides=overrides)

    assert result["nested"]["choices"] == ["x", "b"]
    assert result["nested"]["value"] == 2
