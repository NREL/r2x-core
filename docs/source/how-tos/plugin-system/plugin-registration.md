# Plugin Registration

Plugins in R2X Core are created by implementing `BaseParser` and `BaseExporter` classes, and providing a `PluginConfig` for configuration.

## Creating a Model Plugin

A complete model plugin consists of three components: a configuration class, a parser, and an exporter.

### Step 1: Define Configuration

Create a configuration class extending `PluginConfig`:

```python
from r2x_core import PluginConfig
from pathlib import Path

class MyModelConfig(PluginConfig):
    """Configuration for MyModel plugin."""
    input_folder: Path
    output_folder: Path
    weather_year: int = 2012
    scenario: str = "base"
```

### Step 2: Implement Parser

Extend `BaseParser` and implement the required abstract methods:

```python
from r2x_core import BaseParser, Ok, Err, ParserError
from r2x_core.result import Result
from infrasys.components import ACBus, ThermalStandard

class MyModelParser(BaseParser):
    """Parser for MyModel data."""

    def build_system_components(self) -> Result[None, ParserError]:
        """Create power system components from data files."""
        try:
            # Read and process data
            bus_data = self.store.read_data("buses")
            if bus_data is None:
                return Err(ParserError("Bus data not found"))

            # Create buses
            for row in bus_data.iter_rows(named=True):
                bus = self.create_component(
                    ACBus,
                    name=row["bus_name"],
                    voltage=row["voltage_kv"],
                )
                self.add_component(bus)

            return Ok(None)
        except Exception as e:
            return Err(ParserError(f"Component building failed: {e}"))

    def build_time_series(self) -> Result[None, ParserError]:
        """Attach time series data to components."""
        # Add time series if needed
        return Ok(None)
```

### Step 3: Implement Exporter

Extend `BaseExporter` and implement the export logic:

```python
from r2x_core import BaseExporter, Ok, Err, ExporterError
from r2x_core.result import Result
from infrasys.components import ACBus
import polars as pl

class MyModelExporter(BaseExporter):
    """Exporter for MyModel format."""

    def prepare_export(self) -> Result[None, ExporterError]:
        """Export system to files."""
        try:
            # Extract components
            buses = list(self.system.get_components(ACBus))
            bus_data = [
                {"name": bus.name, "voltage_kv": bus.voltage}
                for bus in buses
            ]

            # Write to CSV
            output_file = Path(self.config.output_folder) / "buses.csv"
            pl.DataFrame(bus_data).write_csv(output_file)

            return Ok(None)
        except Exception as e:
            return Err(ExporterError(f"Export failed: {e}"))
```

## Using Your Plugin

Once implemented, use your plugin directly:

```python
from pathlib import Path
from r2x_core import DataStore
from r2x_core.datafile import DataFile

# Create configuration
config = MyModelConfig(
    input_folder=Path("data"),
    output_folder=Path("output"),
    weather_year=2020,
)

# Set up data store
data_store = DataStore(path=config.input_folder)
data_store.add_data(DataFile(name="buses", fpath="buses.csv"))

# Parse
parser = MyModelParser(config, data_store=data_store)
system = parser.build_system()

# Export
exporter = MyModelExporter(config, system=system)
result = exporter.export()

if result.is_ok():
    print("Export successful")
else:
    print(f"Export failed: {result.unwrap_err()}")
```

## Entry Point Discovery

To make your plugin discoverable by other packages, register it as an entry point in `pyproject.toml`:

```toml
[project.entry-points.r2x_plugins]
my_model = "my_package.plugins:parser_plugin"
my_model_exporter = "my_package.plugins:exporter_plugin"
```

Then expose a manifest in `my_package/plugins.py`:

```python
from r2x_core import PluginManifest, PluginSpec

manifest = PluginManifest(package="my_package")

manifest.add(
    PluginSpec.parser(
        name="my_model.parser",
        entry="my_package.parser:MyModelParser",
        description="Builds a System from model inputs.",
        config="my_package.config:MyModelConfig",
    )
)
```

The CLI (and other downstream tools) read this manifest to determine how to construct your parser/exporter/upgrader without having to import your module eagerly.

## Best Practices

- Keep configuration separate from implementation logic
- Handle errors gracefully and return `Err(...)` with descriptive messages
- Use `self.store.read_data()` to access data files managed by DataStore
- Validate inputs in `validate_inputs()` hook if overridden
- Test with various data inputs before distributing

## See Also

- [Parser Basics](parser-basics.md) - Detailed parser implementation guide
- [Exporter Basics](exporter-basics.md) - Detailed exporter implementation guide
- [Plugin Standards](plugin-standards.md) - Plugin development standards
