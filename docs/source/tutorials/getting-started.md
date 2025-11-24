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
from pydantic import Field
from pathlib import Path
from r2x_core import PluginConfig

class SimpleGridConfig(PluginConfig):
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
from rust_ok import Err, Ok, Result
from r2x_core import BaseParser, ParserError

class SimpleGridParser(BaseParser):
    """Parser for SimpleGrid model data."""

    def build_system_components(self) -> Result[None, ParserError]:
        """Create power system components from data files."""
        try:
            # Read bus data
            bus_data = self.store.read_data("buses")
            if bus_data is None:
                return Err(ParserError("Bus data file not found"))

            # Create buses
            for row in bus_data.iter_rows(named=True):
                bus = self.create_component(
                    ACBus,
                    name=row["bus_name"],
                    voltage=row["voltage_kv"],
                    base_voltage=row["voltage_kv"],
                )
                self.add_component(bus)

            # Read generator data
            gen_data = self.store.read_data("generators")
            if gen_data is None:
                return Err(ParserError("Generator data file not found"))

            # Create generators
            for row in gen_data.iter_rows(named=True):
                bus = self.system.get_component(
                    ACBus, row["bus_name"]
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

            return Ok(None)
        except Exception as e:
            return Err(ParserError(f"Failed to build components: {e}"))

    def build_time_series(self) -> Result[None, ParserError]:
        """Build time series (not needed for this example)."""
        return Ok(None)
```

## Exporter

Create `simplegrid/exporter.py`:

```python
from pathlib import Path
from infrasys.components import ACBus, ThermalStandard, RenewableDispatch
from rust_ok import Err, Ok, Result
from r2x_core import BaseExporter, ExporterError
import polars as pl

class SimpleGridExporter(BaseExporter):
    """Exporter for SimpleGrid model data."""

    def prepare_export(self) -> Result[None, ExporterError]:
        """Export system components to CSV files."""
        try:
            output_folder = Path(self.config.output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)

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

            return Ok(None)
        except Exception as e:
            return Err(ExporterError(f"Export failed: {e}"))
```

## Run the Translator

Create `main.py`:

```python
from pathlib import Path
from r2x_core import DataStore
from r2x_core.datafile import DataFile
from simplegrid.config import SimpleGridConfig
from simplegrid.parser import SimpleGridParser
from simplegrid.exporter import SimpleGridExporter

def main():
    input_folder = Path("data")
    output_folder = Path("output")
    output_folder.mkdir(exist_ok=True)

    # Configure the data store
    data_store = DataStore(path=input_folder)
    data_store.add_data(DataFile(name="buses", fpath="buses.csv"))
    data_store.add_data(DataFile(name="generators", fpath="generators.csv"))

    # Create configuration
    config = SimpleGridConfig(
        input_folder=input_folder,
        output_folder=output_folder,
        base_year=2030,
    )

    # Parse the model
    print("Parsing SimpleGrid model...")
    parser = SimpleGridParser(config, data_store=data_store)
    system = parser.build_system()
    print(f"Created system with {len(list(system.get_components()))} components")

    # Export the system
    print("Exporting system...")
    exporter = SimpleGridExporter(config, system=system)
    result = exporter.export()

    if result.is_ok():
        print(f"Export complete! Check {output_folder}")
    else:
        print(f"Export failed: {result.unwrap_err()}")

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

- [How-To: Create Parsers](../how-tos/system-operations/parser-basics.md)
- [How-To: Create Exporters](../how-tos/system-operations/exporter-basics.md)
- [API Reference](../references/index.md)
