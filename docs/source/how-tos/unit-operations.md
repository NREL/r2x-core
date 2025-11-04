# ... create a component with per-unit fields

```python
from typing import Annotated
from infrasys import Component
from r2x_core.units import HasPerUnit, Unit

class Generator(HasPerUnit, Component):
    """Generator with unit-aware fields."""

    base_power: Annotated[float, Unit("MVA")]
    rated_voltage: Annotated[float, Unit("kV")]
    active_power: Annotated[float, Unit("pu", base="base_power")]
    terminal_voltage: Annotated[float, Unit("pu", base="rated_voltage")]

gen = Generator(
    name="Gen1",
    base_power=100.0,
    rated_voltage=13.8,
    active_power=0.95,
    terminal_voltage=1.05
)
```

# ... input values in natural units

```python
gen = Generator(
    name="Gen2",
    base_power=250.0,
    rated_voltage=22.0,
    active_power={"value": 200.0, "unit": "MVA"},
    terminal_voltage={"value": 22.5, "unit": "kV"}
)

print(gen.active_power)  # 0.8 pu (auto-converted)
```

# ... switch between display modes

```python
from r2x_core.units import UnitSystem, set_unit_system

gen = Generator(
    name="Gen3",
    base_power=150.0,
    rated_voltage=15.0,
    active_power=0.90,
    terminal_voltage=1.02
)

# Device-base per-unit
set_unit_system(UnitSystem.DEVICE_BASE)
print(gen.active_power)  # 0.9 pu

# Natural units
set_unit_system(UnitSystem.NATURAL_UNITS)
print(gen.active_power)  # 135 MVA

# System-base
from r2x_core.system import System
system = System(100.0, name="Grid")
system.add_component(gen)
set_unit_system(UnitSystem.SYSTEM_BASE)
print(gen.active_power)  # 1.35 pu
```

# ... use context manager for temporary mode

```python
from r2x_core.units import unit_system, UnitSystem

gen = Generator(
    name="Gen4",
    base_power=200.0,
    rated_voltage=18.0,
    active_power=0.75,
    terminal_voltage=1.0
)

with unit_system(UnitSystem.NATURAL_UNITS):
    print(f"In context: {gen.active_power}")  # 150 MVA

print(f"After context: {gen.active_power}")  # 0.75 pu
```

# ... add components to system

```python
system = System(100.0, name="MyGrid")

gen = Generator(
    name="Plant1",
    base_power=425.0,
    rated_voltage=20.0,
    active_power=0.8,
    terminal_voltage=1.0
)

system.add_component(gen)
set_unit_system(UnitSystem.SYSTEM_BASE)
print(gen.active_power)  # 3.4 pu (system base)
```
