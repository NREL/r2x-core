"""Tests for the plugin system."""

from unittest.mock import MagicMock, patch

import polars as pl
from pydantic import BaseModel

from r2x_core import (
    BaseExporter,
    BaseParser,
    DataStore,
    PluginManager,
    System,
)


class MockPluginConfig(BaseModel):
    """Mock configuration for testing."""

    folder: str
    year: int = 2030


class MockParser(BaseParser):
    """Mock parser for plugin system testing."""

    def __init__(self, config: MockPluginConfig, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)
        self.year = config.year

    def build_system_components(self) -> None:
        """Build mock components."""
        pass

    def build_time_series(self) -> None:
        """Build mock time series."""
        pass


class MockExporter(BaseExporter):
    """Mock exporter for plugin system testing."""

    def export(self) -> None:
        """Export mock data."""
        pass

    def export_time_series(self) -> None:
        """Export mock time series."""
        pass


# Model Plugin Registration Tests


def test_register_complete_plugin():
    """Test registering a complete model plugin."""
    PluginManager.register_model_plugin(
        name="test_model",
        config=MockPluginConfig,
        parser=MockParser,
        exporter=MockExporter,
    )

    manager = PluginManager()
    assert "test_model" in manager.registered_parsers
    assert "test_model" in manager.registered_exporters


def test_register_parser_only():
    """Test registering parser-only plugin."""
    PluginManager.register_model_plugin(
        name="test_parser_only",
        config=MockPluginConfig,
        parser=MockParser,
    )

    manager = PluginManager()
    assert "test_parser_only" in manager.registered_parsers
    assert "test_parser_only" not in manager.registered_exporters


def test_register_exporter_only():
    """Test registering exporter-only plugin."""
    PluginManager.register_model_plugin(
        name="test_exporter_only",
        config=MockPluginConfig,
        exporter=MockExporter,
    )

    manager = PluginManager()
    assert "test_exporter_only" not in manager.registered_parsers
    assert "test_exporter_only" in manager.registered_exporters


def test_register_plugin_with_neither_parser_nor_exporter():
    """Test registering plugin without parser or exporter (should warn)."""
    # This should still work but log a warning
    PluginManager.register_model_plugin(
        name="test_neither",
        config=MockPluginConfig,
    )

    # Should have registered
    manager = PluginManager()
    assert manager.get_config_class("test_neither") is MockPluginConfig
    assert "test_neither" not in manager.registered_parsers
    assert "test_neither" not in manager.registered_exporters


# System Modifier Registration Tests


def test_register_system_modifier():
    """Test registering a system modifier with explicit name."""

    @PluginManager.register_system_modifier("test_modifier")
    def test_modifier(system: System, param: int = 10, **kwargs) -> System:
        return system

    manager = PluginManager()
    assert "test_modifier" in manager.system_modifiers
    modifier = manager.system_modifiers["test_modifier"]
    assert callable(modifier)


def test_register_system_modifier_without_name():
    """Test registering a system modifier without explicit name (uses function name)."""

    @PluginManager.register_system_modifier
    def my_modifier(system: System, **kwargs) -> System:
        return system

    manager = PluginManager()
    assert "my_modifier" in manager.system_modifiers
    modifier = manager.system_modifiers["my_modifier"]
    assert callable(modifier)


def test_register_filter():
    """Test registering a filter function with explicit name."""

    @PluginManager.register_filter("test_filter")
    def test_filter(data: pl.LazyFrame, column: str) -> pl.LazyFrame:
        return data.filter(pl.col(column).is_not_null())

    manager = PluginManager()
    assert "test_filter" in manager.filter_functions
    filter_func = manager.filter_functions["test_filter"]
    assert callable(filter_func)


def test_register_filter_without_name():
    """Test registering a filter function without explicit name (uses function name)."""

    @PluginManager.register_filter
    def my_filter(data: pl.LazyFrame) -> pl.LazyFrame:
        return data

    manager = PluginManager()
    assert "my_filter" in manager.filter_functions
    filter_func = manager.filter_functions["my_filter"]
    assert callable(filter_func)


# Plugin Discovery Tests


def test_load_parser():
    """Test loading a parser class."""
    PluginManager.register_model_plugin(
        name="test_load_parser",
        config=MockPluginConfig,
        parser=MockParser,
    )

    manager = PluginManager()
    parser_class = manager.load_parser("test_load_parser")
    assert parser_class is MockParser


def test_load_parser_not_found():
    """Test loading non-existent parser."""
    manager = PluginManager()
    parser_class = manager.load_parser("nonexistent")
    assert parser_class is None


def test_load_exporter():
    """Test loading an exporter class."""
    PluginManager.register_model_plugin(
        name="test_load_exporter",
        config=MockPluginConfig,
        exporter=MockExporter,
    )

    manager = PluginManager()
    exporter_class = manager.load_exporter("test_load_exporter")
    assert exporter_class is MockExporter


def test_load_exporter_not_found():
    """Test loading non-existent exporter."""
    manager = PluginManager()
    exporter_class = manager.load_exporter("nonexistent")
    assert exporter_class is None


def test_get_config_class():
    """Test getting config class for a plugin."""
    PluginManager.register_model_plugin(
        name="test_get_config",
        config=MockPluginConfig,
        parser=MockParser,
    )

    manager = PluginManager()
    config_class = manager.get_config_class("test_get_config")
    assert config_class is MockPluginConfig


def test_get_config_class_not_found():
    """Test getting config for non-existent plugin."""
    manager = PluginManager()
    config_class = manager.get_config_class("nonexistent")
    assert config_class is None


# System Modifier Tests


def test_modifier_transforms_system():
    """Test that modifier receives and returns system."""

    @PluginManager.register_system_modifier("test_transform")
    def transform_system(system: System, **kwargs) -> System:
        # In real usage, would modify system
        return system

    manager = PluginManager()
    modifier = manager.system_modifiers["test_transform"]

    system = System()
    result = modifier(system)
    assert isinstance(result, System)


def test_modifier_with_parameters():
    """Test modifier with custom parameters."""

    @PluginManager.register_system_modifier("test_params")
    def modifier_with_params(
        system: System, capacity_mw: float = 100.0, **kwargs
    ) -> System:
        # Store param for testing
        system._test_capacity = capacity_mw
        return system

    manager = PluginManager()
    modifier = manager.system_modifiers["test_params"]

    system = System()
    result = modifier(system, capacity_mw=250.0)
    assert result._test_capacity == 250.0


def test_modifier_with_context():
    """Test modifier accessing context via kwargs."""

    @PluginManager.register_system_modifier("test_context")
    def modifier_with_context(system: System, **kwargs) -> System:
        config = kwargs.get("config")
        if config:
            system._test_year = config.year
        return system

    manager = PluginManager()
    modifier = manager.system_modifiers["test_context"]

    system = System()
    config = MockPluginConfig(folder="./test", year=2040)
    result = modifier(system, config=config)
    assert result._test_year == 2040


# Filter Function Tests


def test_filter_processes_data():
    """Test that filter receives and returns data."""

    @PluginManager.register_filter("test_process")
    def process_data(data: pl.LazyFrame) -> pl.LazyFrame:
        return data

    manager = PluginManager()
    filter_func = manager.filter_functions["test_process"]

    df = pl.LazyFrame({"a": [1, 2, 3]})
    result = filter_func(df)
    assert isinstance(result, pl.LazyFrame)


def test_filter_with_parameters():
    """Test filter with custom parameters."""

    @PluginManager.register_filter("test_filter_params")
    def filter_with_params(data: pl.LazyFrame, threshold: int) -> pl.LazyFrame:
        return data.filter(pl.col("value") > threshold)

    manager = PluginManager()
    filter_func = manager.filter_functions["test_filter_params"]

    df = pl.LazyFrame({"value": [1, 5, 10]})
    result = filter_func(df, threshold=4).collect()
    assert len(result) == 2
    assert result["value"].to_list() == [5, 10]


# PluginManager Singleton Tests


def test_singleton_instance():
    """Test that PluginManager returns same instance."""
    manager1 = PluginManager()
    manager2 = PluginManager()
    assert manager1 is manager2


def test_registries_are_shared():
    """Test that registries are shared across instances."""
    PluginManager.register_model_plugin(
        name="test_shared",
        config=MockPluginConfig,
        parser=MockParser,
    )

    manager1 = PluginManager()
    manager2 = PluginManager()

    assert "test_shared" in manager1.registered_parsers
    assert "test_shared" in manager2.registered_parsers
    assert (
        manager1.registered_parsers is not manager2.registered_parsers
    )  # Copy returned


# Plugin Manager Property Tests


def test_registered_parsers_property():
    """Test registered_parsers property."""
    PluginManager.register_model_plugin(
        name="test_props_parser",
        config=MockPluginConfig,
        parser=MockParser,
    )

    manager = PluginManager()
    parsers = manager.registered_parsers
    assert isinstance(parsers, dict)
    assert "test_props_parser" in parsers
    assert parsers["test_props_parser"] is MockParser


def test_registered_exporters_property():
    """Test registered_exporters property."""
    PluginManager.register_model_plugin(
        name="test_props_exporter",
        config=MockPluginConfig,
        exporter=MockExporter,
    )

    manager = PluginManager()
    exporters = manager.registered_exporters
    assert isinstance(exporters, dict)
    assert "test_props_exporter" in exporters
    assert exporters["test_props_exporter"] is MockExporter


def test_system_modifiers_property():
    """Test system_modifiers property."""

    @PluginManager.register_system_modifier("test_props_modifier")
    def test_mod(system: System, **kwargs) -> System:
        return system

    manager = PluginManager()
    modifiers = manager.system_modifiers
    assert isinstance(modifiers, dict)
    assert "test_props_modifier" in modifiers


def test_filter_functions_property():
    """Test filter_functions property."""

    @PluginManager.register_filter("test_props_filter")
    def test_filter(data: pl.LazyFrame) -> pl.LazyFrame:
        return data

    manager = PluginManager()
    filters = manager.filter_functions
    assert isinstance(filters, dict)
    assert "test_props_filter" in filters


def test_entry_point_load_error():
    """Test entry point loading with failed plugin load."""
    # Create a mock entry point that raises an error when loaded
    mock_ep = MagicMock()
    mock_ep.name = "failing_plugin"
    mock_ep.load.side_effect = ImportError("Module not found")

    # Should not raise, just log warning
    with patch("r2x_core.plugins.entry_points", return_value=[mock_ep]):
        PluginManager._load_entry_point_plugins()

    # Verify the entry point load was attempted
    mock_ep.load.assert_called_once()


def test_entry_point_successful_load():
    """Test successful entry point loading."""
    # Create a mock registration function
    mock_register = MagicMock()

    # Create a mock entry point that successfully loads
    mock_ep = MagicMock()
    mock_ep.name = "successful_plugin"
    mock_ep.load.return_value = mock_register

    with patch("r2x_core.plugins.entry_points", return_value=[mock_ep]):
        PluginManager._load_entry_point_plugins()

    # Verify the registration function was called
    mock_ep.load.assert_called_once()
    mock_register.assert_called_once()


def test_entry_point_discovery_error():
    """Test entry point discovery failure."""
    # Should not raise, just log debug message
    with patch(
        "r2x_core.plugins.entry_points", side_effect=RuntimeError("Discovery failed")
    ):
        PluginManager._load_entry_point_plugins()

    # If we got here, the exception was caught and handled
