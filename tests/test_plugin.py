"""Tests for plugin functionality: configuration, file mapping, and CLI schema methods."""

import json

import pytest

from r2x_core.plugin_config import PluginConfig


@pytest.fixture
def test_config() -> PluginConfig:
    return PluginConfig()


def test_load_defaults_with_valid_file(tmp_path, test_config):
    """Test loading defaults from a valid JSON file."""
    defaults_data = {
        "excluded_techs": ["coal", "oil"],
        "default_capacity": 100.0,
        "regions": ["east", "west"],
    }
    defaults_file = tmp_path / "test_defaults.json"
    with open(defaults_file, "w") as f:
        json.dump(defaults_data, f)

    result = test_config.load_defaults(defaults_file)

    assert result == defaults_data
    assert result["excluded_techs"] == ["coal", "oil"]
    assert result["default_capacity"] == 100.0


def test_load_defaults_with_missing_file(tmp_path, test_config):
    """Test loading defaults from non-existent file returns empty dict."""
    missing_file = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        _ = test_config.load_defaults(missing_file)


def test_load_defaults_with_invalid_json(tmp_path, test_config):
    """Test loading defaults from invalid JSON returns empty dict."""
    invalid_file = tmp_path / "invalid.json"
    with open(invalid_file, "w") as f:
        f.write("{ invalid json content }")

    with pytest.raises(json.JSONDecodeError):
        _ = test_config.load_defaults(invalid_file)


def test_load_defaults_integration(tmp_path):
    """Test loading defaults and using them in a config."""
    defaults_data = {
        "excluded_techs": ["coal"],
        "default_capacity": 50.0,
    }
    defaults_file = tmp_path / "defaults.json"
    with open(defaults_file, "w") as f:
        json.dump(defaults_data, f)

    class TestConfig(PluginConfig):
        model_year: int
        scenario: str = "base"

    config = TestConfig(model_year=2030)
    defaults = config.load_defaults(defaults_file)

    assert config.model_year == 2030
    assert config.scenario == "base"
    assert defaults == defaults_data
    assert defaults["excluded_techs"] == ["coal"]


def test_load_defaults_custom_filename(tmp_path):
    """Test that DEFAULTS_FILE_NAME can be overridden."""
    defaults_data = {"custom_setting": "value"}

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    custom_file = config_dir / "my_defaults.json"
    with open(custom_file, "w") as f:
        json.dump(defaults_data, f)

    class CustomDefaultsConfig(PluginConfig):
        DEFAULTS_FILE_NAME = "my_defaults.json"
        model_year: int

    config = CustomDefaultsConfig(model_year=2012, config_path=config_dir)
    defaults = config.load_defaults()
    assert defaults == defaults_data


def test_defaults_file_name_default():
    """Test that default DEFAULTS_FILE_NAME is defaults.json."""
    assert PluginConfig.DEFAULTS_FILE_NAME == "defaults.json"


def test_load_file_mapping_fails_if_not_found():
    config = PluginConfig()

    with pytest.raises(FileNotFoundError):
        config.load_file_mapping()


def test_load_file_mapping_from_file(tmp_path):
    json_path = tmp_path / "config.json"
    json_data = [
        {"name": "test1", "fpath": "file1.csv"},
        {"name": "test2", "fpath": "file2.csv"},
    ]
    with open(json_path, "w") as f:
        json.dump(json_data, f)

    config = PluginConfig()
    fmap = config.load_file_mapping(json_path)
    assert isinstance(fmap, list)
