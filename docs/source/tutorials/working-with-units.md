# Working with Units in Power System Components

This tutorial guides you through creating power system components with proper unit handling in R2X Core. You'll learn how to define components with per-unit calculations, work with different unit systems, and leverage multiple base values for complex equipment models.

## What You'll Learn

By the end of this tutorial, you'll be able to:

- Create components with unit-aware fields
- Use device-base and system-base per-unit systems
- Display values in different unit modes
- Handle natural unit inputs automatically
- Work with components that have multiple base values

## Prerequisites

Make sure you have R2X Core installed:

```console
pip install r2x-core
```

## Understanding Per-Unit Systems in Power Systems

Power system analysis relies heavily on per-unit normalization to simplify calculations and comparisons across equipment with different ratings. In R2X Core, components can express electrical quantities in three different ways depending on the analysis context.

## Step 1: Creating a Basic Component with Units

Let's start by creating a simple generator component that tracks its power output using per-unit values.

```python
from typing import Annotated
from infrasys import Component
from r2x_core.units import HasPerUnit, Unit

class Generator(HasPerUnit, Component):
    """A simple generator with per-unit power tracking."""

    base_power: Annotated[float, Unit("MVA")]
    rated_voltage: Annotated[float, Unit("kV")]
    output: Annotated[float, Unit("pu", base="base_power")]
```

The `base_power` field uses `Unit("MVA")` to indicate it stores power in megavolt-amperes. The `output` field uses `Unit("pu", base="base_power")` which tells R2X Core that this value is in per-unit with `base_power` as its base quantity.

Create a generator instance:

```python
gen = Generator(
    name="Coal Plant 1",
    base_power=500.0,    # 500 MVA rated capacity
    rated_voltage=22.0,   # 22 kV terminal voltage
    output=0.85          # Operating at 85% of rated capacity
)

print(f"Generator: {gen.name}")
print(f"Base Power: {gen.base_power} MVA")
print(f"Output: {gen.output} pu")
# Output shows: Output: 0.85 pu
```

The component stores `output` internally as 0.85 in per-unit based on the device's own rating.

## Step 2: Using Natural Unit Inputs

R2X Core automatically converts natural units to per-unit for storage. Instead of manually calculating per-unit values, you can provide actual megawatt values:

```python
gen = Generator(
    name="Wind Farm 1",
    base_power=200.0,
    rated_voltage=34.5,
    output={"value": 150.0, "unit": "MVA"}  # Natural unit input
)

print(f"Output: {gen.output} pu")
# Automatically converted: 150 MVA / 200 MVA base = 0.75 pu
```

When you provide a dictionary with `value` and `unit` keys, R2X Core performs the conversion automatically. This feature simplifies data import from external sources that provide measurements in physical units rather than per-unit.

## Step 3: Displaying Values in Different Unit Systems

R2X Core supports three display modes for per-unit quantities, allowing you to view the same data in different ways depending on your analysis needs.

### Device-Base Per-Unit (Default)

The default mode shows values normalized to each device's own rating:

```python
from r2x_core.units import UnitSystem, set_unit_system

# Ensure device-base mode
set_unit_system(UnitSystem.DEVICE_BASE)

gen = Generator(
    name="Gas Turbine 1",
    base_power=300.0,
    rated_voltage=13.8,
    output=0.90
)

print(gen)
# Shows: output='0.9 pu'
```

This mode is intuitive because each device expresses its loading relative to its own nameplate rating.

### Natural Units Mode

Natural units mode displays the actual physical quantities:

```python
set_unit_system(UnitSystem.NATURAL_UNITS)

print(gen)
# Shows: output='270 MVA' (calculated as 0.90 * 300 MVA)
```

This mode is helpful when you need to see absolute values for reporting or validation against measured data.

### System-Base Per-Unit

System-base mode normalizes all quantities to a common system base, essential for power flow analysis and system-wide comparisons:

```python
from r2x_core.system import System

# Create a system with 100 MVA system base
system = System(100.0, name="TransmissionGrid")
system.add_component(gen)

set_unit_system(UnitSystem.SYSTEM_BASE)

print(gen)
# Shows: output='2.7 pu (system)' (calculated as 270 MVA / 100 MVA system base)
```

When components are added to a system, they automatically track the system base power for this conversion. System-base per-unit is crucial for network analysis where all impedances and powers must reference the same base.

## Step 4: Working with Multiple Base Values

Real power system equipment often has multiple ratings. A transformer, for example, has separate voltage bases for its high and low sides:

```python
class Transformer(HasPerUnit, Component):
    """Transformer with high and low voltage sides."""

    base_power: Annotated[float, Unit("MVA")]
    high_voltage: Annotated[float, Unit("kV")]
    low_voltage: Annotated[float, Unit("kV")]

    # Impedance referenced to base_power
    impedance: Annotated[float, Unit("pu", base="base_power")]

    # Tap position referenced to high_voltage
    tap_position: Annotated[float, Unit("pu", base="high_voltage")]

    # Load current referenced to low_voltage
    load_current: Annotated[float, Unit("pu", base="low_voltage")]
```

Create a transformer with multiple references:

```python
tx = Transformer(
    name="Main Transformer",
    base_power=100.0,
    high_voltage=138.0,
    low_voltage=13.8,
    impedance=0.10,
    tap_position=1.05,  # 5% above nominal
    load_current={"value": 4.2, "unit": "kA"}  # Natural units
)
```

Each per-unit field correctly references its designated base. The `impedance` uses `base_power`, `tap_position` uses `high_voltage`, and `load_current` uses `low_voltage`. R2X Core tracks these relationships and performs conversions accordingly:

```python
set_unit_system(UnitSystem.NATURAL_UNITS)

print(f"Impedance: {tx.impedance}")  # Shows as percentage of base power
print(f"Tap: {tx.tap_position}")     # Shows as kV on high side
print(f"Current: {tx.load_current}") # Shows as amperes on low side
```

## Step 5: Building a Complete System

Let's combine everything into a small power system:

```python
from r2x_core.system import System
from r2x_core.units import set_unit_system, UnitSystem

# Create system with 100 MVA base
system = System(100.0, name="DistributionFeeder")

# Add generators
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

# Add transformer
step_up = Transformer(
    name="Step-Up TX",
    base_power=600.0,
    high_voltage=230.0,
    low_voltage=22.0,
    impedance=0.08,
    tap_position=1.0,
    load_current=0.85
)

system.add_components(coal_gen, wind_gen, step_up)

# View in different modes
print("=== Device Base ===")
set_unit_system(UnitSystem.DEVICE_BASE)
for comp in system.get_components(Generator):
    print(f"{comp.name}: output={comp.output}")

print("\n=== Natural Units ===")
set_unit_system(UnitSystem.NATURAL_UNITS)
for comp in system.get_components(Generator):
    print(f"{comp.name}: output={comp.output}")

print("\n=== System Base ===")
set_unit_system(UnitSystem.SYSTEM_BASE)
for comp in system.get_components(Generator):
    print(f"{comp.name}: output={comp.output}")
```

The output demonstrates how the same data appears in each mode:

```text
=== Device Base ===
Coal Unit: output=0.85 pu
Wind Farm: output=0.8 pu

=== Natural Units ===
Coal Unit: output=425 MVA
Wind Farm: output=120 MVA

=== System Base ===
Coal Unit: output=4.25 pu (system)
Wind Farm: output=1.2 pu (system)
```

## Next Steps

Now that you understand unit handling in R2X Core, you can:

- Create complex component models with multiple electrical quantities
- Import data from measurement systems using natural units
- Perform system-wide analysis using common system-base per-unit
- Build parsers that automatically handle unit conversions

```{seealso}
- {doc}`../how-tos/unit-operations` - Additional unit manipulation techniques
- {doc}`../explanations/unit-system` - Deep dive into the unit system design
- {doc}`../references/units` - Complete API reference for units module
```
