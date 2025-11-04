# Getting Started with R2X Core

Create your first power system model translator using R2X Core. We'll build a translator for SimpleGrid, a fictional model using CSV files for buses and generators.

## Prerequisites

Install R2X Core:

```console
pip install r2x-core
```

## Project Structure

Create a new directory with this structure:

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

## Sample Data

**data/buses.csv:**

```text
bus_id,bus_name,voltage_kv,base_mva
1,North Station,345,100
2,South Station,345,100
3,East Substation,138,50
```

**data/generators.csv:**

```text
gen_id,gen_name,bus_id,capacity_mw,fuel_type,heat_rate
G1,Coal Plant 1,1,500,coal,9500
G2,Wind Farm 1,2,200,wind,0
G3,Gas Plant 1,3,300,natural_gas,7500
```

## Configuration

Create `simplegrid/config.py`:

```python
from pydantic import BaseModel, Field
from pathlib import Path

class SimpleGridConfig(BaseModel):
    """Configuration for SimpleGrid model."""
    input_folder: Path
    output_folder: Path
    base_year: int = Field(ge=2020, le=2050)
    scenario_name: str = "base"
```

## Parser

Create `simplegrid/parser.py`:

```python
from infrasys.components import ACBus, ThermalStandard, RenewableDispatch
from r2x_core.parser import BaseParser

class SimpleGridParser(BaseParser):
    """Parser for SimpleGrid model data."""

    def validate_inputs(self) -> None:
        """Validate required data files exist."""
        for file_name in ["buses", "generators"]:
            if file_name not in self.data_store.data_files:
                raise ValueError(f"Missing required file: {file_name}")

    def build_system_components(self) -> None:
        """Create power system components from data files."""
        # Create buses
        bus_data = self.read_data_file("buses")
        for row in bus_data.iter_rows(named=True):
            bus = self.create_component(
                ACBus,
                name=row["bus_name"],
                voltage=row["voltage_kv"],
                base_voltage=row["voltage_kv"],
            )
            self.add_component(bus)

        # Create generators
        gen_data = self.read_data_file("generators")
        for row in gen_data.iter_rows(named=True):
            bus = self.system.get_component(
                ACBus, self._get_bus_name(row["bus_id"])
            )
            gen_class = (
                RenewableDispatch
                if row["fuel_type"] in ["wind", "solar"]
                else ThermalStandard
            )
            gen = self.create_component(
                gen_class,
                name=row["gen_name"],
                rating=row["capacity_mw"],
                prime_mover_type=row["fuel_type"],
                bus=bus,
            )
            self.add_component(gen)

    def _get_bus_name(self, bus_id: int) -> str:
        """Get bus name from bus_id."""
        for row in self.read_data_file("buses").iter_rows(named=True):
            if row["bus_id"] == bus_id:
                return row["bus_name"]
        raise ValueError(f"Bus {bus_id} not found")

    def build_time_series(self) -> None:
        """Build time series (not needed for this example)."""
        pass
```

## Exporter

Create `simplegrid/exporter.py`:

```python
from pathlib import Path
from infrasys.components import ACBus, ThermalStandard, RenewableDispatch
from r2x_core.exporter import BaseExporter
import polars as pl

class SimpleGridExporter(BaseExporter):
    """Exporter for SimpleGrid model data."""

    def export(self) -> None:
        """Export system components to CSV files."""
        output_folder = Path(self.config.output_folder)

        # Export buses
        buses = list(self.system.get_components(ACBus))
        bus_data = [
            {
                "bus_id": i,
                "bus_name": bus.name,
                "voltage_kv": bus.voltage,
            }
            for i, bus in enumerate(buses, start=1)
        ]
        pl.DataFrame(bus_data).write_csv(output_folder / "buses_output.csv")

        # Export generators
        gens = list(self.system.get_components(ThermalStandard)) + list(
            self.system.get_components(RenewableDispatch)
        )
        gen_data = [
            {
                "gen_name": gen.name,
                "capacity_mw": gen.rating,
                "fuel_type": gen.prime_mover_type,
            }
            for gen in gens
        ]
        pl.DataFrame(gen_data).write_csv(output_folder / "generators_output.csv")

    def export_time_series(self) -> None:
        """Not needed for this example."""
        pass
```

## Plugin Registration

Create `simplegrid/__init__.py`:

```python
from r2x_core import PluginManager
from .config import SimpleGridConfig
from .parser import SimpleGridParser
from .exporter import SimpleGridExporter

PluginManager.register_model_plugin(
    name="simplegrid",
    config=SimpleGridConfig,
    parser=SimpleGridParser,
    exporter=SimpleGridExporter,
)
```

## Run the Translator

Create `main.py`:

```python
from pathlib import Path
from r2x_core import PluginManager, DataStore
from r2x_core.datafile import DataFile
import simplegrid

def main():
    input_folder = Path("data")
    output_folder = Path("output")
    output_folder.mkdir(exist_ok=True)

    data_store = DataStore(folder_path=input_folder)
    data_store.add_data(DataFile(name="buses", fpath="buses.csv"))
    data_store.add_data(DataFile(name="generators", fpath="generators.csv"))

    manager = PluginManager()
    config = manager.load_config_class("simplegrid")(
        input_folder=input_folder,
        output_folder=output_folder,
        base_year=2030,
    )

    print("Parsing SimpleGrid model...")
    parser = manager.load_parser("simplegrid")
    system = parser(config, data_store).build_system()
    print(f"Created system with {len(list(system.get_components()))} components")

    print("Exporting system...")
    exporter = manager.load_exporter("simplegrid")
    exporter(config, system, data_store).export()
    print(f"Export complete! Check {output_folder}")

if __name__ == "__main__":
    main()
```

Execute:

```console
python main.py
```

## Next Steps

- Add data transformations using DataFile filters and column mappings
- Implement `build_time_series()` for time-dependent data
- Support additional file formats with custom file readers
- Apply system-wide transformations with system modifiers

## Learn More

- [How-To: Create Parsers](../how-tos/parser-basics.md)
- [How-To: Create Exporters](../how-tos/exporter-basics.md)
- [API Reference](../references/index.md)
