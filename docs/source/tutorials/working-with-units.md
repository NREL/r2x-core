# Working with Units in Power System Components

Create power system components with proper unit handling. Learn to define unit-aware fields, use different per-unit systems, and handle automatic unit conversions.

## Prerequisites

Install R2X Core:

```console
pip install r2x-core
```

## Understanding Per-Unit Systems

R2X Core stores all per-unit quantities internally in device-base per-unit. Display modes only affect how values appear, not how they're calculated.

## Creating a Component with Units

Define a generator with per-unit fields:

```python
from typing import Annotated
from infrasys import Component
from r2x_core.units import HasPerUnit, Unit

class Generator(HasPerUnit, Component):
    """Generator with per-unit power tracking."""
    base_power: Annotated[float, Unit("MVA")]
    rated_voltage: Annotated[float, Unit("kV")]
    output: Annotated[float, Unit("pu", base="base_power")]

# Create instance
gen = Generator(
    name="Coal Plant 1",
    base_power=500.0,
    rated_voltage=22.0,
    output=0.85  # 85% of rated capacity
)
```

The `output` field stores the value in per-unit normalized to `base_power`.

## Natural Unit Inputs

Provide values in physical units—R2X Core converts automatically:

```python
gen = Generator(
    name="Wind Farm 1",
    base_power=200.0,
    rated_voltage=34.5,
    output={"value": 150.0, "unit": "MVA"}  # Auto-converted to 0.75 pu
)
```

## Display Modes

View the same data in three ways:

```python
from r2x_core.units import UnitSystem, set_unit_system

# Device-base (default): each device normalized to its own rating
set_unit_system(UnitSystem.DEVICE_BASE)
print(gen.output)  # Shows: 0.75 pu

# Natural units: actual physical values
set_unit_system(UnitSystem.NATURAL_UNITS)
print(gen.output)  # Shows: 150 MVA

# System-base: all values normalized to system base
from r2x_core.system import System
system = System(100.0, name="Grid")
system.add_component(gen)
set_unit_system(UnitSystem.SYSTEM_BASE)
print(gen.output)  # Shows: 1.5 pu (system)
```

## Multiple Base Values

Equipment with multiple ratings (like transformers) can reference different bases:

```python
class Transformer(HasPerUnit, Component):
    """Transformer with multiple voltage references."""
    base_power: Annotated[float, Unit("MVA")]
    high_voltage: Annotated[float, Unit("kV")]
    low_voltage: Annotated[float, Unit("kV")]
    impedance: Annotated[float, Unit("pu", base="base_power")]
    tap_position: Annotated[float, Unit("pu", base="high_voltage")]
    load_current: Annotated[float, Unit("pu", base="low_voltage")]

tx = Transformer(
    name="Main TX",
    base_power=100.0,
    high_voltage=138.0,
    low_voltage=13.8,
    impedance=0.10,
    tap_position=1.05,
    load_current={"value": 4.2, "unit": "kA"}
)
```

Each field references its designated base; R2X Core tracks and converts accordingly.

## Complete System Example

```python
# Create system
system = System(100.0, name="DistributionFeeder")

coal_gen = Generator(
    name="Coal Unit",
    base_power=500.0,
    rated_voltage=22.0,
    output={"value": 425.0, "unit": "MVA"}
)

wind_gen = Generator(
    name="Wind Farm",
    base_power=150.0,
    rated_voltage=34.5,
    output={"value": 120.0, "unit": "MVA"}
)

system.add_components(coal_gen, wind_gen)

# View in different modes
set_unit_system(UnitSystem.DEVICE_BASE)
for comp in system.get_components(Generator):
    print(f"{comp.name}: {comp.output}")

set_unit_system(UnitSystem.NATURAL_UNITS)
for comp in system.get_components(Generator):
    print(f"{comp.name}: {comp.output}")

set_unit_system(UnitSystem.SYSTEM_BASE)
for comp in system.get_components(Generator):
    print(f"{comp.name}: {comp.output}")
```

## Next Steps

- Create components with multiple electrical quantities
- Import measurement data using natural unit conversions
- Build parsers with automatic unit handling

## Learn More

- [How-To: Unit Operations](../how-tos/working-with-data/unit-operations.md)
- [API Reference](../references/units.md)
