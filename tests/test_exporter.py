"""Tests for the exporter module."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from r2x_core import BaseExporter, DataStore
from r2x_core.system import System


class MockConfig(BaseModel):
    """Mock configuration for testing."""

    output_dir: Path = Path("output")


class ConcreteExporter(BaseExporter):
    """Concrete implementation of BaseExporter for testing."""

    def export(self) -> None:
        """Implement abstract export method."""
        # Simple implementation for testing

    def export_time_series(self) -> None:
        """Implement abstract export_time_series method."""
        # Simple implementation for testing


class ExporterWithKwargs(BaseExporter):
    """Exporter that uses additional kwargs."""

    def __init__(
        self,
        config: BaseModel,
        system: System,
        data_store: DataStore,
        custom_field: str = "default",
        **kwargs,
    ):
        """Initialize with custom field."""
        super().__init__(config, system, data_store, custom_field=custom_field, **kwargs)

    def export(self) -> None:
        """Implement abstract export method."""

    def export_time_series(self) -> None:
        """Implement abstract export_time_series method."""


def test_base_exporter_initialization(tmp_path):
    """Test BaseExporter initialization."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()

    exporter = ConcreteExporter(config, system, data_store)

    assert exporter.config == config
    assert exporter.system == system
    assert exporter.data_store == data_store


def test_base_exporter_with_kwargs(tmp_path):
    """Test BaseExporter initialization with additional kwargs."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()

    exporter = ExporterWithKwargs(
        config,
        system,
        data_store,
        custom_field="test_value",
        extra_param="extra",
    )

    assert exporter.config == config
    assert exporter.system == system
    assert exporter.data_store == data_store
    assert exporter.custom_field == "test_value"
    assert exporter.extra_param == "extra"


def test_base_exporter_abstract_methods():
    """Test that BaseExporter cannot be instantiated directly."""
    config = MockConfig()
    system = System()
    data_store = DataStore()

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseExporter(config, system, data_store)


def test_concrete_exporter_export_method(tmp_path):
    """Test that concrete exporter can call export method."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()

    exporter = ConcreteExporter(config, system, data_store)
    # Should not raise any exception
    exporter.export()


def test_concrete_exporter_export_time_series_method(tmp_path):
    """Test that concrete exporter can call export_time_series method."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()

    exporter = ConcreteExporter(config, system, data_store)
    # Should not raise any exception
    exporter.export_time_series()
