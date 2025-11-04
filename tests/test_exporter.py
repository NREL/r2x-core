"""Tests for the exporter module."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from r2x_core import BaseExporter, DataStore
from r2x_core.exceptions import ExporterError
from r2x_core.result import Err, Ok, Result
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


class ExporterWithSetupError(BaseExporter):
    """Exporter that fails during setup."""

    def setup_configuration(self) -> Result[None, ExporterError]:
        """Return error during setup."""
        return Err(ExporterError("Setup failed"))

    def prepare_export(self) -> Result[None, ExporterError]:
        """Implement required prepare_export method."""
        return Ok(None)


class ExporterWithPrepareError(BaseExporter):
    """Exporter that fails during prepare."""

    def prepare_export(self) -> Result[None, ExporterError]:
        """Return error during prepare."""
        return Err(ExporterError("Prepare failed"))


class ExporterWithValidationError(BaseExporter):
    """Exporter that fails during validation."""

    def prepare_export(self) -> Result[None, ExporterError]:
        """Implement required prepare_export method."""
        return Ok(None)

    def validate_export(self) -> Result[None, ExporterError]:
        """Return error during validation."""
        return Err(ExporterError("Validation failed"))


class ExporterWithTimeSeriesError(BaseExporter):
    """Exporter that fails during time series export."""

    def prepare_export(self) -> Result[None, ExporterError]:
        """Implement required prepare_export method."""
        return Ok(None)

    def export_time_series(self) -> Result[None, ExporterError]:
        """Return error during time series export."""
        return Err(ExporterError("Time series export failed"))


class ExporterWithPostprocessError(BaseExporter):
    """Exporter that fails during postprocess."""

    def prepare_export(self) -> Result[None, ExporterError]:
        """Implement required prepare_export method."""
        return Ok(None)

    def postprocess_export(self) -> Result[None, ExporterError]:
        """Return error during postprocess."""
        return Err(ExporterError("Postprocess failed"))


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


def test_exporter_setup_error(tmp_path, caplog):
    """Test that setup errors are properly logged and returned."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()
    exporter = ExporterWithSetupError(config, system, data_store=data_store)

    result = exporter.export()
    assert result.is_err()
    assert "Setup failed" in str(result.err())


def test_exporter_prepare_error(tmp_path, caplog):
    """Test that prepare errors are properly logged and returned."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()
    exporter = ExporterWithPrepareError(config, system, data_store=data_store)

    result = exporter.export()
    assert result.is_err()
    assert "Prepare failed" in str(result.err())


def test_exporter_validation_error(tmp_path, caplog):
    """Test that validation errors are properly logged and returned."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()
    exporter = ExporterWithValidationError(config, system, data_store=data_store)

    result = exporter.export()
    assert result.is_err()
    assert "Validation failed" in str(result.err())


def test_exporter_timeseries_error(tmp_path, caplog):
    """Test that time series export errors are properly logged and returned."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()
    exporter = ExporterWithTimeSeriesError(config, system, data_store=data_store)

    result = exporter.export()
    assert result.is_err()
    assert "Time series export failed" in str(result.err())


def test_exporter_postprocess_error(tmp_path, caplog):
    """Test that postprocess errors are properly logged and returned."""
    config = MockConfig(output_dir=tmp_path)
    system = System()
    data_store = DataStore()
    exporter = ExporterWithPostprocessError(config, system, data_store=data_store)

    result = exporter.export()
    assert result.is_err()
    assert "Postprocess failed" in str(result.err())
