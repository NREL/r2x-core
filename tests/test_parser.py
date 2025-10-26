"""Tests for parser module."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from infrasys import Component

from r2x_core.datafile import DataFile
from r2x_core.exceptions import ComponentCreationError, ParserError, ValidationError
from r2x_core.parser import BaseParser
from r2x_core.plugin_config import PluginConfig
from r2x_core.result import Err, Ok
from r2x_core.store import DataStore


class MockModelConfig(PluginConfig):
    """Test configuration."""

    model_year: int
    scenario: str = "base"


class MockComponent(Component):
    """Mock infrasys Component with extra fields."""

    value: float = 0.0
    extra_field: str | None = None


class MockBus(Component):
    """Mock Bus component based on infrasys.Component."""

    voltage: float = 230.0


class MockParser(BaseParser):
    """Test parser implementation."""

    def __init__(self, config: MockModelConfig, data_store: DataStore | None = None, **kwargs):
        super().__init__(config, data_store=data_store, **kwargs)
        self.model_year = config.model_year
        self.validation_called = False
        self.components_built = False
        self.time_series_built = False
        self.post_process_called = False

    def validate_inputs(self) -> None:
        """Test validation."""
        self.validation_called = True
        if self.model_year < 2020:
            raise ValidationError("Model year must be >= 2020")
        return Ok()

    def build_system_components(self) -> None:
        """Test component building."""
        self.components_built = True
        bus1 = self.create_component(MockBus, name="Bus1", voltage=230.0)
        self.add_component(bus1)
        bus2 = self.create_component(MockBus, name="Bus2", voltage=500.0)
        self.add_component(bus2)
        return Ok()

    def build_time_series(self) -> None:
        """Test time series building."""
        self.time_series_built = True
        mock_ts = Mock()
        bus = next(iter(self.system.get_components(MockBus)))
        self.add_time_series(bus, mock_ts)
        return Ok()

    def post_process_system(self) -> None:
        """Test post-processing."""
        self.post_process_called = True
        return Ok()


@pytest.fixture
def sample_config():
    """Create sample configuration."""
    return MockModelConfig(
        model_year=2030,
        scenario="test",
    )


@pytest.fixture
def sample_data_store(tmp_path):
    """Create sample data store."""
    bus_file = tmp_path / "buses.csv"
    bus_file.write_text("name,voltage\nBus1,230\nBus2,500\n")

    data_store = DataStore(tmp_path)
    data_store.add_data(DataFile(name="buses", fpath=bus_file))

    return data_store


@pytest.fixture
def mock_parser(sample_config, sample_data_store):
    """Create mock parser instance."""
    return MockParser(sample_config, data_store=sample_data_store)


def test_config_creation():
    """Test creating a config instance."""
    config = MockModelConfig(model_year=2030, scenario="test")
    assert config.model_year == 2030
    assert config.scenario == "test"


def test_config_validation():
    """Test Pydantic validation works."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MockModelConfig(scenario="test")  # Missing required model_year


def test_parser_data_store_error(sample_config):
    class NotDataSstore: ...

    with pytest.raises(TypeError):
        MockParser(sample_config, data_store=NotDataSstore())


def test_parser_initialization(mock_parser, sample_config, sample_data_store):
    """Test parser initialization."""
    assert mock_parser.config == sample_config
    assert mock_parser.store == sample_data_store
    assert mock_parser.system
    assert mock_parser.auto_add_composed_components is True
    assert mock_parser.skip_validation is False


def test_parser_custom_name(sample_config, sample_data_store):
    """Test parser with custom name."""
    parser = MockParser(sample_config, sample_data_store, system_name="custom_system")
    assert parser.system.name == "custom_system"


def test_parser_skip_validation(sample_config, sample_data_store):
    """Test parser with skip_validation flag."""
    parser = MockParser(sample_config, store=sample_data_store, skip_validation=True)
    assert parser.skip_validation is True


def test_validation_error_stops_build(sample_data_store):
    """Test that validation errors prevent system build."""
    config = MockModelConfig(model_year=2019, scenario="test")  # Invalid year
    parser = MockParser(config, store=sample_data_store)

    with patch("infrasys.system.System") as mock_system_class:
        with pytest.raises(ValidationError, match="Model year must be >= 2020"):
            parser.build_system()

        mock_system_class.assert_not_called()


def test_get_data(mock_parser: BaseParser, tmp_path):
    """Test get_data method."""
    test_file = tmp_path / "test.csv"
    test_file.write_text("data")
    mock_parser.store.add_data(DataFile(name="test_data", fpath=test_file))

    data_file = mock_parser.get_data("test_data")
    assert data_file.name == "test_data"


def test_get_data_not_found(mock_parser):
    """Test get_data with missing key."""
    with pytest.raises(KeyError):
        mock_parser.get_data("missing")


def test_read_data_file(mock_parser):
    """Test read_data_file method."""
    data = mock_parser.read_data_file("buses")
    assert data is not None


def test_create_component(mock_parser):
    """Test create_component method."""
    component = mock_parser.create_component(MockBus, name="TestBus", voltage=230.0)
    assert isinstance(component, MockBus)
    assert component.name == "TestBus"
    assert component.voltage == 230.0


def test_create_component_filters_invalid_fields(mock_parser):
    """Test that create_component filters invalid fields."""
    component = mock_parser.create_component(
        MockBus,
        name="TestBus",
        voltage=230.0,
        invalid_field="should_be_ignored",  # Not in model_fields
        another_invalid=123,
    )
    assert component.name == "TestBus"
    assert component.voltage == 230.0
    assert not hasattr(component, "invalid_field")


def test_create_component_filters_none_values(mock_parser):
    """Test that create_component filters None values."""
    component = mock_parser.create_component(
        MockBus,
        name="TestBus",
        voltage=None,  # Should be filtered out
    )
    assert component.name == "TestBus"


def test_create_component_skip_validation(mock_parser):
    """Test create_component with skip_validation=True."""
    mock_parser.skip_validation = True
    component = mock_parser.create_component(MockBus, name="TestBus")
    assert component.name == "TestBus"


def test_create_component_validation_error(mock_parser: BaseParser):
    """Test create_component with validation error."""
    with pytest.raises(ComponentCreationError, match="MockBus"):
        mock_parser.create_component(MockBus)


def test_validate_inputs_hook(mock_parser):
    """Test validate_inputs hook method."""
    mock_parser.validate_inputs()
    assert mock_parser.validation_called is True


def test_post_process_system_hook(mock_parser):
    """Test post_process_system hook method."""
    mock_parser.post_process_system()
    assert mock_parser.post_process_called is True


def test_plugin_workflow(mock_parser):
    """Test individual method calls for plugin integration."""
    mock_system = MagicMock()
    mock_system.get_components.return_value = [MockBus(name="Bus1")]

    mock_parser.validate_inputs()
    assert mock_parser.validation_called is True

    mock_parser.build_system_components()
    assert mock_parser.components_built is True

    mock_parser.build_time_series()
    assert mock_parser.time_series_built is True

    mock_parser.post_process_system()
    assert mock_parser.post_process_called is True


def test_cannot_instantiate_base_parser(sample_config, sample_data_store):
    """Test that BaseParser cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseParser(sample_config, sample_data_store)


def test_must_implementbuild_system_components(sample_config, sample_data_store):
    """Test that build_system_components must be implemented."""

    class IncompleteParser(BaseParser):
        def build_time_series(self):
            pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteParser(sample_config, store=sample_data_store)


def test_must_implementbuild_time_series(sample_config, sample_data_store):
    """Test that build_time_series must be implemented."""

    class IncompleteParser(BaseParser):
        def build_system_components(self):
            pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteParser(sample_config, store=sample_data_store)


def test_parser_with_custom_validation(tmp_path):
    """Test parser with custom validation logic."""

    class ValidatingParser(BaseParser):
        def validate_inputs(self):
            required = ["buses", "generators"]
            data_files = self.store.list_data()
            for name in required:
                if name not in data_files:
                    raise ValidationError(f"Required file '{name}' missing")

        def build_system_components(self):
            pass

        def build_time_series(self):
            pass

    bus_file = tmp_path / "buses.csv"
    bus_file.write_text("name,voltage\nBus1,230\n")
    data_store = DataStore(tmp_path)
    data_store.add_data(DataFile(name="buses", fpath=bus_file))

    config = PluginConfig()
    parser = ValidatingParser(config, store=data_store)

    with patch("infrasys.system.System") as mock_system_class:
        mock_system = MagicMock()
        mock_system_class.return_value = mock_system

        with pytest.raises(ValidationError):
            parser.build_system()


@pytest.mark.parametrize(
    "fail_stage",
    [
        "validate_inputs",
        "prepare_data",
        "build_system_components",
        "build_time_series",
        "postprocess_system",
        "validate_system",
    ],
)
def test_build_system_fails_on_specific_stage(fail_stage):
    class MockParser(BaseParser):
        def validate_inputs(self):
            return Err(ValidationError("Stage failed")) if fail_stage == "validate_inputs" else Ok(None)

        def prepare_data(self):
            return Err(ValidationError("Stage failed")) if fail_stage == "prepare_data" else Ok(None)

        def build_system_components(self):
            return (
                Err(ValidationError("Stage failed")) if fail_stage == "build_system_components" else Ok(None)
            )

        def build_time_series(self):
            return Err(ValidationError("Stage failed")) if fail_stage == "build_time_series" else Ok(None)

        def postprocess_system(self):
            return Err(ValidationError("Stage failed")) if fail_stage == "postprocess_system" else Ok(None)

        def validate_system(self):
            return Err(ValidationError("Stage failed")) if fail_stage == "validate_system" else Ok(None)

    parser = MockParser(config=PluginConfig())

    with pytest.raises(ParserError):
        parser.build_system()
