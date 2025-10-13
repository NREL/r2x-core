"""Tests for units._utils internal utility functions."""

from typing import Annotated

import pytest
from infrasys import Component

from r2x_core.units import HasUnits, Unit, UnitSystem, set_unit_system
from r2x_core.units._specs import UnitSpec
from r2x_core.units._utils import (
    _convert_to_internal,
    _format_for_display,
    _get_base_unit_from_context,
    _get_base_unit_from_subclass,
    _is_annotated,
)


def test_convert_to_internal_with_int():
    """Test _convert_to_internal with int value."""
    spec = UnitSpec(unit="MVA", base=None)
    result = _convert_to_internal(50, spec)
    assert result == 50.0


def test_convert_to_internal_with_float():
    """Test _convert_to_internal with float value."""
    spec = UnitSpec(unit="MVA", base=None)
    result = _convert_to_internal(50.5, spec)
    assert result == 50.5


def test_convert_to_internal_with_invalid_type():
    """Test _convert_to_internal with invalid type returns 0.0."""
    spec = UnitSpec(unit="MVA", base=None)
    result = _convert_to_internal("invalid", spec)
    assert result == 0.0


def test_convert_to_internal_dict_missing_value_key():
    """Test _convert_to_internal with dict missing 'value' key."""
    spec = UnitSpec(unit="MVA", base=None)
    result = _convert_to_internal({"unit": "MVA"}, spec)
    assert result == 0.0


def test_convert_to_internal_dict_missing_unit_key():
    """Test _convert_to_internal with dict missing 'unit' key."""
    spec = UnitSpec(unit="MVA", base=None)
    result = _convert_to_internal({"value": 100.0}, spec)
    assert result == 0.0


def test_convert_to_internal_missing_base_value():
    """Test _convert_to_internal raises when base_value is None but required."""
    spec = UnitSpec(unit="pu", base="base_power")
    value = {"value": 1.0, "unit": "MVA"}

    with pytest.raises(ValueError, match=r"Base field 'base_power' is required.*not provided"):
        _convert_to_internal(value, spec, base_value=None, base_unit="MVA")


def test_convert_to_internal_missing_base_unit():
    """Test _convert_to_internal raises when base_unit is None but required."""
    spec = UnitSpec(unit="pu", base="base_power")
    value = {"value": 1.0, "unit": "MVA"}

    with pytest.raises(ValueError, match=r"Base unit for field 'base_power' could not be determined"):
        _convert_to_internal(value, spec, base_value=100.0, base_unit=None)


def test_convert_to_internal_with_invalid_unit():
    """Test _convert_to_internal handles invalid pint units gracefully."""
    spec = UnitSpec(unit="pu", base="base_power")
    value = {"value": 100.0, "unit": "InvalidUnit"}

    # Should fall back to simple division
    result = _convert_to_internal(value, spec, base_value=100.0, base_unit="MVA")
    assert result == 1.0


def test_convert_to_internal_with_dimensionality_error():
    """Test _convert_to_internal handles dimensionality errors gracefully."""
    spec = UnitSpec(unit="pu", base="base_power")
    value = {"value": 100.0, "unit": "m"}  # Length unit, incompatible with power

    # Should fall back to simple division
    result = _convert_to_internal(value, spec, base_value=100.0, base_unit="MVA")
    assert result == 1.0


def test_format_for_display_device_base_no_base_value():
    """Test _format_for_display in DEVICE_BASE mode when base_value is None."""
    spec = UnitSpec(unit="pu", base="base_power")
    set_unit_system(UnitSystem.DEVICE_BASE)

    result = _format_for_display(0.8, spec, UnitSystem.DEVICE_BASE)
    assert result == "0.8 pu"


def test_format_for_display_natural_units_no_base():
    """Test _format_for_display in NATURAL_UNITS mode when base_value is None."""
    spec = UnitSpec(unit="pu", base="base_power")

    result = _format_for_display(0.8, spec, UnitSystem.NATURAL_UNITS, base_value=None, base_unit="MVA")
    assert result == "0.8 pu"


def test_format_for_display_system_base_no_base_value():
    """Test _format_for_display in SYSTEM_BASE mode when base_value is None."""
    spec = UnitSpec(unit="pu", base="base_power")

    result = _format_for_display(0.8, spec, UnitSystem.SYSTEM_BASE, base_value=None)
    assert result == "0.8 pu"


def test_format_for_display_system_base_no_system_base():
    """Test _format_for_display in SYSTEM_BASE mode when system_base is None."""
    spec = UnitSpec(unit="pu", base="base_power")

    result = _format_for_display(
        0.8, spec, UnitSystem.SYSTEM_BASE, base_value=100.0, base_unit="MVA", system_base=None
    )
    assert result == "0.8 pu"


def test_is_annotated_with_annotated_type():
    """Test _is_annotated returns True for Annotated types."""
    annotated_type = Annotated[float, Unit("MVA")]
    assert _is_annotated(annotated_type) is True


def test_is_annotated_with_plain_type():
    """Test _is_annotated returns False for plain types."""
    assert _is_annotated(float) is False
    assert _is_annotated(int) is False
    assert _is_annotated(str) is False


def test_is_annotated_with_invalid_input():
    """Test _is_annotated returns False for invalid input."""
    assert _is_annotated(None) is False
    assert _is_annotated(123) is False
    assert _is_annotated("string") is False


def test_get_base_unit_from_context_not_dict():
    """Test _get_base_unit_from_context returns None when context is not dict."""
    assert _get_base_unit_from_context(None, "base_power") is None
    assert _get_base_unit_from_context("invalid", "base_power") is None
    assert _get_base_unit_from_context(123, "base_power") is None


def test_get_base_unit_from_context_no_base_units_map():
    """Test _get_base_unit_from_context returns None when base_units not in context."""
    context = {"other_key": "value"}
    assert _get_base_unit_from_context(context, "base_power") is None


def test_get_base_unit_from_context_base_units_not_dict():
    """Test _get_base_unit_from_context returns None when base_units is not dict."""
    context = {"base_units": "not_a_dict"}
    assert _get_base_unit_from_context(context, "base_power") is None


def test_get_base_unit_from_context_value_not_string():
    """Test _get_base_unit_from_context returns None when value is not string."""
    context = {"base_units": {"base_power": 123}}
    assert _get_base_unit_from_context(context, "base_power") is None


def test_get_base_unit_from_subclass_no_owner():
    """Test _get_base_unit_from_subclass returns None when owner_name is None."""
    assert _get_base_unit_from_subclass(None, "base_power") is None
    assert _get_base_unit_from_subclass("", "base_power") is None


def test_get_base_unit_from_subclass_not_found():
    """Test _get_base_unit_from_subclass returns None when class not found."""
    result = _get_base_unit_from_subclass("NonExistentClass", "base_power")
    assert result is None


def test_get_base_unit_from_subclass_found():
    """Test _get_base_unit_from_subclass finds unit from subclass."""

    class TestComponent(HasUnits, Component):
        """Test component with units."""

        base_power: Annotated[float, Unit("MVA")]
        rating: Annotated[float, Unit("pu", base="base_power")]

    result = _get_base_unit_from_subclass("TestComponent", "base_power")
    assert result == "MVA"


def test_get_base_unit_from_subclass_recursive_search():
    """Test _get_base_unit_from_subclass searches recursively through inheritance."""

    class Level1Component(HasUnits, Component):
        """Level 1 component."""

        voltage: Annotated[float, Unit("kV")]

    class Level2Component(Level1Component):
        """Level 2 component - intermediate."""

        current: Annotated[float, Unit("A")]

    class Level3Component(Level2Component):
        """Level 3 component - deepest level."""

        base_power: Annotated[float, Unit("MVA")]
        rating: Annotated[float, Unit("pu", base="base_power")]

    # Search for Level3Component's base_power through the hierarchy
    result = _get_base_unit_from_subclass("Level3Component", "base_power")
    assert result == "MVA"
