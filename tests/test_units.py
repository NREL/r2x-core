"""Tests for unit system."""

from typing import Annotated

import pytest

from r2x_core.units import Unit, UnitAwareModel, UnitSystem, set_unit_system


# Test Models
class Generator(UnitAwareModel):
    """Test generator model."""

    name: str
    base_power: Annotated[float, Unit("MVA")]
    rated_voltage: Annotated[float, Unit("kV")]
    rating: Annotated[float, Unit("pu", base="base_power")]
    voltage: Annotated[float, Unit("pu", base="rated_voltage")]


class SimpleComponent(UnitAwareModel):
    """Simple component with just base_power."""

    name: str
    base_power: Annotated[float, Unit("MVA")]
    active_power: Annotated[float, Unit("pu", base="base_power")]


# Basic Input Tests
def test_create_with_pu_values():
    """Test creating component with plain pu values."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    assert gen.name == "G1"
    assert gen.base_power == 100.0
    assert gen.rated_voltage == 13.8
    assert gen.rating == 0.8
    assert gen.voltage == 1.05


def test_create_with_natural_units():
    """Test creating component with natural unit input (auto-converts to pu)."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating={"value": 80.0, "unit": "MW"},
        voltage={"value": 14.49, "unit": "kV"},
    )

    # Internal storage should be in pu
    assert gen.rating == 0.8  # 80 MW / 100 MVA = 0.8 pu
    assert gen.voltage == pytest.approx(1.05, rel=0.01)  # 14.49 kV / 13.8 kV = 1.05 pu


def test_create_with_mixed_units():
    """Test creating component with mixed pu and natural units."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,  # Already pu
        voltage={"value": 14.49, "unit": "kV"},  # Natural - converts to pu
    )

    assert gen.rating == 0.8
    assert gen.voltage == pytest.approx(1.05, rel=0.01)


def test_default_base_power():
    """Test that Unit['pu'] defaults to base_power."""
    comp = SimpleComponent(
        name="C1",
        base_power=50.0,
        active_power=0.5,
    )

    assert comp.active_power == 0.5


# Display Tests
def test_display_device_base():
    """Test display in device base (default)."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    # Default display should be device base
    repr_str = repr(gen)
    assert "0.8 pu" in repr_str
    assert "1.05 pu" in repr_str
    assert "100.0 MVA" in repr_str
    assert "13.8 kV" in repr_str


def test_display_natural_units():
    """Test display in natural units."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    # Set display mode to natural units
    set_unit_system(UnitSystem.NATURAL_UNITS)

    repr_str = repr(gen)
    assert "80" in repr_str and "MVA" in repr_str  # rating: 0.8 * 100 MVA = 80 MVA
    assert "14.49" in repr_str and "kV" in repr_str  # voltage: 1.05 * 13.8 kV = 14.49 kV

    # Reset to default
    set_unit_system(UnitSystem.DEVICE_BASE)


def test_display_system_base():
    """Test display in system base."""
    from r2x_core.system import System

    # Create a system with system_base_power=200 MVA
    system = System(name="TestSystem", system_base_power=200.0)

    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    # Add generator to system (this sets _system_base on the component)
    system.add_component(gen)

    # Set display mode to system base
    set_unit_system(UnitSystem.SYSTEM_BASE)

    repr_str = repr(gen)
    # rating: 0.8 pu * 100 MVA = 80 MVA / 200 MVA = 0.4 pu (system)
    assert "0.4" in repr_str and "pu (system)" in repr_str

    # Reset to default for other tests
    set_unit_system(UnitSystem.DEVICE_BASE)


# Field Access Tests
def test_field_access_returns_float():
    """Test that field access returns plain float for calculations."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    # Should return plain float
    assert isinstance(gen.rating, float)
    assert gen.rating == 0.8

    # Math should work
    result = gen.rating * 2
    assert result == 1.6


def test_field_assignment():
    """Test that field assignment works."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    gen.rating = 0.9
    assert gen.rating == 0.9


# Conversion Tests
def test_convert_power_to_pu():
    """Test converting MW to pu."""
    gen = Generator(
        name="G1",
        base_power=50.0,  # 50 MVA base
        rated_voltage=13.8,
        rating={"value": 40.0, "unit": "MW"},  # Should convert to 0.8 pu
        voltage=1.0,
    )

    assert gen.rating == 0.8  # 40 MW / 50 MVA = 0.8 pu


def test_convert_voltage_to_pu():
    """Test converting kV to pu."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=138.0,  # 138 kV base
        rating=1.0,
        voltage={"value": 144.9, "unit": "kV"},  # Should convert to 1.05 pu
    )

    assert gen.voltage == pytest.approx(1.05, rel=0.01)  # 144.9 / 138 = 1.05 pu


# Edge Cases
def test_missing_natural_unit_in_spec():
    """Test display when natural_unit is not specified."""

    class ComponentNoNaturalUnit(UnitAwareModel):
        name: str
        base_power: Annotated[float, Unit("MVA")]
        rating: Annotated[float, Unit("pu", base="base_power")]

    comp = ComponentNoNaturalUnit(name="C1", base_power=100.0, rating=0.8)
    set_unit_system(UnitSystem.NATURAL_UNITS)

    # Should convert to natural units (MVA)
    repr_str = repr(comp)
    assert "80" in repr_str  # 0.8 * 100 MVA = 80 MVA

    # Reset to default
    set_unit_system(UnitSystem.DEVICE_BASE)


def test_component_without_system_base():
    """Test component display without system_base set."""
    gen = Generator(
        name="G1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    # Try to display in system base mode without system_base set
    set_unit_system(UnitSystem.SYSTEM_BASE)
    # Should fallback to pu display
    repr_str = repr(gen)
    assert "pu" in repr_str

    # Reset to default
    set_unit_system(UnitSystem.DEVICE_BASE)
