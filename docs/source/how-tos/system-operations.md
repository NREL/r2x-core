# ... get all components as records

```python
from infrasys import Component
from r2x_core.system import System

# Create a system with components
system = System(name="MySystem")
system.add_components(
    Component(name="comp1"),
    Component(name="comp2"),
    Component(name="comp3"),
)

# Get all components as records (list of dictionaries)
all_records = system.components_to_records()
print(f"Total components: {len(all_records)}")
```

# ... filter components by type

```python
from infrasys import Component
from r2x_core.system import System

# Define component subclasses
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

# Filter only generators
gen_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Generator)
)

# Filter only buses
bus_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Bus)
)

print(f"Generators: {len(gen_records)}")
print(f"Buses: {len(bus_records)}")
```

# ... filter components by attributes

```python
from infrasys import Component
from pydantic import Field
from r2x_core.system import System

# Define generator with attributes
class Generator(Component):
    """Generator component."""
    max_active_power: float = Field(default=0.0, description="Maximum active power in MW")
    fuel_type: str = Field(default="unknown", description="Fuel type")

class Bus(Component):
    """Bus component."""
    voltage: float = Field(default=0.0, description="Voltage in kV")

system = System(name="MySystem")
system.add_components(
    Generator(name="large_gen", max_active_power=500.0, fuel_type="gas"),
    Generator(name="small_gen", max_active_power=50.0, fuel_type="solar"),
    Bus(name="bus_hv", voltage=230.0),
    Bus(name="bus_lv", voltage=69.0),
)

# Filter large generators (power > 100 MW)
large_gen_records = system.components_to_records(
    filter_func=lambda c: (
        isinstance(c, Generator) and c.max_active_power > 100
    )
)

# Filter high voltage buses
hv_bus_records = system.components_to_records(
    filter_func=lambda c: (
        isinstance(c, Bus) and c.voltage > 100
    )
)

# Filter renewable generators
renewable_records = system.components_to_records(
    filter_func=lambda c: (
        isinstance(c, Generator) and c.fuel_type in ["solar", "wind"]
    )
)

print(f"Large generators: {len(large_gen_records)}")
print(f"High voltage buses: {len(hv_bus_records)}")
print(f"Renewable generators: {len(renewable_records)}")
```

# ... select specific fields

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

# Get only specific fields from buses
bus_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Bus),
    fields=["name", "voltage", "base_voltage"]
)

print(bus_records)
# Output: [{"name": "bus1", "voltage": 230.0, "base_voltage": 230.0}, ...]
```

# ... rename fields with key mapping

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

# Rename fields to match target format
gen_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Generator),
    fields=["name", "max_active_power", "min_active_power"],
    key_mapping={
        "max_active_power": "PMax_MW",
        "min_active_power": "PMin_MW"
    }
)

print(gen_records)
# Output: [{"name": "gen1", "PMax_MW": 500.0, "PMin_MW": 100.0}]
```

# ... combine filtering, field selection, and renaming

```python
from infrasys import Component
from pydantic import Field
from r2x_core.system import System

class Generator(Component):
    """Generator component."""
    max_active_power: float = Field(default=0.0, description="Maximum active power in MW")
    min_active_power: float = Field(default=0.0, description="Minimum active power in MW")
    bus: str = Field(default="", description="Connected bus name")

system = System(name="MySystem")
system.add_components(
    Generator(name="large_gen_1", max_active_power=500.0, min_active_power=100.0, bus="bus1"),
    Generator(name="large_gen_2", max_active_power=300.0, min_active_power=50.0, bus="bus2"),
    Generator(name="small_gen_1", max_active_power=25.0, min_active_power=5.0, bus="bus3"),
)

# Get large generators (>50 MW) with renamed fields for export
export_records = system.components_to_records(
    # Filter: only generators with capacity > 50 MW
    filter_func=lambda c: (
        isinstance(c, Generator) and c.max_active_power > 50
    ),
    # Select: only fields needed for export
    fields=["name", "max_active_power", "min_active_power", "bus"],
    # Rename: match target model's column names
    key_mapping={
        "max_active_power": "capacity_mw",
        "min_active_power": "min_output_mw",
        "bus": "bus_id"
    }
)

print(export_records)
# Output: [{"name": "large_gen_1", "capacity_mw": 500.0, "min_output_mw": 100.0, "bus_id": "bus1"}, ...]
```

# ... use records for data analysis

```python
from infrasys import Component
from pydantic import Field
from r2x_core.system import System
import polars as pl

class Generator(Component):
    """Generator component."""
    max_active_power: float = Field(default=0.0, description="Maximum active power in MW")
    fuel_type: str = Field(default="unknown", description="Fuel type")

system = System(name="MySystem")
system.add_components(
    Generator(name="gen1", max_active_power=500.0, fuel_type="gas"),
    Generator(name="gen2", max_active_power=300.0, fuel_type="gas"),
    Generator(name="gen3", max_active_power=100.0, fuel_type="solar"),
    Generator(name="gen4", max_active_power=150.0, fuel_type="wind"),
)

# Get all generators as records
gen_records = system.components_to_records(
    filter_func=lambda c: isinstance(c, Generator)
)

# Convert to Polars DataFrame for analysis
gen_df = pl.DataFrame(gen_records)

# Perform analysis
total_capacity = gen_df["max_active_power"].sum()
avg_capacity = gen_df["max_active_power"].mean()
capacity_by_type = gen_df.group_by("fuel_type").agg(
    pl.col("max_active_power").sum().alias("total_capacity")
)

print(f"Total capacity: {total_capacity} MW")
print(f"Average capacity: {avg_capacity} MW")
print(capacity_by_type)
```

# ... export components to CSV

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

# Export all components to CSV
system.export_components_to_csv("all_components.csv")

# Export only generators
system.export_components_to_csv(
    "generators.csv",
    filter_func=lambda c: isinstance(c, Generator)
)

# Export with field selection and renaming
system.export_components_to_csv(
    "generators_export.csv",
    filter_func=lambda c: isinstance(c, Generator),
    fields=["name", "max_active_power", "bus"],
    key_mapping={"max_active_power": "capacity_mw"}
)
```

# ... count components by type

```python
from infrasys import Component
from r2x_core.system import System

class Generator(Component):
    """Generator component."""
    pass

class Bus(Component):
    """Bus component."""
    pass

class Branch(Component):
    """Branch component."""
    pass

system = System(name="MySystem")
system.add_components(
    Generator(name="gen1"),
    Generator(name="gen2"),
    Bus(name="bus1"),
    Bus(name="bus2"),
    Bus(name="bus3"),
    Branch(name="branch1"),
)

# Count all component types
component_types = {}
for record in system.components_to_records():
    comp_type = record.get("__class__", "Unknown")
    component_types[comp_type] = component_types.get(comp_type, 0) + 1

for comp_type, count in component_types.items():
    print(f"{comp_type}: {count}")
```
