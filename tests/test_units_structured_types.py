"""Tests for structured types with unit conversion."""

from typing import Annotated

from infrasys import Component
from pydantic import BaseModel

from r2x_core.units import HasUnits, Unit


class UpDown(BaseModel):
    up: float
    down: float


class MinMax(BaseModel):
    min: float
    max: float


def test_structured_type_with_unit_conversion():
    class Generator(HasUnits, Component):
        base_power: Annotated[float, Unit("MVA")]
        ramp_limits: Annotated[UpDown, Unit("MW/min", base="base_power")]

    gen = Generator(
        name="Gen1",
        base_power=100.0,
        ramp_limits=UpDown(up=10.0, down=8.0),
    )

    assert gen.ramp_limits.up == 0.1
    assert gen.ramp_limits.down == 0.08


def test_structured_type_without_base():
    class Bus(HasUnits, Component):
        voltage_limits: Annotated[MinMax, Unit("kV")]

    bus = Bus(
        name="Bus1",
        voltage_limits=MinMax(min=132.0, max=138.0),
    )

    assert bus.voltage_limits.min == 132.0
    assert bus.voltage_limits.max == 138.0


def test_structured_type_optional():
    class Generator(HasUnits, Component):
        base_power: Annotated[float, Unit("MVA")]
        limits: Annotated[MinMax | None, Unit("MW", base="base_power")] = None

    gen1 = Generator(name="Gen1", base_power=100.0)
    assert gen1.limits is None

    gen2 = Generator(
        name="Gen2",
        base_power=100.0,
        limits=MinMax(min=20.0, max=80.0),
    )
    assert gen2.limits.min == 0.2
    assert gen2.limits.max == 0.8


def test_structured_type_serialization():
    class Battery(HasUnits, Component):
        base_power: Annotated[float, Unit("MVA")]
        power_limits: Annotated[MinMax, Unit("MW", base="base_power")]

    battery = Battery(
        name="Batt1",
        base_power=50.0,
        power_limits=MinMax(min=-40.0, max=40.0),
    )

    serialized = battery.model_dump()

    assert isinstance(serialized["power_limits"], dict)
    assert serialized["power_limits"]["min"] == -0.8
    assert serialized["power_limits"]["max"] == 0.8

    deserialized = Battery.model_validate(serialized)
    assert isinstance(deserialized, Battery)


def test_same_structured_type_different_units():
    class Component1(HasUnits, Component):
        base_power: Annotated[float, Unit("MVA")]
        power_limits: Annotated[MinMax, Unit("MW", base="base_power")]

    class Component2(HasUnits, Component):
        voltage_limits: Annotated[MinMax, Unit("kV")]

    comp1 = Component1(
        name="C1",
        base_power=100.0,
        power_limits=MinMax(min=20.0, max=80.0),
    )

    comp2 = Component2(
        name="C2",
        voltage_limits=MinMax(min=132.0, max=138.0),
    )

    assert comp1.power_limits.min == 0.2
    assert comp2.voltage_limits.min == 132.0


def test_nested_float_only():
    class ComplexLimits(BaseModel):
        value: float
        label: str
        enabled: bool

    class Device(HasUnits, Component):
        base_power: Annotated[float, Unit("MVA")]
        limits: Annotated[ComplexLimits, Unit("MW", base="base_power")]

    device = Device(
        name="Dev1",
        base_power=100.0,
        limits=ComplexLimits(value=50.0, label="test", enabled=True),
    )

    assert device.limits.value == 0.5
    assert device.limits.label == "test"
    assert device.limits.enabled is True
