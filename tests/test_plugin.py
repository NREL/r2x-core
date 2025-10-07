"""Tests for plugin functionality: configuration, file mapping, and CLI schema methods."""

import json
from pathlib import Path

from r2x_core.parser import BaseParser
from r2x_core.plugin_config import PluginConfig
from r2x_core.plugins import PluginManager


def test_load_defaults_with_valid_file(tmp_path):
    """Test loading defaults from a valid JSON file."""
    defaults_data = {
        "excluded_techs": ["coal", "oil"],
        "default_capacity": 100.0,
        "regions": ["east", "west"],
    }
    defaults_file = tmp_path / "test_defaults.json"
    with open(defaults_file, "w") as f:
        json.dump(defaults_data, f)

    result = PluginConfig.load_defaults(defaults_file)

    assert result == defaults_data
    assert result["excluded_techs"] == ["coal", "oil"]
    assert result["default_capacity"] == 100.0


def test_load_defaults_with_missing_file(tmp_path):
    """Test loading defaults from non-existent file returns empty dict."""
    missing_file = tmp_path / "nonexistent.json"

    result = PluginConfig.load_defaults(missing_file)

    assert result == {}


def test_load_defaults_with_invalid_json(tmp_path):
    """Test loading defaults from invalid JSON returns empty dict."""
    invalid_file = tmp_path / "invalid.json"
    with open(invalid_file, "w") as f:
        f.write("{ invalid json content }")

    result = PluginConfig.load_defaults(invalid_file)

    assert result == {}


# def test_load_defaults_auto_discovery(tmp_path):
#     """Test auto-discovery of constants.json in config directory."""
#     module_dir = tmp_path / "test_module"
#     module_dir.mkdir()
#     config_dir = module_dir / "config"
#     config_dir.mkdir()

#     constants_data = {"test_constant": "value"}
#     constants_file = config_dir / "constants.json"
#     with open(constants_file, "w") as f:
#         json.dump(constants_data, f)

#     config_file = module_dir / "config.py"
#     config_file.write_text(
#         """
# from r2x_core.plugin_config import PluginConfig

# class TestConfig(PluginConfig):
#     pass
# """
#     )

#     result = PluginConfig.load_defaults(constants_file)
#     assert result == constants_data


def test_load_defaults_with_path_object(tmp_path):
    """Test load_defaults accepts Path objects."""
    defaults_data = {"key": "value"}
    defaults_file = tmp_path / "test.json"
    with open(defaults_file, "w") as f:
        json.dump(defaults_data, f)

    result = PluginConfig.load_defaults(defaults_file)

    assert result == defaults_data


def test_load_defaults_with_string_path(tmp_path):
    """Test load_defaults accepts string paths."""
    defaults_data = {"key": "value"}
    defaults_file = tmp_path / "test.json"
    with open(defaults_file, "w") as f:
        json.dump(defaults_data, f)

    result = PluginConfig.load_defaults(str(defaults_file))

    assert result == defaults_data


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

    defaults = TestConfig.load_defaults(defaults_file)
    config = TestConfig(model_year=2030)

    assert config.model_year == 2030
    assert config.scenario == "base"
    assert defaults == defaults_data
    assert defaults["excluded_techs"] == ["coal"]


def test_load_defaults_custom_filename(tmp_path):
    """Test that DEFAULTS_FILE_NAME can be overridden."""
    defaults_data = {"custom_setting": "value"}

    # Create config directory and custom defaults file
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    custom_file = config_dir / "my_defaults.json"
    with open(custom_file, "w") as f:
        json.dump(defaults_data, f)

    # Create a test module file in tmp_path
    module_file = tmp_path / "test_module.py"
    module_file.write_text("# test module")

    class CustomDefaultsConfig(PluginConfig):
        DEFAULTS_FILE_NAME = "my_defaults.json"
        model_year: int

    # Mock inspect.getfile to return our test module
    import inspect

    original_getfile = inspect.getfile

    def mock_getfile(cls):
        if cls == CustomDefaultsConfig:
            return str(module_file)
        return original_getfile(cls)

    inspect.getfile = mock_getfile
    try:
        defaults = CustomDefaultsConfig.load_defaults()
        assert defaults == defaults_data
    finally:
        inspect.getfile = original_getfile


def test_defaults_file_name_default():
    """Test that default DEFAULTS_FILE_NAME is defaults.json."""
    assert PluginConfig.DEFAULTS_FILE_NAME == "defaults.json"


def test_get_file_mapping_path_returns_path(tmp_path):
    """Test that get_file_mapping_path returns a Path object."""
    config_dir = tmp_path / "test_config"
    config_dir.mkdir()
    config_subdir = config_dir / "config"
    config_subdir.mkdir()

    config_file = config_dir / "config.py"
    config_file.write_text(
        """
from r2x_core.plugin_config import PluginConfig

class TestConfig(PluginConfig):
    model_year: int
"""
    )

    class ConcreteTestConfig(PluginConfig):
        model_year: int

    mapping_path = ConcreteTestConfig.get_file_mapping_path()

    assert isinstance(mapping_path, Path)
    assert mapping_path.name == "file_mapping.json"
    assert mapping_path.parent.name == "config"


def test_get_file_mapping_path_custom_filename():
    """Test that FILE_MAPPING_NAME can be overridden."""

    class CustomConfig(PluginConfig):
        FILE_MAPPING_NAME = "custom_mapping.json"
        model_year: int

    mapping_path = CustomConfig.get_file_mapping_path()

    assert mapping_path.name == "custom_mapping.json"
    assert mapping_path.parent.name == "config"


def test_get_file_mapping_path_default_filename():
    """Test that default FILE_MAPPING_NAME is file_mapping.json."""

    class DefaultConfig(PluginConfig):
        model_year: int

    mapping_path = DefaultConfig.get_file_mapping_path()

    assert mapping_path.name == "file_mapping.json"
    assert DefaultConfig.FILE_MAPPING_NAME == "file_mapping.json"


def test_get_file_mapping_path_is_absolute():
    """Test that the returned path is absolute."""

    class AbsoluteTestConfig(PluginConfig):
        model_year: int

    mapping_path = AbsoluteTestConfig.get_file_mapping_path()

    assert mapping_path.is_absolute()


def test_get_file_mapping_path_works_with_actual_file(tmp_path):
    """Test that get_file_mapping_path can locate an actual file."""

    class RealFileConfig(PluginConfig):
        model_year: int

    mapping_path = RealFileConfig.get_file_mapping_path()

    assert "tests" in str(mapping_path) or "test_plugin" in str(mapping_path)
    assert mapping_path.name == "file_mapping.json"


def test_get_cli_schema_basic():
    """Test basic CLI schema generation from a simple config class."""

    class SimpleConfig(PluginConfig):
        """Simple configuration for testing."""

        model_year: int
        scenario: str = "base"

    schema = SimpleConfig.get_cli_schema()

    assert "title" in schema
    assert "description" in schema
    assert "properties" in schema
    assert "required" in schema
    assert "model_year" in schema["properties"]
    assert "scenario" in schema["properties"]
    assert schema["properties"]["model_year"]["cli_flag"] == "--model-year"
    assert schema["properties"]["scenario"]["cli_flag"] == "--scenario"
    assert schema["properties"]["model_year"]["required"] is True
    assert schema["properties"]["scenario"]["required"] is False
    assert "model_year" in schema["required"]
    assert "scenario" not in schema["required"]


def test_get_cli_schema_with_description():
    """Test CLI schema preserves field descriptions."""

    class DescribedConfig(PluginConfig):
        """Configuration with field descriptions."""

        model_year: int
        scenario: str = "base"

    schema = DescribedConfig.get_cli_schema()

    assert schema["description"] == "Configuration with field descriptions."


def test_get_cli_schema_underscore_to_hyphen():
    """Test that underscores in field names become hyphens in CLI flags."""

    class UnderscoreConfig(PluginConfig):
        weather_year: int
        solve_year: int
        model_version_string: str = "v1.0"

    schema = UnderscoreConfig.get_cli_schema()

    assert schema["properties"]["weather_year"]["cli_flag"] == "--weather-year"
    assert schema["properties"]["solve_year"]["cli_flag"] == "--solve-year"
    assert schema["properties"]["model_version_string"]["cli_flag"] == "--model-version-string"


def test_get_cli_schema_no_required_fields():
    """Test schema generation when all fields have defaults."""

    class AllDefaultsConfig(PluginConfig):
        scenario: str = "base"
        year: int = 2030
        debug: bool = False

    schema = AllDefaultsConfig.get_cli_schema()

    assert schema["properties"]["scenario"]["required"] is False
    assert schema["properties"]["year"]["required"] is False
    assert schema["properties"]["debug"]["required"] is False
    assert len(schema["required"]) == 0


def test_get_cli_schema_preserves_pydantic_schema():
    """Test that CLI schema preserves Pydantic field information."""

    class DetailedConfig(PluginConfig):
        """Detailed configuration."""

        model_year: int
        capacity: float = 100.0

    schema = DetailedConfig.get_cli_schema()

    assert "type" in schema["properties"]["model_year"]
    assert "type" in schema["properties"]["capacity"]

    if "default" in schema["properties"]["capacity"]:
        assert schema["properties"]["capacity"]["default"] == 100.0


def test_get_cli_schema_integration_with_config_class():
    """Test that get_cli_schema works with a realistic config class."""

    class RealisticConfig(PluginConfig):
        """Realistic model configuration for testing."""

        solve_year: int
        weather_year: int
        scenario: str = "reference"
        output_dir: str = "./output"
        verbose: bool = False

    schema = RealisticConfig.get_cli_schema()

    assert len(schema["properties"]) == 5  # 5 user-defined fields
    assert schema["properties"]["solve_year"]["required"] is True
    assert schema["properties"]["weather_year"]["required"] is True
    assert schema["properties"]["scenario"]["required"] is False

    for field_name in schema["properties"]:
        cli_flag = schema["properties"][field_name]["cli_flag"]
        assert cli_flag.startswith("--")
        assert "_" not in cli_flag
        assert field_name.replace("_", "-") in cli_flag


def test_plugin_manager_get_file_mapping_path_with_parser():
    """Test getting file mapping path through PluginManager."""

    class TestParser(BaseParser):
        def build_system_components(self):
            pass

        def build_time_series(self):
            pass

    manager = PluginManager()
    manager.register_model_plugin(
        name="test_plugin",
        config=PluginConfig,
        parser=TestParser,
    )

    mapping_path = manager.get_file_mapping_path("test_plugin")

    assert mapping_path is not None
    assert isinstance(mapping_path, Path)
    assert mapping_path.name == "file_mapping.json"


def test_plugin_manager_get_file_mapping_path_without_parser():
    """Test that get_file_mapping_path works even for plugins without parsers."""
    from r2x_core.exporter import BaseExporter

    class TestExporter(BaseExporter):
        def export_to_model_format(self):
            pass

        def export_time_series(self):
            pass

    manager = PluginManager()
    manager.register_model_plugin(
        name="exporter_only",
        config=PluginConfig,
        exporter=TestExporter,
    )

    # Should still work since config is registered
    mapping_path = manager.get_file_mapping_path("exporter_only")

    assert mapping_path is not None
    assert isinstance(mapping_path, Path)


def test_plugin_manager_get_file_mapping_path_nonexistent_plugin():
    """Test that get_file_mapping_path returns None for non-existent plugins."""
    manager = PluginManager()

    mapping_path = manager.get_file_mapping_path("nonexistent")

    assert mapping_path is None


def test_plugin_manager_get_file_mapping_path_delegates_to_parser():
    """Test that PluginManager delegates to config's get_file_mapping_path."""

    class CustomMappingConfig(PluginConfig):
        FILE_MAPPING_NAME = "custom_file_map.json"
        model_year: int

    class CustomMappingParser(BaseParser):
        def build_system_components(self):
            pass

        def build_time_series(self):
            pass

    manager = PluginManager()
    manager.register_model_plugin(
        name="custom_mapping",
        config=CustomMappingConfig,
        parser=CustomMappingParser,
    )

    mapping_path = manager.get_file_mapping_path("custom_mapping")

    assert mapping_path is not None
    assert mapping_path.name == "custom_file_map.json"
