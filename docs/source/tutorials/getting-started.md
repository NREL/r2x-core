# Getting Started with R2X Core

This tutorial will guide you through creating your first power system model translator using R2X Core. By the end, you'll understand how to:

- Set up the plugin architecture for your model
- Define configurations with type safety
- Build a parser to read model data
- Create an exporter to write transformed data
- Use the complete translation workflow

## What We'll Build

We'll create a translator for a fictional power system model called "SimpleGrid". This model uses CSV files for buses and generators, and we'll translate it to the standardized infrasys format.

## Prerequisites

Make sure you have R2X Core installed:

```console
pip install r2x-core
```

## Step 1: Project Structure

Create a new directory for your translator:

```console
mkdir simplegrid-translator
cd simplegrid-translator
```

Create the following structure:

```
simplegrid-translator/
├── data/
│   ├── buses.csv
│   └── generators.csv
├── simplegrid/
│   ├── __init__.py
│   ├── config.py
│   ├── parser.py
│   └── exporter.py
└── main.py
```

## Step 2: Sample Data Files

Create sample input files to work with.

**data/buses.csv:**

```csv
bus_id,bus_name,voltage_kv,base_mva
1,North Station,345,100
2,South Station,345,100
3,East Substation,138,50
```

**data/generators.csv:**

```csv
gen_id,gen_name,bus_id,capacity_mw,fuel_type,heat_rate
G1,Coal Plant 1,1,500,coal,9500
G2,Wind Farm 1,2,200,wind,0
G3,Gas Plant 1,3,300,natural_gas,7500
```

## Step 3: Define Configuration

Create `simplegrid/config.py` to define type-safe configuration:

```python
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class SimpleGridConfig(BaseModel):
    """Configuration for SimpleGrid model."""

    input_folder: Path = Field(description="Path to input data folder")
    output_folder: Path = Field(description="Path to output data folder")
    base_year: int = Field(description="Base year for the model", ge=2020, le=2050)
    scenario_name: str = Field(default="base", description="Scenario identifier")

    @field_validator("input_folder", "output_folder")
    @classmethod
    def validate_path_exists(cls, v: Path) -> Path:
        """Ensure paths exist."""
        if not v.exists():
            raise ValueError(f"Path does not exist: {v}")
        return v

    class Config:
        validate_assignment = True
```

## Step 4: Build the Parser

Create `simplegrid/parser.py` to read and parse SimpleGrid data:

```python
from infrasys import System
from infrasys.components import ACBus, ThermalStandard, RenewableDispatch
from r2x_core.parser import BaseParser
from r2x_core.store import DataStore
from r2x_core.datafile import DataFile
from r2x_core.exceptions import ValidationError, ParserError

from .config import SimpleGridConfig


class SimpleGridParser(BaseParser):
    """Parser for SimpleGrid model data."""

    def __init__(self, config: SimpleGridConfig, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)
        self.base_year = config.base_year
        self.scenario = config.scenario_name

    def validate_inputs(self) -> None:
        """Validate that required data files exist."""
        required_files = ["buses", "generators"]
        for file_name in required_files:
            if file_name not in self.data_store.data_files:
                raise ValidationError(
                    f"Required data file '{file_name}' not found in data store"
                )

    def build_system_components(self) -> None:
        """Create power system components from data files."""
        # First, create all buses
        self._build_buses()

        # Then create generators (which reference buses)
        self._build_generators()

    def _build_buses(self) -> None:
        """Create ACBus components from bus data."""
        bus_data = self.read_data_file("buses")

        for row in bus_data.iter_rows(named=True):
            bus = self.create_component(
                ACBus,
                name=row["bus_name"],
                voltage=row["voltage_kv"],
                base_voltage=row["voltage_kv"],
            )
            self.add_component(bus)

    def _build_generators(self) -> None:
        """Create generator components from generator data."""
        gen_data = self.read_data_file("generators")

        for row in gen_data.iter_rows(named=True):
            # Get the corresponding bus
            bus_name = self._get_bus_name(row["bus_id"])
            bus = self.system.get_component(ACBus, bus_name)

            # Create appropriate generator type based on fuel
            if row["fuel_type"] in ["wind", "solar"]:
                gen = self.create_component(
                    RenewableDispatch,
                    name=row["gen_name"],
                    active_power=row["capacity_mw"],
                    rating=row["capacity_mw"],
                    prime_mover_type=row["fuel_type"],
                    bus=bus,
                )
            else:
                gen = self.create_component(
                    ThermalStandard,
                    name=row["gen_name"],
                    active_power=row["capacity_mw"],
                    rating=row["capacity_mw"],
                    prime_mover_type=row["fuel_type"],
                    bus=bus,
                )

            self.add_component(gen)

    def _get_bus_name(self, bus_id: int) -> str:
        """Helper to get bus name from bus_id."""
        bus_data = self.read_data_file("buses")
        for row in bus_data.iter_rows(named=True):
            if row["bus_id"] == bus_id:
                return row["bus_name"]
        raise ParserError(f"Bus with id {bus_id} not found")

    def build_time_series(self) -> None:
        """Build time series data (not implemented for this simple example)."""
        pass
```

## Step 5: Build the Exporter

Create `simplegrid/exporter.py` to export the system:

```python
from pathlib import Path
from infrasys import System
from infrasys.components import ACBus, ThermalStandard, RenewableDispatch
from r2x_core.exporter import BaseExporter
from r2x_core.store import DataStore

from .config import SimpleGridConfig


class SimpleGridExporter(BaseExporter):
    """Exporter for SimpleGrid model data."""

    def __init__(
        self,
        config: SimpleGridConfig,
        system: System,
        data_store: DataStore,
        **kwargs,
    ):
        super().__init__(config, system, data_store, **kwargs)
        self.output_folder = Path(config.output_folder)

    def export(self) -> None:
        """Export system components to CSV files."""
        self.export_buses()
        self.export_generators()

    def export_buses(self) -> None:
        """Export buses to CSV."""
        output_file = self.output_folder / "buses_output.csv"

        buses = self.system.get_components(ACBus)
        bus_data = []
        for i, bus in enumerate(buses, start=1):
            bus_data.append({
                "bus_id": i,
                "bus_name": bus.name,
                "voltage_kv": bus.voltage,
                "base_mva": 100,  # default value
            })

        # Write to CSV using polars
        import polars as pl
        df = pl.DataFrame(bus_data)
        df.write_csv(output_file)

    def export_generators(self) -> None:
        """Export generators to CSV."""
        output_file = self.output_folder / "generators_output.csv"

        # Get all generator types
        thermal_gens = list(self.system.get_components(ThermalStandard))
        renewable_gens = list(self.system.get_components(RenewableDispatch))

        gen_data = []
        gen_id = 1
        for gen in thermal_gens + renewable_gens:
            bus_id = self._get_bus_id(gen.bus.name)
            gen_data.append({
                "gen_id": gen_id,
                "gen_name": gen.name,
                "bus_id": bus_id,
                "capacity_mw": gen.rating,
                "fuel_type": gen.prime_mover_type,
                "heat_rate": 0 if isinstance(gen, RenewableDispatch) else 8000,
            })
            gen_id += 1

        import polars as pl
        df = pl.DataFrame(gen_data)
        df.write_csv(output_file)

    def _get_bus_id(self, bus_name: str) -> int:
        """Helper to get bus_id from bus name."""
        buses = list(self.system.get_components(ACBus))
        for i, bus in enumerate(buses, start=1):
            if bus.name == bus_name:
                return i
        return 0

    def export_time_series(self) -> None:
        """Export time series data (not implemented for this simple example)."""
        pass
```

## Step 6: Register the Plugin

Create `simplegrid/__init__.py` to register your model as a plugin:

```python
from r2x_core import PluginManager

from .config import SimpleGridConfig
from .parser import SimpleGridParser
from .exporter import SimpleGridExporter

# Register the SimpleGrid model plugin
PluginManager.register_model_plugin(
    name="simplegrid",
    config=SimpleGridConfig,
    parser=SimpleGridParser,
    exporter=SimpleGridExporter,
)

__all__ = ["SimpleGridConfig", "SimpleGridParser", "SimpleGridExporter"]
```

## Step 7: Create the Main Script

Create `main.py` to tie everything together:

```python
from pathlib import Path
from r2x_core import PluginManager, DataStore
from r2x_core.datafile import DataFile

# Import to trigger plugin registration
import simplegrid


def main():
    # Define paths
    input_folder = Path("data")
    output_folder = Path("output")
    output_folder.mkdir(exist_ok=True)

    # Create data store with file configurations
    data_store = DataStore(folder=input_folder)

    # Configure data files
    data_store.add_data_file(
        DataFile(
            name="buses",
            fpath="buses.csv",
            description="Bus data for SimpleGrid model",
        )
    )

    data_store.add_data_file(
        DataFile(
            name="generators",
            fpath="generators.csv",
            description="Generator data for SimpleGrid model",
        )
    )

    # Create configuration
    manager = PluginManager()
    config_class = manager.load_config_class("simplegrid")
    config = config_class(
        input_folder=input_folder,
        output_folder=output_folder,
        base_year=2030,
        scenario_name="base_case",
    )

    # Parse the model
    print("Parsing SimpleGrid model...")
    parser = manager.load_parser("simplegrid")
    system = parser(config, data_store).build_system()

    # Print summary
    print(f"\nSystem created with:")
    print(f"  - {len(list(system.get_components()))} total components")
    from infrasys.components import ACBus, ThermalStandard, RenewableDispatch
    print(f"  - {len(list(system.get_components(ACBus)))} buses")
    print(f"  - {len(list(system.get_components(ThermalStandard)))} thermal generators")
    print(f"  - {len(list(system.get_components(RenewableDispatch)))} renewable generators")

    # Export the model
    print("\nExporting system...")
    exporter = manager.load_exporter("simplegrid")
    exporter(config, system, data_store).export()

    print(f"\nExport complete! Check {output_folder} for output files.")


if __name__ == "__main__":
    main()
```

## Step 8: Run the Translator

Execute the translation:

```console
python main.py
```

You should see output like:

```
Parsing SimpleGrid model...

System created with:
  - 6 total components
  - 3 buses
  - 2 thermal generators
  - 1 renewable generators

Exporting system...

Export complete! Check output for output files.
```

Check the `output/` folder for the exported files.

## What's Next?

Now that you've built a basic translator, you can:

1. **Add data transformations** - Use filters and column mappings in your DataFile configurations
2. **Implement time series** - Add the `build_time_series()` and `export_time_series()` methods
3. **Add validation** - Enhance `validate_inputs()` to check data quality and consistency
4. **Create custom file readers** - Support additional file formats beyond CSV
5. **Register system modifiers** - Apply transformations to the entire system after parsing
6. **Package as a library** - Distribute your translator as a Python package using entry points

## Learn More

- [Plugin System Guide](../explanations/plugin-system.md) - Deep dive into the plugin architecture
- [How-To: Register Plugins](../how-tos/plugin-registration.md) - Advanced plugin registration patterns
- [How-To: Create Parsers](../how-tos/parser-basics.md) - Parser development best practices
- [How-To: Create Exporters](../how-tos/exporter-basics.md) - Exporter development best practices
- [API Reference](../references/index.md) - Complete API documentation
