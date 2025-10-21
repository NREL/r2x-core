"""Tests for the exporter module."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from r2x_core import BaseExporter, DataStore
from r2x_core.exceptions import ExporterError
from r2x_core.result import Ok, Result
from r2x_core.system import System


class MockConfig(BaseModel):
    """Mock configuration for testing."""

    output_dir: Path = Path("output")


class ConcreteExporter(BaseExporter):
    """Concrete implementation of BaseExporter for testing.

    This minimal exporter implements the required prepare_export method.
    All other hook methods use the default implementations from BaseExporter.
    """

    def prepare_export(self) -> Result[None, ExporterError]:
        """Implement required prepare_export method."""
        # Simple test implementation - just return success
        return Ok(None)


class ExporterWithKwargs(BaseExporter):
    """Exporter that uses additional kwargs.

    This exporter demonstrates how to extend BaseExporter with custom
    initialization parameters.
    """

    def __init__(
        self,
        config: BaseModel,
        system: System,
        /,
        *,
        data_store: DataStore | None = None,
        custom_field: str = "default",
        **kwargs: Any,
    ):
        """Initialize with custom field."""
        super().__init__(config, system, data_store=data_store, **kwargs)
        self.custom_field = custom_field
        # Store any additional kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    def prepare_export(self) -> Result[None, ExporterError]:
        """Implement required prepare_export method."""
        # Simple test implementation - just return success
        return Ok(None)


def test_base_exporter_initialization(tmp_path):
    """Test BaseExporter initialization."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()

    exporter = ConcreteExporter(config, system, data_store=data_store)

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
        data_store=data_store,
        custom_field="test_value",
        extra_param="extra",
    )

    assert exporter.config == config
    assert exporter.system == system
    assert exporter.data_store == data_store
    assert exporter.custom_field == "test_value"
    assert exporter.extra_param == "extra"


def test_base_exporter_abstract_method():
    """Test that BaseExporter cannot be instantiated without implementing prepare_export."""
    config = MockConfig()
    system = System()
    data_store = DataStore()

    # BaseExporter should not be instantiable since prepare_export is abstract
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseExporter(config, system, data_store=data_store)


def test_concrete_exporter_export_method(tmp_path):
    """Test that concrete exporter can call export method."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()

    exporter = ConcreteExporter(config, system, data_store=data_store)
    # Should not raise any exception
    result = exporter.export()
    assert result.is_ok()


def test_concrete_exporter_export_time_series_method(tmp_path):
    """Test that concrete exporter can call export_time_series method."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()

    exporter = ConcreteExporter(config, system, data_store=data_store)
    # Should not raise any exception
    result = exporter.export_time_series()
    assert result.is_ok()
