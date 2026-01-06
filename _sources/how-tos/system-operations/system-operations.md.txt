# Get All Components as Records

```python
from infrasys import Component
from r2x_core.system import System

system = System(name="MySystem")
system.add_components(
    Component(name="comp1"),
    Component(name="comp2"),
    Component(name="comp3"),
)

all_records = system.components_to_records()
print(f"Total components: {len(all_records)}")
```

# Filter Components By Type

```python
from infrasys import Component
from r2x_core.system import System

class Generator(Component):
    """Generator component."""
    pass

class Bus(Component):
    """Bus component."""
    pass

system = System(name="MySystem")
system.add_components(
    Generator(name="gen1"),
    Generator(name="gen2"),
    Bus(name="bus1"),
)

gen_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Generator)
)
bus_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Bus)
)
```

# Select Specific Fields

```python
from infrasys import Component
from pydantic import Field
from r2x_core.system import System

class Bus(Component):
    """Bus component."""
    voltage: float = Field(default=0.0, description="Voltage in kV")
    base_voltage: float = Field(default=0.0, description="Base voltage in kV")

system = System(name="MySystem")
system.add_components(
    Bus(name="bus1", voltage=230.0, base_voltage=230.0),
    Bus(name="bus2", voltage=115.0, base_voltage=115.0),
)

bus_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Bus),
    fields=["name", "voltage", "base_voltage"]
)
```

# Rename Fields With Key Mapping

```python
from infrasys import Component
from pydantic import Field
from r2x_core.system import System

class Generator(Component):
    """Generator component."""
    max_active_power: float = Field(default=0.0, description="Maximum active power in MW")
    min_active_power: float = Field(default=0.0, description="Minimum active power in MW")

system = System(name="MySystem")
system.add_components(
    Generator(name="gen1", max_active_power=500.0, min_active_power=100.0)
)

gen_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Generator),
    fields=["name", "max_active_power", "min_active_power"],
    key_mapping={
        "max_active_power": "PMax_MW",
        "min_active_power": "PMin_MW"
    }
)
```

# Export Components To CSV

```python
from infrasys import Component
from pydantic import Field
from r2x_core.system import System

class Generator(Component):
    """Generator component."""
    max_active_power: float = Field(default=0.0, description="Maximum active power in MW")
    bus: str = Field(default="", description="Connected bus name")

class Bus(Component):
    """Bus component."""
    voltage: float = Field(default=0.0, description="Voltage in kV")

system = System(name="MySystem")
system.add_components(
    Generator(name="gen1", max_active_power=500.0, bus="bus1"),
    Bus(name="bus1", voltage=230.0),
)

system.export_components_to_csv("all_components.csv")

system.export_components_to_csv(
    "generators.csv",
    filter_func=lambda c: isinstance(c, Generator)
)

system.export_components_to_csv(
    "generators_export.csv",
    filter_func=lambda c: isinstance(c, Generator),
    fields=["name", "max_active_power", "bus"],
    key_mapping={"max_active_power": "capacity_mw"}
)
```
