"""Test the HasUnits vs HasPerUnit class hierarchy."""

from typing import Annotated

import pytest
from infrasys import Component

from r2x_core.units import HasPerUnit, HasUnits, Unit, UnitSystem, set_unit_system


class Sensor(HasUnits, Component):
    """A sensor that only reports absolute values."""

    name: str
    temperature: Annotated[float, Unit("°C")]
    pressure: Annotated[float, Unit("Pa")]


class Generator(HasPerUnit, Component):
    """A generator with base values and per-unit fields."""

    name: str
    base_power: Annotated[float, Unit("MVA")]
    rated_voltage: Annotated[float, Unit("kV")]
    rating: Annotated[float, Unit("pu", base="base_power")]
    voltage: Annotated[float, Unit("pu", base="rated_voltage")]


def test_has_units_with_absolute_values():
    """Test HasUnits with only absolute unit fields."""
    sensor = Sensor(name="TempSensor1", temperature=25.0, pressure=101325.0)
    assert sensor.temperature == 25.0
    assert sensor.pressure == 101325.0


def test_has_units_repr_formatting():
    """Test HasUnits repr includes unit labels."""
    sensor = Sensor(name="TempSensor1", temperature=25.0, pressure=101325.0)
    repr_str = repr(sensor)
    assert "25.0 °C" in repr_str
    assert "101325.0 Pa" in repr_str


def test_has_per_units_with_pu_input():
    """Test HasPerUnit with per-unit input values."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.0,
    )
    assert gen.rating == 0.8
    assert gen.voltage == 1.0


def test_has_per_units_with_natural_unit_input():
    """Test HasPerUnit with natural unit dict input."""
    gen = Generator(
        name="Gen2",
        base_power=100.0,
        rated_voltage=13.8,
        rating={"value": 80.0, "unit": "MW"},  # type: ignore[arg-type]
        voltage={"value": 13.8, "unit": "kV"},  # type: ignore[arg-type]
    )
    assert gen.rating == pytest.approx(0.8, abs=1e-6)
    assert gen.voltage == pytest.approx(1.0, abs=1e-6)


def test_has_per_units_repr_device_base():
    """Test HasPerUnit repr in device base mode."""
    set_unit_system(UnitSystem.DEVICE_BASE)
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.0,
    )
    repr_str = repr(gen)
    assert "0.8 pu" in repr_str
    assert "1.0 pu" in repr_str


def test_has_per_units_repr_natural_units():
    """Test HasPerUnit repr in natural units mode."""
    set_unit_system(UnitSystem.NATURAL_UNITS)
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.0,
    )
    repr_str = repr(gen)
    assert "80" in repr_str
    assert "MVA" in repr_str
    assert "13.8" in repr_str
    assert "kV" in repr_str
    set_unit_system(UnitSystem.DEVICE_BASE)


def test_class_hierarchy_isinstance_sensor():
    """Test isinstance checks for HasUnits sensor."""
    sensor = Sensor(name="TempSensor1", temperature=25.0, pressure=101325.0)
    assert isinstance(sensor, HasUnits)
    assert not isinstance(sensor, HasPerUnit)


def test_class_hierarchy_isinstance_generator():
    """Test isinstance checks for HasPerUnit generator."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.0,
    )
    assert isinstance(gen, HasUnits)
    assert isinstance(gen, HasPerUnit)


def test_has_units_no_system_base_attribute():
    """Test that HasUnits does not have _system_base attribute."""
    sensor = Sensor(name="TempSensor1", temperature=25.0, pressure=101325.0)
    assert not hasattr(sensor, "_system_base")


def test_has_per_units_has_system_base_attribute():
    """Test that HasPerUnit has _system_base attribute."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.0,
    )
    assert hasattr(gen, "_system_base")


def test_has_per_units_system_base_can_be_set():
    """Test that _system_base can be set on HasPerUnit."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.0,
    )
    gen._system_base = 150.0
    assert gen._system_base == 150.0


def test_has_per_units_system_base_repr():
    """Test HasPerUnit repr with system base set."""
    set_unit_system(UnitSystem.SYSTEM_BASE)
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.0,
    )
    gen._system_base = 150.0
    repr_str = repr(gen)
    assert "pu (system)" in repr_str
    set_unit_system(UnitSystem.DEVICE_BASE)


def test_mixed_units_conversion():
    """Test conversion with mixed natural and pu inputs."""
    gen = Generator(
        name="Gen3",
        base_power=100.0,
        rated_voltage=13.8,
        rating={"value": 90.0, "unit": "MVA"},  # type: ignore[arg-type]
        voltage=1.05,
    )
    assert gen.rating == pytest.approx(0.9, abs=1e-6)
    assert gen.voltage == 1.05


def test_has_units_caching():
    """Test that unit specs are cached correctly for HasUnits."""
    sensor1 = Sensor(name="S1", temperature=25.0, pressure=101325.0)
    sensor2 = Sensor(name="S2", temperature=30.0, pressure=101000.0)

    specs1 = type(sensor1)._get_unit_specs_map()
    specs2 = type(sensor2)._get_unit_specs_map()

    assert specs1 is specs2


def test_has_per_units_caching():
    """Test that unit specs are cached correctly for HasPerUnit."""
    gen1 = Generator(name="G1", base_power=100.0, rated_voltage=13.8, rating=0.8, voltage=1.0)
    gen2 = Generator(name="G2", base_power=200.0, rated_voltage=20.0, rating=0.9, voltage=1.05)

    specs1 = type(gen1)._get_unit_specs_map()
    specs2 = type(gen2)._get_unit_specs_map()

    assert specs1 is specs2
