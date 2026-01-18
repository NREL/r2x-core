"""Tests for :mod:`r2x_core.utils.parser` utilities."""

from fixtures.source_system import BusComponent
from pydantic import ValidationError

from r2x_core.utils.parser import create_component


def test_create_component_success():
    """Test creating a valid component."""
    result = create_component(BusComponent, name="Bus1", voltage_kv=345.0)
    assert result.is_ok()
    bus = result.unwrap()
    assert bus.name == "Bus1"
    assert bus.voltage_kv == 345.0


def test_create_component_with_skip_none_true():
    """Test creating component with skip_none=True (default)."""
    result = create_component(
        BusComponent,
        skip_none=True,
        name="Bus1",
        voltage_kv=345.0,
        zone=None,  # Should be skipped
    )
    assert result.is_ok()
    bus = result.unwrap()
    assert bus.name == "Bus1"


def test_create_component_with_skip_none_false():
    """Test creating component with skip_none=False."""
    result = create_component(
        BusComponent,
        skip_none=False,
        name="Bus1",
        voltage_kv=345.0,
    )
    assert result.is_ok()
    bus = result.unwrap()
    assert bus.name == "Bus1"


def test_create_component_with_skip_validation_true():
    """Test creating component with skip_validation=True."""
    result = create_component(
        BusComponent,
        skip_validation=True,
        name="Bus1",
        voltage_kv=345.0,
    )
    assert result.is_ok()
    bus = result.unwrap()
    assert bus.name == "Bus1"
    assert bus.voltage_kv == 345.0


def test_create_component_with_skip_validation_false():
    """Test creating component with skip_validation=False (default)."""
    result = create_component(
        BusComponent,
        skip_validation=False,
        name="Bus1",
        voltage_kv=345.0,
    )
    assert result.is_ok()
    bus = result.unwrap()
    assert bus.name == "Bus1"


def test_create_component_validation_error():
    """Test creating component with invalid data returns Err."""
    # BusComponent has optional fields with defaults, so we need to pass invalid type
    result = create_component(
        BusComponent,
        name="Bus1",
        voltage_kv="not_a_number",  # Should be float
    )
    assert result.is_err()
    error = result.unwrap_err()
    assert isinstance(error, ValidationError)


def test_create_component_invalid_field_type():
    """Test validation error for wrong field type in optional field."""
    result = create_component(
        BusComponent,
        name="Bus1",
        voltage_kv=345.0,
        load_mw="not_a_number",  # Should be float
    )
    assert result.is_err()
    error = result.unwrap_err()
    assert isinstance(error, ValidationError)


def test_create_component_filters_invalid_fields():
    """Test that invalid field names are filtered out."""
    result = create_component(
        BusComponent,
        name="Bus1",
        voltage_kv=345.0,
        invalid_field="should_be_ignored",
    )
    assert result.is_ok()
    bus = result.unwrap()
    assert bus.name == "Bus1"
    assert not hasattr(bus, "invalid_field")


def test_create_component_with_optional_field():
    """Test creating component with optional field."""
    result = create_component(
        BusComponent,
        name="Bus1",
        voltage_kv=345.0,
        zone="North",
    )
    assert result.is_ok()
    bus = result.unwrap()
    assert bus.name == "Bus1"
    assert bus.zone == "North"
