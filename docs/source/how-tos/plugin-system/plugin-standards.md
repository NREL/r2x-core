# Follow Plugin Standards

r2x-core defines standards for plugin structure and configuration.

## Standard Directory Structure

```
my_plugin/
├── __init__.py
├── config.py
├── parser.py
└── config/
    ├── defaults.json
    └── file_mapping.json
```

## Create Configuration Classes

All plugin configurations inherit from `PluginConfig`:

```python
from r2x_core import PluginConfig

class MyModelConfig(PluginConfig):
    """Configuration for MyModel parser."""
    solve_year: int
    weather_year: int
    scenario: str = "reference"
```

## Customize File Names

Override class variables to use different file names:

```python
from r2x_core import PluginConfig

class MyModelConfig(PluginConfig):
    CONFIG_DIR = "resources"                 # default: "config"
    FILE_MAPPING_NAME = "data_files.json"   # default: "file_mapping.json"
    DEFAULTS_FILE_NAME = "constants.json"   # default: "defaults.json"

    solve_year: int
```

## Load Default Constants

Use `load_defaults()` to load model-specific constants from JSON:

```python
from r2x_core import PluginConfig

class ReEDSConfig(PluginConfig):
    solve_year: int
    weather_year: int

defaults = ReEDSConfig.load_defaults()
config = ReEDSConfig(solve_year=2030, weather_year=2012)
excluded_techs = defaults.get("excluded_techs", [])
```

**defaults.json:**

```json
{
  "excluded_techs": ["coal", "oil"],
  "default_capacity_mw": 100.0,
  "regions": ["east", "west", "central"]
}
```

## Create File Mappings

Store file mapping in `config/file_mapping.json`:

```json
{
  "generators": "gen_*.csv",
  "buses": "bus_data.csv",
  "load_profiles": "load_ts_*.parquet"
}
```

## Create DataStore from Config

Use `DataStore.from_plugin_config()` for the cleanest API:

```python
from r2x_core import DataStore, PluginConfig

class MyModelConfig(PluginConfig):
    solve_year: int

config = MyModelConfig(solve_year=2030)
store = DataStore.from_plugin_config(config, folder_path="/data/mymodel")
print(store.list_data())
```
