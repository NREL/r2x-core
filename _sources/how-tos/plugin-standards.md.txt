# ... follow plugin standards

r2x-core defines standards for plugin structure and configuration to ensure consistency across model plugins. This guide covers the standard directory structure, file naming conventions, and methods that plugins should implement.

# ... use standard directory structure

Plugins should follow this standard structure:

```
my_plugin/
├── __init__.py
├── parser.py           # Parser implementation
├── exporter.py         # Exporter implementation (optional)
├── config.py           # Configuration classes
└── config/
    ├── defaults.json       # Default values and mappings
    └── file_mapping.json   # File path mappings
```

# ... create configuration classes

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

# ... customize file and directory names

`PluginConfig` provides class variables to customize where configuration files are located:

```python
from r2x_core import PluginConfig

class MyModelConfig(PluginConfig):
    """Configuration with custom file locations."""

    # Customize directory name (default: "config")
    CONFIG_DIR = "resources"

    # Customize file mapping filename (default: "file_mapping.json")
    FILE_MAPPING_NAME = "data_files.json"

    # Customize defaults filename (default: "defaults.json")
    DEFAULTS_FILE_NAME = "constants.json"

    solve_year: int
    weather_year: int
```

**Directory structure with custom names:**

```
my_plugin/
├── __init__.py
├── config.py
└── resources/              # Custom CONFIG_DIR
    ├── constants.json      # Custom DEFAULTS_FILE_NAME
    └── data_files.json     # Custom FILE_MAPPING_NAME
```

**Available class variables:**

- `CONFIG_DIR`: Directory name for configuration files (default: `"config"`)
- `FILE_MAPPING_NAME`: Filename for file mappings (default: `"file_mapping.json"`)
- `DEFAULTS_FILE_NAME`: Filename for default constants (default: `"defaults.json"`)

# ... load default constants

Use `load_defaults()` to load model-specific constants from JSON:

```python
from pathlib import Path
from r2x_core import PluginConfig

class ReEDSConfig(PluginConfig):
    """ReEDS model configuration."""

    solve_year: int
    weather_year: int

# Auto-discovers config/defaults.json next to the config module
# (customizable via DEFAULTS_FILE_NAME class variable)
defaults = ReEDSConfig.load_defaults()
config = ReEDSConfig(
    solve_year=2030,
    weather_year=2012,
)
# Use defaults dict in your parser/exporter logic
excluded_techs = defaults.get("excluded_techs", [])
```

**defaults.json example:**

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
defaults = ReEDSConfig.load_defaults("/path/to/custom_defaults.json")
```

**Custom filename:**

```python
class MyModelConfig(PluginConfig):
    """Config with custom defaults filename."""
    DEFAULTS_FILE_NAME = "my_constants.json"
    solve_year: int

# Will look for config/my_constants.json
defaults = MyModelConfig.load_defaults()
```

# ... create file mappings

Plugins should store file mapping in `config/file_mapping.json`:

```json
{
  "generators": "gen_*.csv",
  "buses": "bus_data.csv",
  "load_profiles": "load_ts_*.parquet",
  "transmission": "tx_lines.h5"
}
```

# ... get file mapping path

Load and use file mappings from `config/file_mapping.json`:

```python
from r2x_core import PluginConfig
import json

class MyModelConfig(PluginConfig):
    solve_year: int
    weather_year: int

# Get the mapping file path
mapping_path = MyModelConfig().file_mapping_path
print(f"Mappings at: {mapping_path}")

# Load mappings if file exists
if mapping_path.exists():
    with open(mapping_path) as f:
        mappings = json.load(f)
```

# ... use custom mapping filename

Override `FILE_MAPPING_NAME` to use a different filename:

```python
from r2x_core import PluginConfig

class CustomConfig(PluginConfig):
    FILE_MAPPING_NAME = "data_mappings.json"  # Instead of file_mapping.json
    solve_year: int

# Will look for config/data_mappings.json
path = CustomConfig().file_mapping_path
```

# ... create DataStore from config

Use `DataStore.from_plugin_config()` for the cleanest API:

```python
from r2x_core import DataStore, PluginConfig

class MyModelConfig(PluginConfig):
    solve_year: int
    weather_year: int

# Create config
config = MyModelConfig(solve_year=2030, weather_year=2012)

# Create DataStore directly from config
store = DataStore.from_plugin_config(config, folder_path="/data/mymodel")

# The store automatically discovers and loads config/file_mapping.json
print(store.list_data())
```

# ... get mapping path from PluginManager

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

# ... generate CLI schemas

PluginConfig instances can be integrated with CLI tools. You can access field information via the Pydantic model_fields:

```python
from r2x_core.plugin_config import PluginConfig

class MyModelConfig(PluginConfig):
    solve_year: int
    weather_year: int
    scenario: str = "base"

# Access model fields for CLI generation
config = MyModelConfig(solve_year=2030, weather_year=2012)
for field_name, field_info in config.model_fields.items():
    print(f"Field: {field_name}, Type: {field_info.annotation}")
```

# ... build CLI tools from schema

Use Pydantic's built-in model schema capabilities with argparse:

```python
import argparse
from my_plugin.config import MyModelConfig

# Create config instance
config = MyModelConfig(solve_year=2030, weather_year=2012)

# Build parser using Pydantic field information
parser = argparse.ArgumentParser(description="MyModel Configuration")

for field_name, field_info in config.model_fields.items():
    if field_name == "config_path":
        continue  # Skip inherited fields

    # Convert snake_case to --kebab-case
    flag = f"--{field_name.replace('_', '-')}"

    # Extract type and default
    field_type = field_info.annotation
    default = field_info.default if field_info.default is not None else None
    description = field_info.description or ""

    # Map types to Python types
    type_map = {int: int, str: str, bool: bool, float: float}
    py_type = type_map.get(field_type, str)

    if field_type == bool:
        parser.add_argument(flag, action="store_true", help=description)
    else:
        parser.add_argument(
            flag,
            type=py_type,
            required=field_info.is_required(),
            help=description,
            default=default
        )

# Parse arguments
args = parser.parse_args()

# Create config from parsed args
config = MyModelConfig(
    solve_year=args.solve_year,
    weather_year=args.weather_year,
    scenario=args.scenario,
)
```

# ... understand CLI flag naming

Field names are automatically converted to CLI-friendly flags by converting snake_case to kebab-case:

| Field Name             | CLI Flag                 |
| ---------------------- | ------------------------ |
| `solve_year`           | `--solve-year`           |
| `weather_year`         | `--weather-year`         |
| `model_version_string` | `--model-version-string` |
| `output_dir`           | `--output-dir`           |

# ... see complete plugin example

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

**my_plugin/config/defaults.json:**

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

# Load configuration and defaults
defaults = MyModelConfig.load_defaults()
config = MyModelConfig(
    solve_year=2030,
    weather_year=2012,
)

# Create data store from mapping file
mapping_path = config.file_mapping_path
store = DataStore.from_json(mapping_path, folder="/data/mymodel")

# Build system
parser = MyModelParser(config, store)
system = parser.build_system()
```

# ... follow best practices

## Always use standard directory structure

```
plugin/
├── config.py
├── parser.py
└── config/
    ├── defaults.json
    └── file_mapping.json
```

## Load defaults in configuration

```python
# Good - loads defaults automatically and uses in parser logic
defaults = MyConfig.load_defaults()
config = MyConfig(year=2030)
# Use defaults dict in your parser/exporter
excluded = defaults.get("excluded_techs", [])

# Not recommended - hardcoding defaults
defaults = {"tech": ["solar", "wind"]}
```

## Use file mapping discovery

```python
# Good - uses property access (cleanest)
config = MyConfig(year=2030)
mapping_path = config.file_mapping_path
store = DataStore.from_json(mapping_path, folder=data_folder)

# Also good - uses property access
defaults = MyConfig.load_defaults()
config = MyConfig(year=2030)
defaults_data = config.load_defaults()

# Not recommended - hardcoding paths
store = DataStore.from_json("/hardcoded/path/mappings.json", folder=data_folder)
```

## Generate CLI schema for tools

```python
# Good - use Pydantic field information
from my_plugin.config import MyConfig
config = MyConfig(year=2030)
for field_name, field_info in config.model_fields.items():
    # Build CLI args from field metadata

# Not recommended - manually defining CLI args
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--solve-year", type=int, required=True)
parser.add_argument("--weather-year", type=int, required=True)
# ... manually list all arguments
```

## Document configuration fields

```python
from pydantic import Field

class MyConfig(PluginConfig):
    """Model configuration."""

    solve_year: int = Field(..., description="Year to solve the model for")
    scenario: str = Field("reference", description="Scenario name")
```

# ... see also

- [Plugin Registration](plugin-registration.md) - How to register plugins
- [Parser Basics](parser-basics.md) - Creating custom parsers
- [Configuration Guide](configuration.md) - Configuration management
