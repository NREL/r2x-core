"""Tests for parser module."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from r2x_core.parser import BaseParser, ParserConfig
from r2x_core.store import DataStore
from r2x_core.datafile import DataFile
from r2x_core.exceptions import ParserError, ValidationError, ComponentCreationError


# Mock configuration for testing
class MockModelConfig(ParserConfig):
    """Test configuration."""

    model_year: int
    scenario: str = "base"


# Mock component classes for testing
class MockComponent:
    """Mock infrasys Component."""

    model_fields = {"name": None, "value": None, "extra_field": None}

    def __init__(self, name: str, value: float = 0.0):
        self.name = name
        self.value = value

    @classmethod
    def model_validate(cls, data: dict):
        """Mock validation."""
        if "name" not in data:
            raise ValueError("name is required")
        return cls(**data)

    @classmethod
    def model_construct(cls, **data):
        """Mock construction without validation."""
        return cls(**{k: v for k, v in data.items() if k in ["name", "value"]})


class MockBus(MockComponent):
    """Mock Bus component."""

    model_fields = {"name": None, "voltage": None}

    def __init__(self, name: str, voltage: float = 230.0):
        self.name = name
        self.voltage = voltage


# Mock parser implementation for testing
class MockParser(BaseParser):
    """Test parser implementation."""

    def __init__(self, config: MockModelConfig, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)
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

    def _build_system_components(self) -> None:
        """Test component building."""
        self.components_built = True
        # Create test components
        bus1 = self.create_component(MockBus, name="Bus1", voltage=230.0)
        self.add_component(bus1)
        bus2 = self.create_component(MockBus, name="Bus2", voltage=500.0)
        self.add_component(bus2)

    def _build_time_series(self) -> None:
        """Test time series building."""
        self.time_series_built = True
        # Mock time series attachment
        mock_ts = Mock()
        bus = list(self.system.get_components(MockBus))[0]
        self.add_time_series(bus, mock_ts)

    def post_process_system(self) -> None:
        """Test post-processing."""
        self.post_process_called = True


@pytest.fixture
def sample_config():
    """Create sample configuration."""
    return MockModelConfig(
        model_year=2030,
        scenario="test",
        defaults={"tech_map": {"wind": "renewable"}},
    )


@pytest.fixture
def sample_data_store(tmp_path):
    """Create sample data store."""
    # Create test data file
    bus_file = tmp_path / "buses.csv"
    bus_file.write_text("name,voltage\nBus1,230\nBus2,500\n")

    # Create data store
    data_store = DataStore(folder=tmp_path)
    data_store.add_data_file(DataFile(name="buses", fpath=bus_file))

    return data_store


@pytest.fixture
def mock_parser(sample_config, sample_data_store):
    """Create mock parser instance."""
    return MockParser(sample_config, sample_data_store)


# ParserConfig tests


def test_config_creation():
    """Test creating a config instance."""
    config = MockModelConfig(model_year=2030, scenario="test")
    assert config.model_year == 2030
    assert config.scenario == "test"
    assert config.defaults == {}


def test_config_with_defaults():
    """Test config with defaults."""
    config = MockModelConfig(
        model_year=2025,
        defaults={"excluded_techs": ["coal"]},
    )
    assert config.defaults == {"excluded_techs": ["coal"]}


def test_config_validation():
    """Test Pydantic validation works."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        MockModelConfig(scenario="test")  # Missing required model_year


# BaseParser tests


def test_parser_initialization(mock_parser, sample_config, sample_data_store):
    """Test parser initialization."""
    assert mock_parser.config == sample_config
    assert mock_parser.data_store == sample_data_store
    assert mock_parser.system is None
    assert mock_parser.name == "system"
    assert mock_parser.auto_add_composed_components is True
    assert mock_parser.skip_validation is False


def test_parser_custom_name(sample_config, sample_data_store):
    """Test parser with custom name."""
    parser = MockParser(sample_config, sample_data_store, name="custom_system")
    assert parser.name == "custom_system"


def test_parser_skip_validation(sample_config, sample_data_store):
    """Test parser with skip_validation flag."""
    parser = MockParser(sample_config, sample_data_store, skip_validation=True)
    assert parser.skip_validation is True


def test_build_system_workflow(mock_parser):
    """Test complete build_system workflow."""
    # Patch the System import at the actual location
    with patch("infrasys.system.System") as mock_system_class:
        mock_system = MagicMock()
        mock_system.get_components.return_value = [MockBus(name="Bus1")]
        mock_system_class.return_value = mock_system

        # Build system
        system = mock_parser.build_system()

        # Verify workflow
        assert mock_parser.validation_called is True
        assert mock_parser.components_built is True
        assert mock_parser.time_series_built is True
        assert mock_parser.post_process_called is True
        assert system == mock_system
        mock_system_class.assert_called_once()


def test_validation_error_stops_build(sample_data_store):
    """Test that validation errors prevent system build."""
    config = MockModelConfig(model_year=2019, scenario="test")  # Invalid year
    parser = MockParser(config, sample_data_store)

    # Use patch to ensure System is not created
    with patch("infrasys.system.System") as mock_system_class:
        with pytest.raises(ValidationError, match="Model year must be >= 2020"):
            parser.build_system()

        # System should not have been created
        mock_system_class.assert_not_called()


def test_get_data(mock_parser, tmp_path):
    """Test get_data method."""
    # Add mock data to data store
    test_file = tmp_path / "test.csv"
    test_file.write_text("data")
    mock_parser.data_store.add_data_file(DataFile(name="test_data", fpath=test_file))

    data_file = mock_parser.get_data("test_data")
    assert data_file.name == "test_data"


def test_get_data_not_found(mock_parser):
    """Test get_data with missing key."""
    with pytest.raises(KeyError, match="Data file 'missing' not found"):
        mock_parser.get_data("missing")


def test_read_data_file(mock_parser):
    """Test read_data_file method."""
    data = mock_parser.read_data_file("buses")
    assert data is not None


def test_read_data_file_not_found(mock_parser):
    """Test read_data_file with missing file."""
    with pytest.raises(ParserError, match="Data file 'missing' not found"):
        mock_parser.read_data_file("missing")


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


def test_create_component_validation_error(mock_parser):
    """Test create_component with validation error."""
    with pytest.raises(ComponentCreationError, match="error creating MockBus"):
        mock_parser.create_component(MockBus)  # Missing required 'name'


def test_add_component_before_system_created(mock_parser):
    """Test add_component before system is created."""
    component = mock_parser.create_component(MockBus, name="TestBus")
    with pytest.raises(ParserError, match="System has not been created yet"):
        mock_parser.add_component(component)


def test_add_component_success(mock_parser):
    """Test successful component addition."""
    # Create system first
    mock_system = MagicMock()
    mock_parser.system = mock_system

    component = MockBus(name="TestBus")
    mock_parser.add_component(component)

    mock_system.add_component.assert_called_once_with(component)


def test_add_time_series_before_system_created(mock_parser):
    """Test add_time_series before system is created."""
    component = MockBus(name="TestBus")
    mock_ts = Mock()
    with pytest.raises(ParserError, match="System has not been created yet"):
        mock_parser.add_time_series(component, mock_ts)


def test_add_time_series_success(mock_parser):
    """Test successful time series addition."""
    # Create system first
    mock_system = MagicMock()
    mock_parser.system = mock_system

    component = MockBus(name="TestBus")
    mock_ts = Mock()
    mock_parser.add_time_series(component, mock_ts)

    mock_system.add_time_series.assert_called_once_with(mock_ts, component)


def test_validate_inputs_hook(mock_parser):
    """Test validate_inputs hook method."""
    mock_parser.validate_inputs()
    assert mock_parser.validation_called is True


def test_build_system_components_public_method(mock_parser):
    """Test build_system_components public method."""
    # Create system first
    mock_system = MagicMock()
    mock_parser.system = mock_system

    mock_parser.build_system_components()
    assert mock_parser.components_built is True


def test_build_time_series_public_method(mock_parser):
    """Test build_time_series public method."""
    # Create system first
    mock_system = MagicMock()
    mock_system.get_components.return_value = [MockBus(name="Bus1")]
    mock_parser.system = mock_system

    mock_parser.build_time_series()
    assert mock_parser.time_series_built is True


def test_post_process_system_hook(mock_parser):
    """Test post_process_system hook method."""
    mock_parser.post_process_system()
    assert mock_parser.post_process_called is True


def test_plugin_workflow(mock_parser):
    """Test individual method calls for plugin integration."""
    # Create a mock system
    mock_system = MagicMock()
    mock_system.get_components.return_value = [MockBus(name="Bus1")]

    # Call methods individually (plugin workflow)
    mock_parser.validate_inputs()
    assert mock_parser.validation_called is True

    # Create system manually (simulating manual control)
    mock_parser.system = mock_system

    # Build components
    mock_parser.build_system_components()
    assert mock_parser.components_built is True

    # Custom modifications could happen here in real plugin...

    # Build time series
    mock_parser.build_time_series()
    assert mock_parser.time_series_built is True

    # Post-process
    mock_parser.post_process_system()
    assert mock_parser.post_process_called is True


# Parser abstract methods tests


def test_cannot_instantiate_base_parser(sample_config, sample_data_store):
    """Test that BaseParser cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseParser(sample_config, sample_data_store)


def test_must_implement_build_system_components(sample_config, sample_data_store):
    """Test that _build_system_components must be implemented."""

    class IncompleteParser(BaseParser):
        def _build_time_series(self):
            pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteParser(sample_config, sample_data_store)


def test_must_implement_build_time_series(sample_config, sample_data_store):
    """Test that _build_time_series must be implemented."""

    class IncompleteParser(BaseParser):
        def _build_system_components(self):
            pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteParser(sample_config, sample_data_store)


# Parser integration tests


def test_full_parser_workflow_with_data(tmp_path):
    """Test full parser workflow with actual data files."""
    # Create test data files
    bus_file = tmp_path / "buses.csv"
    bus_file.write_text("name,voltage\nBus1,230\nBus2,500\n")

    # Create data store
    data_store = DataStore(folder=tmp_path)
    data_store.add_data_file(DataFile(name="buses", fpath=bus_file))

    # Create config
    config = MockModelConfig(model_year=2030, scenario="integration_test")

    # Create parser
    parser = MockParser(config, data_store, name="integration_system")

    # Mock System
    with patch("infrasys.system.System") as mock_system_class:
        mock_system = MagicMock()
        mock_system.get_components.return_value = [MockBus(name="Bus1")]
        mock_system_class.return_value = mock_system

        # Build system
        system = parser.build_system()

        # Verify complete workflow
        assert parser.validation_called is True
        assert parser.components_built is True
        assert parser.time_series_built is True
        assert parser.post_process_called is True
        assert system == mock_system
        assert parser.name == "integration_system"


def test_parser_with_custom_validation(tmp_path):
    """Test parser with custom validation logic."""

    class ValidatingParser(BaseParser):
        def validate_inputs(self):
            # Check required files
            required = ["buses", "generators"]
            data_files = self.data_store.list_data_files()
            for name in required:
                if name not in data_files:
                    raise ValidationError(f"Required file '{name}' missing")

        def _build_system_components(self):
            pass

        def _build_time_series(self):
            pass

    # Create data store with only buses (no file needed, just checking validation)
    bus_file = tmp_path / "buses.csv"
    bus_file.write_text("name,voltage\nBus1,230\n")
    data_store = DataStore(folder=tmp_path)
    data_store.add_data_file(DataFile(name="buses", fpath=bus_file))

    config = ParserConfig()
    parser = ValidatingParser(config, data_store)

    # Use patch for System
    with patch("infrasys.system.System") as mock_system_class:
        mock_system = MagicMock()
        mock_system_class.return_value = mock_system

        # Should fail validation
        with pytest.raises(ValidationError, match="Required file 'generators' missing"):
            parser.build_system()


# Parser coverage tests


def test_read_data_file_generic_exception(mock_parser):
    """Test read_data_file with generic exception."""
    # Mock data_store.read_data_file to raise a generic exception
    with patch.object(mock_parser.data_store, "read_data_file") as mock_read:
        mock_read.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(ParserError, match="Failed to read data file 'buses'"):
            mock_parser.read_data_file("buses")


def test_create_component_skip_validation_fallback(tmp_path):
    """Test create_component with skip_validation=True falling back to validation."""

    class FailingComponent(MockComponent):
        """Component that fails on model_construct but succeeds on validate."""

        @classmethod
        def model_construct(cls, **data):
            """Fail construction."""
            raise RuntimeError("Construction failed")

        @classmethod
        def model_validate(cls, data: dict):
            """Succeed on validation."""
            return cls(name=data["name"])

    bus_file = tmp_path / "buses.csv"
    bus_file.write_text("name\nBus1\n")
    data_store = DataStore(folder=tmp_path)
    data_store.add_data_file(DataFile(name="buses", fpath=bus_file))

    config = MockModelConfig(model_year=2030, scenario="test")
    parser = MockParser(config, data_store, skip_validation=True)

    # Should fall back to model_validate
    component = parser.create_component(FailingComponent, name="test")
    assert component.name == "test"


def test_create_component_pydantic_validation_error(mock_parser):
    """Test create_component with Pydantic validation error (not generic Exception)."""

    class StrictBus(MockBus):
        """Bus that raises Pydantic validation error."""

        @classmethod
        def model_validate(cls, data: dict):
            """Raise Pydantic validation error."""
            from pydantic import ValidationError as PydanticValidationError

            raise PydanticValidationError.from_exception_data(
                "test", [{"type": "missing", "loc": ("name",), "input": data}]
            )

    with pytest.raises(ComponentCreationError, match="Failed to create StrictBus"):
        mock_parser.create_component(StrictBus, voltage=230.0)


def test_empty_hook_methods_coverage(tmp_path):
    """Test that empty hook methods (pass statements) are covered."""

    class MinimalParser(BaseParser):
        """Parser with only required methods, using default hooks."""

        def _build_system_components(self):
            """Minimal implementation."""
            pass  # Line 952

        def _build_time_series(self):
            """Minimal implementation."""
            pass  # Line 1064

        # validate_inputs() not overridden - uses base class pass (line 816)
        # post_process_system() not overridden - uses base class pass (line 1123)

    bus_file = tmp_path / "buses.csv"
    bus_file.write_text("name\nBus1\n")
    data_store = DataStore(folder=tmp_path)
    data_store.add_data_file(DataFile(name="buses", fpath=bus_file))

    config = ParserConfig()
    parser = MinimalParser(config, data_store)

    with patch("infrasys.system.System") as mock_system_class:
        mock_system = MagicMock()
        mock_system.get_components.return_value = []
        mock_system_class.return_value = mock_system

        # This will execute all the pass statements
        system = parser.build_system()
        assert system == mock_system

        # Explicitly call hook methods to ensure coverage
        parser.validate_inputs()  # Line 816
        parser.post_process_system()  # Line 1123
