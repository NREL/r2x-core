# ... follow plugin standards

## Overview

r2x-core defines standards for plugin structure and configuration to ensure consistency across model plugins. This guide covers the standard directory structure, file naming conventions, and methods that plugins should implement.

## Directory Structure

Plugins should follow this standard structure:

```
my_plugin/
├── __init__.py
├── parser.py           # Parser implementation
├── exporter.py         # Exporter implementation (optional)
├── config.py           # Configuration classes
└── config/
    ├── constants.json      # Default values and mappings
    └── file_mapping.json   # File path mappings
```

## Configuration Standards

### PluginConfig Base Class

All plugin configurations should inherit from `PluginConfig`:

```python
from r2x_core import PluginConfig

class MyModelConfig(PluginConfig):
    """Configuration for MyModel parser."""

    solve_year: int
    weather_year: int
    scenario: str = "reference"
    output_dir: str = "./output"
```

### Loading Default Constants

Use `load_defaults()` to load model-specific constants from JSON:

```python
from pathlib import Path
from r2x_core import PluginConfig

class ReEDSConfig(PluginConfig):
    """ReEDS model configuration."""

    solve_year: int
    weather_year: int

# Auto-discovers config/constants.json next to the config module
defaults = ReEDSConfig.load_defaults()
config = ReEDSConfig(
    solve_year=2030,
    weather_year=2012,
    defaults=defaults
)
```

**constants.json example:**

```json
{
  "excluded_techs": ["coal", "oil"],
  "default_capacity_mw": 100.0,
  "regions": ["east", "west", "central"],
  "tech_mappings": {
    "solar": "pv",
    "wind": "onshore_wind"
  }
}
```

**Custom path:**

```python
# Load from custom location
defaults = ReEDSConfig.load_defaults("/path/to/custom_constants.json")
```

## File Mapping Standards

### Standard Location

Plugins should store file mapping in `config/file_mapping.json`:

```json
{
  "generators": "gen_*.csv",
  "buses": "bus_data.csv",
  "load_profiles": "load_ts_*.parquet",
  "transmission": "tx_lines.h5"
}
```

### Getting File Mapping Path

Use `get_file_mapping_path()` to get the path to file mappings:

```python
from r2x_core import BaseParser

class MyModelParser(BaseParser):
    def build_system_components(self):
        pass

    def build_time_series(self):
        pass

# Get the mapping file path
mapping_path = MyModelParser.get_file_mapping_path()
print(f"Mappings at: {mapping_path}")

# Load mappings if file exists
if mapping_path.exists():
    import json
    with open(mapping_path) as f:
        mappings = json.load(f)
```

### Custom Mapping Filename

Override `FILE_MAPPING_NAME` to use a different filename:

```python
class CustomParser(BaseParser):
    FILE_MAPPING_NAME = "data_mappings.json"  # Instead of file_mapping.json

    def build_system_components(self):
        pass

    def build_time_series(self):
        pass

# Will look for config/data_mappings.json
path = CustomParser.get_file_mapping_path()
```

### Using PluginManager

Get mapping path by plugin name without importing the parser:

```python
from r2x_core import PluginManager

manager = PluginManager()
mapping_path = manager.get_file_mapping_path("reeds")

if mapping_path and mapping_path.exists():
    import json
    with open(mapping_path) as f:
        mappings = json.load(f)
        print(f"Found {len(mappings)} file mappings")
```

## CLI Schema Generation

### Dynamic CLI Arguments

Use `get_cli_schema()` to generate CLI-friendly schemas from configuration classes:

```python
from r2x_core.plugin_config import PluginConfig

class MyModelConfig(PluginConfig):
    solve_year: int
    weather_year: int
    scenario: str = "base"

# Get CLI schema
schema = MyModelConfig.get_cli_schema()

### Building CLI Tools

Use the schema to build argument parsers dynamically:

```python
import argparse
from my_plugin.config import MyModelConfig

# Get schema
schema = MyModelConfig.get_cli_schema()

# Build parser
parser = argparse.ArgumentParser(description=schema["description"])

for field_name, field_info in schema["properties"].items():
    # Skip inherited fields you don't want exposed
    if field_name == "defaults":
        continue

    flag = field_info["cli_flag"]
    required = field_info["required"]
    help_text = field_info.get("description", "")
    field_type = field_info.get("type")

    # Map JSON schema types to Python types
    type_map = {"integer": int, "string": str, "boolean": bool, "number": float}
    py_type = type_map.get(field_type, str)

    if field_type == "boolean":
        parser.add_argument(flag, action="store_true", help=help_text)
    else:
        parser.add_argument(
            flag,
            type=py_type,
            required=required,
            help=help_text,
            default=field_info.get("default")
        )

# Parse arguments
args = parser.parse_args()

# Create config from parsed args
config = MyModelConfig(
    solve_year=args.solve_year,
    weather_year=args.weather_year,
    scenario=args.scenario,
    verbose=args.verbose
)
```

### CLI Flag Naming Convention

Field names are automatically converted to CLI-friendly flags:

| Field Name             | CLI Flag                 |
| ---------------------- | ------------------------ |
| `solve_year`           | `--solve-year`           |
| `weather_year`         | `--weather-year`         |
| `model_version_string` | `--model-version-string` |
| `output_dir`           | `--output-dir`           |

## Complete Plugin Example

Here's a complete plugin following all standards:

**my_plugin/config.py:**

```python
from r2x_core import PluginConfig

class MyModelConfig(PluginConfig):
    """Configuration for MyModel."""

    solve_year: int
    weather_year: int
    scenario: str = "reference"
    output_folder: str = "./output"
```

**my_plugin/parser.py:**

```python
from r2x_core import BaseParser, DataStore
from .config import MyModelConfig

class MyModelParser(BaseParser):
    """Parser for MyModel format."""

    def __init__(self, config: MyModelConfig, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)
        self.solve_year = config.solve_year
        self.weather_year = config.weather_year

    def build_system_components(self):
        # Load defaults
        defaults = self.config.defaults
        excluded_techs = defaults.get("excluded_techs", [])

        # Read data files
        generators = self.read_data_file("generators")

        for row in generators.iter_rows(named=True):
            if row["tech"] in excluded_techs:
                continue

            gen = self.create_component(Generator, row)
            self.add_component(gen)

    def build_time_series(self):
        pass
```

**my_plugin/config/constants.json:**

```json
{
  "excluded_techs": ["coal", "oil"],
  "default_capacity": 100.0,
  "tech_mappings": {
    "solar": "pv",
    "wind": "onshore_wind"
  }
}
```

**my_plugin/config/file_mapping.json:**

```json
{
  "generators": "generators_*.csv",
  "buses": "buses.csv",
  "lines": "transmission.h5"
}
```

**Usage:**

```python
from r2x_core import DataStore
from my_plugin.config import MyModelConfig
from my_plugin.parser import MyModelParser

# Load configuration with defaults
defaults = MyModelConfig.load_defaults()
config = MyModelConfig(
    solve_year=2030,
    weather_year=2012,
    defaults=defaults
)

# Get file mapping path
mapping_path = MyModelParser.get_file_mapping_path()
print(f"File mappings: {mapping_path}")

# Create data store
store = DataStore.from_json(mapping_path, folder="/data/mymodel")

# Build system
parser = MyModelParser(config, store)
system = parser.build_system()
```

## Best Practices

### 1. Always Use Standard Directory Structure

```
plugin/
├── config.py
├── parser.py
└── config/
    ├── constants.json
    └── file_mapping.json
```

### 2. Load Defaults in Configuration

```python
# Good - loads defaults automatically
defaults = MyConfig.load_defaults()
config = MyConfig(year=2030, defaults=defaults)

# Not recommended - hardcoding defaults
config = MyConfig(year=2030, defaults={"tech": ["solar", "wind"]})
```

### 3. Use File Mapping Discovery

```python
# Good - uses standard discovery
mapping_path = MyParser.get_file_mapping_path()
store = DataStore.from_json(mapping_path, folder=data_folder)

# Not recommended - hardcoding paths
store = DataStore.from_json("/hardcoded/path/mappings.json", folder=data_folder)
```

### 4. Generate CLI Schema for Tools

```python
# Good - dynamic schema generation
schema = MyConfig.get_cli_schema()
# Build CLI tools from schema

# Not recommended - manually defining CLI args
parser.add_argument("--solve-year", type=int, required=True)
parser.add_argument("--weather-year", type=int, required=True)
# ... manually list all arguments
```

### 5. Document Configuration Fields

```python
from pydantic import Field

class MyConfig(PluginConfig):
    """Model configuration."""

    solve_year: int = Field(..., description="Year to solve the model for")
    scenario: str = Field("reference", description="Scenario name")
```

## See Also

- [Plugin Registration](plugin-registration.md) - How to register plugins
- [Parser Basics](parser-basics.md) - Creating custom parsers
- [Configuration Guide](configuration.md) - Configuration management
