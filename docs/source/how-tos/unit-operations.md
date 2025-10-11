# Unit Operations

This guide shows practical techniques for working with units in power system components.

## ... create a component with per-unit fields

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

## ... input values in natural units

```python
# Instead of calculating per-unit manually, provide natural units
gen = Generator(
    name="Gen2",
    base_power=250.0,
    rated_voltage=22.0,
    active_power={"value": 200.0, "unit": "MVA"},
    terminal_voltage={"value": 22.5, "unit": "kV"}
)

# Values are automatically converted to per-unit
print(gen.active_power)  # 0.8 pu
print(gen.terminal_voltage)  # 1.023 pu (approximately)
```

## ... switch between display modes

```python
from r2x_core.units import UnitSystem, set_unit_system

gen = Generator(
    name="Gen3",
    base_power=150.0,
    rated_voltage=15.0,
    active_power=0.90,
    terminal_voltage=1.02
)

# Device-base per-unit (default)
set_unit_system(UnitSystem.DEVICE_BASE)
print(gen.active_power)  # 0.9 pu

# Natural units
set_unit_system(UnitSystem.NATURAL_UNITS)
print(gen.active_power)  # 135 MVA

# System-base (requires system)
from r2x_core.system import System
system = System(100.0, name="Grid")
system.add_component(gen)

set_unit_system(UnitSystem.SYSTEM_BASE)
print(gen.active_power)  # 1.35 pu (system)
```

## ... use context manager for temporary display mode

```python
from r2x_core.units import unit_system, UnitSystem

gen = Generator(
    name="Gen4",
    base_power=200.0,
    rated_voltage=18.0,
    active_power=0.75,
    terminal_voltage=1.0
)

# Default mode
print(f"Default: {gen.active_power}")  # 0.75 pu

# Temporarily change mode
with unit_system(UnitSystem.NATURAL_UNITS):
    print(f"In context: {gen.active_power}")  # 150 MVA

# Reverts to original mode
print(f"After context: {gen.active_power}")  # 0.75 pu
```

## ... create components with multiple base references

```python
class Transformer(HasPerUnit, Component):
    """Transformer with multiple voltage bases."""

    base_power: Annotated[float, Unit("MVA")]
    high_voltage: Annotated[float, Unit("kV")]
    low_voltage: Annotated[float, Unit("kV")]

    impedance: Annotated[float, Unit("pu", base="base_power")]
    hv_tap: Annotated[float, Unit("pu", base="high_voltage")]
    lv_current: Annotated[float, Unit("pu", base="low_voltage")]

tx = Transformer(
    name="TX1",
    base_power=100.0,
    high_voltage=138.0,
    low_voltage=13.8,
    impedance=0.10,
    hv_tap=1.05,
    lv_current={"value": 4.18, "unit": "kA"}
)
```

## ... work with components without system base

```python
from r2x_core.units import HasUnits

class Bus(HasUnits, Component):
    """Bus with units but no system-base tracking."""

    voltage: Annotated[float, Unit("kV")]
    angle: Annotated[float, Unit("deg")]
    load: Annotated[float, Unit("MW")]

bus = Bus(
    name="Bus1",
    voltage=138.0,
    angle=5.2,
    load={"value": 50.0, "unit": "MW"}
)

# HasUnits provides unit annotations but not system-base tracking
# Useful for non-electrical quantities or fixed-unit fields
```

## ... serialize and deserialize unit-aware components

```python
# Serialization preserves internal per-unit values
data = gen.model_dump()
print(data)  # {'name': 'Gen3', 'active_power': 0.9, ...}

# Deserialize from dict
gen_copy = Generator.model_validate(data)

# JSON serialization
json_str = gen.model_dump_json()

# Deserialize from JSON
gen_from_json = Generator.model_validate_json(json_str)
```

## ... add unit-aware components to a system

```python
from r2x_core.system import System

# Create system with 200 MVA base
system = System(200.0, name="TransmissionSystem")

# Create generators
gen1 = Generator(
    name="Plant1",
    base_power=500.0,
    rated_voltage=22.0,
    active_power=0.85,
    terminal_voltage=1.03
)

gen2 = Generator(
    name="Plant2",
    base_power=300.0,
    rated_voltage=18.0,
    active_power=0.90,
    terminal_voltage=1.01
)

# Add components - system base is automatically set
system.add_components(gen1, gen2)

# View in system-base mode
set_unit_system(UnitSystem.SYSTEM_BASE)
for gen in system.get_components(Generator):
    print(f"{gen.name}: {gen.active_power}")
# Plant1: 2.125 pu (system)  # 425 MVA / 200 MVA base
# Plant2: 1.35 pu (system)   # 270 MVA / 200 MVA base
```

## ... create systems with different base powers

```python
# System with 100 MVA base (common for distribution)
dist_system = System(100.0, name="Distribution")

# System with 100 MVA base using keyword
sub_system = System(system_base_power=500.0, name="Subtransmission")

# System with position and name
trans_system = System(1000.0, name="Transmission")

# Default 100 MVA base
default_system = System(name="DefaultBase")
```

## ... handle unit conversion errors gracefully

```python
from pydantic import ValidationError

try:
    gen = Generator(
        name="BadGen",
        base_power=100.0,
        rated_voltage=13.8,
        active_power={"value": 150.0, "unit": "InvalidUnit"}
    )
except ValidationError as e:
    print(f"Validation error: {e}")
    # Handle invalid unit specification
```

## ... mix unit-aware and regular fields

```python
class HybridComponent(HasPerUnit, Component):
    """Component with both unit-aware and regular fields."""

    # Unit-aware fields
    base_power: Annotated[float, Unit("MVA")]
    output: Annotated[float, Unit("pu", base="base_power")]

    # Regular fields without units
    efficiency: float  # Dimensionless ratio
    fuel_type: str     # String identifier
    commissioning_year: int

hybrid = HybridComponent(
    name="SolarFarm",
    base_power=50.0,
    output=0.65,
    efficiency=0.18,
    fuel_type="solar",
    commissioning_year=2024
)
```

## ... validate unit compatibility

```python
# R2X Core validates unit conversions automatically
try:
    gen = Generator(
        name="Gen5",
        base_power=100.0,
        rated_voltage=13.8,
        # Attempting to use length units for power
        active_power={"value": 100.0, "unit": "meter"}
    )
except ValidationError:
    print("Unit type mismatch detected")
```

## ... access raw per-unit values

```python
gen = Generator(
    name="Gen6",
    base_power=100.0,
    rated_voltage=13.8,
    active_power={"value": 75.0, "unit": "MVA"},
    terminal_voltage=1.02
)

# Internal storage is always in per-unit
print(gen.active_power)  # 0.75 (regardless of display mode)

# Model dump shows internal values
data = gen.model_dump()
print(data['active_power'])  # 0.75
```
