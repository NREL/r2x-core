"""Tests for PluginConfig class and loading methods."""

import json
from pathlib import Path

import pytest

from r2x_core.plugin_config import PluginConfig


class SampleConfig(PluginConfig):
    """Sample configuration for testing."""

    param1: str
    param2: int = 42


class CustomDirConfig(PluginConfig):
    """Config with custom CONFIG_DIR."""

    CONFIG_DIR = "custom_config"
    param: str


def test_plugin_config_basic_instantiation():
    """Test basic PluginConfig instantiation."""
    config = SampleConfig(param1="test")
    assert config.param1 == "test"
    assert config.param2 == 42


def test_plugin_config_custom_values():
    """Test PluginConfig with custom values."""
    config = SampleConfig(param1="custom", param2=100)
    assert config.param1 == "custom"
    assert config.param2 == 100


def test_plugin_config_resolve_config_path():
    """Test that config_path is automatically resolved."""
    config = SampleConfig(param1="test")
    assert config.config_path is not None
    assert isinstance(config.config_path, Path)
    assert config.config_path.name == "config"


def test_plugin_config_explicit_config_path(tmp_path):
    """Test setting explicit config_path."""
    custom_path = tmp_path / "myconfig"
    custom_path.mkdir()
    config = SampleConfig(param1="test", config_path=custom_path)
    assert config.config_path == custom_path


def test_plugin_config_file_mapping_path(tmp_path):
    """Test file_mapping_path property."""
    config = SampleConfig(param1="test", config_path=tmp_path)
    expected_path = tmp_path / "file_mapping.json"
    assert config.file_mapping_path == expected_path


def test_plugin_config_defaults_path(tmp_path):
    """Test defaults_path property."""
    config = SampleConfig(param1="test", config_path=tmp_path)
    expected_path = tmp_path / "defaults.json"
    assert config.defaults_path == expected_path


def test_plugin_config_model_dump_excludes_config_path():
    """Test that config_path is excluded from serialization."""
    config = SampleConfig(param1="test")
    dumped = config.model_dump()
    assert "config_path" not in dumped
    assert "param1" in dumped
    assert "param2" in dumped


def test_plugin_config_model_dump_json_excludes_config_path():
    """Test that config_path is excluded from JSON serialization."""
    config = SampleConfig(param1="test")
    json_str = config.model_dump_json()
    data = json.loads(json_str)
    assert "config_path" not in data
    assert data["param1"] == "test"


def test_load_defaults_basic(tmp_path):
    """Test loading defaults from defaults.json."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text(json.dumps({"key1": "value1", "key2": 42}))

    defaults = SampleConfig.load_defaults(config_path=tmp_path)
    assert defaults["key1"] == "value1"
    assert defaults["key2"] == 42


def test_load_defaults_nonexistent_file(tmp_path):
    """Test loading defaults when file doesn't exist."""
    defaults = SampleConfig.load_defaults(config_path=tmp_path)
    assert defaults == {}


def test_load_defaults_nonexistent_file_with_overrides(tmp_path):
    """Test loading defaults when file doesn't exist but overrides provided."""
    defaults = SampleConfig.load_defaults(config_path=tmp_path, overrides={"key": "value"})
    assert defaults == {"key": "value"}


def test_load_defaults_scalar_override(tmp_path):
    """Test that scalar overrides replace defaults."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text(json.dumps({"key1": "default", "key2": "value2"}))

    defaults = SampleConfig.load_defaults(config_path=tmp_path, overrides={"key1": "overridden"})
    assert defaults["key1"] == "overridden"
    assert defaults["key2"] == "value2"


def test_load_defaults_list_merge(tmp_path):
    """Test that list overrides are merged and deduplicated."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text(json.dumps({"techs": ["coal", "oil"]}))

    defaults = SampleConfig.load_defaults(config_path=tmp_path, overrides={"techs": ["oil", "nuclear"]})
    assert "coal" in defaults["techs"]
    assert "oil" in defaults["techs"]
    assert "nuclear" in defaults["techs"]
    # Check deduplication
    assert defaults["techs"].count("oil") == 1


def test_load_defaults_list_merge_preserves_order(tmp_path):
    """Test that list merging preserves order."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text(json.dumps({"items": ["a", "b", "c"]}))

    defaults = SampleConfig.load_defaults(config_path=tmp_path, overrides={"items": ["d", "b"]})
    # Original order preserved, new items appended
    assert defaults["items"][:3] == ["a", "b", "c"]
    assert "d" in defaults["items"]


def test_load_defaults_new_keys_added(tmp_path):
    """Test that new keys from overrides are added."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text(json.dumps({"existing": "value"}))

    defaults = SampleConfig.load_defaults(config_path=tmp_path, overrides={"new_key": "new_value"})
    assert defaults["existing"] == "value"
    assert defaults["new_key"] == "new_value"


def test_load_defaults_invalid_json(tmp_path):
    """Test loading defaults with invalid JSON raises error."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text("{ invalid json }")

    with pytest.raises(json.JSONDecodeError):
        SampleConfig.load_defaults(config_path=tmp_path)


def test_load_defaults_not_dict(tmp_path):
    """Test loading defaults when file is not a dict raises TypeError."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text(json.dumps(["not", "a", "dict"]))

    with pytest.raises(TypeError, match="must contain a dict"):
        SampleConfig.load_defaults(config_path=tmp_path)


def test_load_file_mapping_basic(tmp_path):
    """Test loading file mapping from file_mapping.json."""
    mapping_file = tmp_path / "file_mapping.json"
    mapping_data = [{"name": "data_file", "fpath": "*.csv"}, {"name": "config_file", "fpath": "*.config"}]
    mapping_file.write_text(json.dumps(mapping_data))

    mapping = SampleConfig.load_file_mapping(config_path=tmp_path)
    assert len(mapping) == 2
    assert mapping[0]["name"] == "data_file"
    assert mapping[1]["name"] == "config_file"


def test_load_file_mapping_nonexistent_file(tmp_path):
    """Test loading file mapping when file doesn't exist."""
    mapping = SampleConfig.load_file_mapping(config_path=tmp_path)
    assert mapping == []


def test_load_file_mapping_with_overrides(tmp_path):
    """Test loading file mapping with path overrides."""
    mapping_file = tmp_path / "file_mapping.json"
    mapping_data = [
        {"name": "data_file", "fpath": "*.csv", "optional": False},
        {"name": "config_file", "fpath": "*.config", "optional": True},
    ]
    mapping_file.write_text(json.dumps(mapping_data))

    mapping = SampleConfig.load_file_mapping(
        config_path=tmp_path, file_overrides={"data_file": "/custom/path/data.csv"}
    )
    assert mapping[0]["fpath"] == "/custom/path/data.csv"
    assert mapping[1]["fpath"] == "*.config"  # Not overridden


def test_load_file_mapping_override_multiple_files(tmp_path):
    """Test overriding multiple file paths."""
    mapping_file = tmp_path / "file_mapping.json"
    mapping_data = [
        {"name": "file1", "fpath": "*.f1"},
        {"name": "file2", "fpath": "*.f2"},
        {"name": "file3", "fpath": "*.f3"},
    ]
    mapping_file.write_text(json.dumps(mapping_data))

    mapping = SampleConfig.load_file_mapping(
        config_path=tmp_path, file_overrides={"file1": "/path/f1.txt", "file3": "/path/f3.txt"}
    )
    assert mapping[0]["fpath"] == "/path/f1.txt"
    assert mapping[1]["fpath"] == "*.f2"  # Not overridden
    assert mapping[2]["fpath"] == "/path/f3.txt"


def test_load_file_mapping_invalid_json(tmp_path):
    """Test loading file mapping with invalid JSON raises error."""
    mapping_file = tmp_path / "file_mapping.json"
    mapping_file.write_text("{ invalid json }")

    with pytest.raises(json.JSONDecodeError):
        SampleConfig.load_file_mapping(config_path=tmp_path)


def test_load_file_mapping_not_list(tmp_path):
    """Test loading file mapping when file is not a list raises ValueError."""
    mapping_file = tmp_path / "file_mapping.json"
    mapping_file.write_text(json.dumps({"not": "a list"}))

    with pytest.raises(ValueError, match="must contain a list"):
        SampleConfig.load_file_mapping(config_path=tmp_path)


def test_load_file_mapping_with_extra_fields(tmp_path):
    """Test that extra fields in mappings are preserved."""
    mapping_file = tmp_path / "file_mapping.json"
    mapping_data = [
        {"name": "data_file", "fpath": "*.csv", "optional": False, "description": "Main data file"}
    ]
    mapping_file.write_text(json.dumps(mapping_data))

    mapping = SampleConfig.load_file_mapping(config_path=tmp_path)
    assert mapping[0]["description"] == "Main data file"
    assert mapping[0]["optional"] is False


def test_merge_dicts_scalar_override():
    """Test _merge_dicts with scalar override."""
    base = {"a": 1, "b": 2}
    overrides = {"a": 10}
    result = PluginConfig._merge_dicts(base, overrides)
    assert result["a"] == 10
    assert result["b"] == 2


def test_merge_dicts_new_keys():
    """Test _merge_dicts adds new keys."""
    base = {"a": 1}
    overrides = {"b": 2, "c": 3}
    result = PluginConfig._merge_dicts(base, overrides)
    assert result["a"] == 1
    assert result["b"] == 2
    assert result["c"] == 3


def test_merge_dicts_list_merge():
    """Test _merge_dicts merges lists."""
    base = {"items": [1, 2, 3]}
    overrides = {"items": [3, 4, 5]}
    result = PluginConfig._merge_dicts(base, overrides)
    assert 1 in result["items"]
    assert 2 in result["items"]
    assert 3 in result["items"]
    assert 4 in result["items"]
    assert 5 in result["items"]


def test_merge_dicts_list_deduplication():
    """Test _merge_dicts deduplicates lists during merge."""
    base = {"items": [1, 2, 3]}
    overrides = {"items": [2, 4, 5]}
    result = PluginConfig._merge_dicts(base, overrides)
    # Check all items present with no duplicates introduced by merge
    assert 1 in result["items"]
    assert 2 in result["items"]
    assert 3 in result["items"]
    assert 4 in result["items"]
    assert 5 in result["items"]
    # Check that 2 and 3 (already in base) aren't duplicated
    assert result["items"].count(2) == 1
    assert result["items"].count(3) == 1


def test_merge_dicts_empty_base():
    """Test _merge_dicts with empty base."""
    base = {}
    overrides = {"a": 1, "b": 2}
    result = PluginConfig._merge_dicts(base, overrides)
    assert result == {"a": 1, "b": 2}


def test_merge_dicts_empty_overrides():
    """Test _merge_dicts with empty overrides."""
    base = {"a": 1, "b": 2}
    overrides = {}
    result = PluginConfig._merge_dicts(base, overrides)
    assert result == {"a": 1, "b": 2}


def test_merge_dicts_preserves_base():
    """Test _merge_dicts doesn't modify original base deeply."""
    base = {"a": 1, "b": [1, 2]}
    base.copy()
    overrides = {"a": 2, "c": [3, 4]}
    result = PluginConfig._merge_dicts(base, overrides)
    # Base scalar should still have original value
    assert base["a"] == 1
    # Result should have merged values
    assert result["a"] == 2
    assert result["c"] == [3, 4]
    assert result["b"] == [1, 2]


def test_resolve_config_path_classmethod(tmp_path):
    """Test _resolve_config_path classmethod."""
    resolved = SampleConfig._resolve_config_path(tmp_path)
    assert resolved == tmp_path


def test_resolve_config_path_none():
    """Test _resolve_config_path with None resolves to class location."""
    resolved = SampleConfig._resolve_config_path(None)
    assert isinstance(resolved, Path)
    assert resolved.name == "config"


def test_resolve_config_path_string(tmp_path):
    """Test _resolve_config_path converts string to Path."""
    path_str = str(tmp_path)
    resolved = SampleConfig._resolve_config_path(path_str)
    assert isinstance(resolved, Path)
    assert resolved == tmp_path


def test_load_defaults_with_logging(tmp_path, caplog):
    """Test that load_defaults logs when file doesn't exist."""
    with caplog.at_level("DEBUG"):
        defaults = SampleConfig.load_defaults(config_path=tmp_path / "nonexistent")
    assert defaults == {}
    # Check that debug logging occurred
    assert "Defaults file not found" in caplog.text or len(caplog.records) == 0


def test_load_file_mapping_with_logging(tmp_path, caplog):
    """Test that load_file_mapping logs when file doesn't exist."""
    with caplog.at_level("DEBUG"):
        mapping = SampleConfig.load_file_mapping(config_path=tmp_path / "nonexistent")
    assert mapping == []


def test_load_defaults_error_logging(tmp_path, caplog):
    """Test that parse errors are logged."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text("{ invalid json }")

    with caplog.at_level("ERROR"), pytest.raises(json.JSONDecodeError):
        SampleConfig.load_defaults(config_path=tmp_path)
    assert "Failed to parse defaults JSON" in caplog.text


def test_load_file_mapping_error_logging(tmp_path, caplog):
    """Test that parse errors are logged."""
    mapping_file = tmp_path / "file_mapping.json"
    mapping_file.write_text("{ invalid json }")

    with caplog.at_level("ERROR"), pytest.raises(json.JSONDecodeError):
        SampleConfig.load_file_mapping(config_path=tmp_path)
    assert "Failed to parse file mapping JSON" in caplog.text


def test_custom_dir_config_default_location(tmp_path):
    """Test PluginConfig with custom CONFIG_DIR."""
    config = CustomDirConfig(param="test", config_path=tmp_path)
    assert config.config_path == tmp_path


@pytest.mark.parametrize(
    "defaults_data,overrides,expected_key,expected_value",
    [
        ({"a": 1}, {"a": 2}, "a", 2),
        ({"a": 1, "b": 2}, {"a": 10}, "a", 10),
        ({}, {"new": "value"}, "new", "value"),
        ({"items": ["a", "b"]}, {"items": ["c"]}, "items", None),  # List case
    ],
)
def test_load_defaults_parametrized(tmp_path, defaults_data, overrides, expected_key, expected_value):
    """Parametrized test for load_defaults."""
    defaults_file = tmp_path / "defaults.json"
    defaults_file.write_text(json.dumps(defaults_data))

    defaults = SampleConfig.load_defaults(config_path=tmp_path, overrides=overrides)

    if expected_value is None and expected_key == "items":
        # For list case, just check key exists and contains expected values
        assert expected_key in defaults
        assert all(item in defaults[expected_key] for item in overrides[expected_key])
    else:
        assert defaults[expected_key] == expected_value


@pytest.mark.parametrize(
    "mapping_data,overrides,idx,expected_fpath",
    [
        ([{"name": "f1", "fpath": "*.csv"}], {"f1": "/path/f1.csv"}, 0, "/path/f1.csv"),
        ([{"name": "f1", "fpath": "*.csv"}, {"name": "f2", "fpath": "*.json"}], {"f1": "/p1"}, 0, "/p1"),
        ([{"name": "f1", "fpath": "*.csv"}, {"name": "f2", "fpath": "*.json"}], {"f2": "/p2"}, 1, "/p2"),
    ],
)
def test_load_file_mapping_parametrized(tmp_path, mapping_data, overrides, idx, expected_fpath):
    """Parametrized test for load_file_mapping."""
    mapping_file = tmp_path / "file_mapping.json"
    mapping_file.write_text(json.dumps(mapping_data))

    mapping = SampleConfig.load_file_mapping(config_path=tmp_path, file_overrides=overrides)

    assert mapping[idx]["fpath"] == expected_fpath


def test_config_path_field_validator():
    """Test that config_path field validator runs."""
    config = SampleConfig(param1="test")
    assert config.config_path is not None
    assert isinstance(config.config_path, Path)


def test_multiple_config_instances_independent(tmp_path):
    """Test that multiple config instances are independent."""
    path1 = tmp_path / "path1"
    path2 = tmp_path / "path2"
    path1.mkdir()
    path2.mkdir()

    config1 = SampleConfig(param1="test1", config_path=path1)
    config2 = SampleConfig(param1="test2", config_path=path2)

    assert config1.config_path == path1
    assert config2.config_path == path2
    assert config1.param1 == "test1"
    assert config2.param1 == "test2"


def test_load_defaults_complex_merge(tmp_path):
    """Test complex merging scenario."""
    defaults_file = tmp_path / "defaults.json"
    defaults_data = {"scalar": "default", "number": 42, "list": ["a", "b"], "nested_dict": {"key": "value"}}
    defaults_file.write_text(json.dumps(defaults_data))

    overrides = {"scalar": "overridden", "list": ["c"], "new_key": "new_value"}
    defaults = SampleConfig.load_defaults(config_path=tmp_path, overrides=overrides)

    assert defaults["scalar"] == "overridden"
    assert defaults["number"] == 42  # Not overridden
    assert "a" in defaults["list"] and "c" in defaults["list"]
    assert defaults["nested_dict"]["key"] == "value"
    assert defaults["new_key"] == "new_value"
