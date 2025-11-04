# Using Parser and Exporter Plugins

This guide covers how to use parser and exporter plugins to translate power system models.

## Basic Parser Usage

Import your parser class and configuration, then build a system:

```python
from pathlib import Path
from r2x_core import DataStore
from r2x_core.datafile import DataFile
from my_model.parser import MyModelParser
from my_model.config import MyModelConfig

# Prepare configuration
config = MyModelConfig(
    input_folder=Path("./data/my_model"),
    output_folder=Path("./output"),
    weather_year=2020,
)

# Set up data store with file mappings
data_store = DataStore(folder_path=config.input_folder)
data_store.add_data(DataFile(name="buses", fpath="buses.csv"))
data_store.add_data(DataFile(name="generators", fpath="generators.csv"))

# Create and run parser
parser = MyModelParser(config, data_store=data_store)
system = parser.build_system()

print(f"Loaded system with {len(list(system.get_components()))} components")
```

## Basic Exporter Usage

Use an exporter to save a system to a specific format:

```python
from my_model.exporter import MyModelExporter

# Create exporter
exporter = MyModelExporter(config, system=system)

# Export the system
result = exporter.export()

if result.is_ok():
    print(f"Export successful to {config.output_folder}")
else:
    error = result.unwrap_err()
    print(f"Export failed: {error}")
```

## Error Handling

Both parsers and exporters return `Result` types for error handling:

```python
from r2x_core import ParserError, ExporterError

# Parser errors
try:
    parser = MyModelParser(config, data_store=data_store)
    system = parser.build_system()
except ParserError as e:
    print(f"Parsing failed: {e}")

# Exporter errors
result = exporter.export()
if result.is_err():
    error = result.unwrap_err()
    print(f"Export error: {error}")
```

## Working with Different File Formats

R2X Core supports multiple file formats through the DataFile configuration:

```python
from r2x_core.datafile import DataFile, TabularProcessing, TabularTransformations

# Configure data files with transformations
data_store = DataStore(folder_path="./data")

# CSV with transformations
data_store.add_data(DataFile(
    name="generators",
    fpath="generators.csv",
    lowercase=True,  # Lowercase column names
    drop_columns=["obsolete_field"],  # Remove columns
    column_mapping={"gen_id": "id"},  # Rename columns
    schema={"capacity_mw": "Float64"},  # Cast types
))

# HDF5 file
data_store.add_data(DataFile(
    name="timeseries",
    fpath="timeseries.h5",
))

# Read processed data
gen_data = data_store.read_data("generators")
ts_data = data_store.read_data("timeseries")
```

## Chaining Multiple Parsers

You can parse data from one model and export to another format:

```python
from reedsparser import REEDSParser, REEDSConfig
from plexosexporter import PLEXOSExporter, PLEXOSConfig

# Parse from REEDS
reeds_config = REEDSConfig(input_folder="./data/reeds")
reeds_parser = REEDSParser(reeds_config)
system = reeds_parser.build_system()

# Export to PLEXOS format
plexos_config = PLEXOSConfig(output_folder="./output/plexos")
plexos_exporter = PLEXOSExporter(plexos_config, system=system)
result = plexos_exporter.export()
```

## Configuration Management

Store configurations in JSON for reusability:

```json
{
  "input_folder": "./data/my_model",
  "output_folder": "./output",
  "weather_year": 2020,
  "scenario": "baseline"
}
```

Load from JSON:

```python
import json
from pathlib import Path

# Load configuration from JSON
with open("config.json") as f:
    config_dict = json.load(f)

config = MyModelConfig(**config_dict)
```

## Handling Large Data Files

For large datasets, use Polars lazy evaluation:

```python
from r2x_core import DataStore

# DataReader automatically handles large files
data_store = DataStore(folder_path="./data")
data_store.add_data(DataFile(name="large_dataset", fpath="large.csv"))

# Data is read lazily (not loaded into memory until needed)
data = data_store.read_data("large_dataset")

# Operations are lazy until collected
result = data.filter(...).select(...).collect()
```

## Next Steps

- [Creating Custom Parsers](parser-basics.md)
- [Creating Custom Exporters](exporter-basics.md)
- [Data Transformations](data-reading.md)
- [Plugin Registration](plugin-registration.md)
