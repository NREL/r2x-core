from typing import Annotated

from infrasys import Component

from r2x_core.units import HasPerUnit, Unit, UnitSystem, unit_system


class Demo(HasPerUnit, Component):
    name: str
    base_power: Annotated[float, Unit("MVA")]
    rating: Annotated[float, Unit("pu", base="base_power")]


def test_unit_system_context_manager_restores():
    demo = Demo(name="demo", base_power=100.0, rating=0.8)
    assert "pu" in repr(demo)
    with unit_system(UnitSystem.NATURAL_UNITS):
        s = repr(demo)
        assert "MVA" in s or "100" in s
    assert "pu" in repr(demo)


def test_unit_system_context_manager_switch():
    demo = Demo(name="demo", base_power=100.0, rating=0.8)
    with unit_system(UnitSystem.SYSTEM_BASE):
        s = repr(demo)
        assert "system" in s or "pu" in s
    assert "pu" in repr(demo)
