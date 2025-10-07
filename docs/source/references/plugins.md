# Plugin System

For complete API documentation of plugin classes, see {doc}`api`.

## Quick Reference

- {py:class}`~r2x_core.PluginManager` - Plugin registration and management
- {py:class}`~r2x_core.PluginComponent` - Plugin component container
- {py:class}`~r2x_core.SystemModifier` - System modifier type
- {py:class}`~r2x_core.FilterFunction` - Filter function type

## Usage Examples

### Registering a Model Plugin

```python
from r2x_core import PluginManager, BaseParser, BaseExporter, PluginConfig

class MyModelConfig(PluginConfig):
    folder: str
    year: int

class MyParser(BaseParser):
    def build_system_components(self):
        # Build components
        pass

    def build_time_series(self):
        # Add time series
        pass

class MyExporter(BaseExporter):
    def export(self):
        # Export logic
        pass

# Register the complete plugin
PluginManager.register_model_plugin(
    name="my_model",
    config=MyModelConfig,
    parser=MyParser,
    exporter=MyExporter,
)
```

### Registering System Modifiers

```python
from r2x_core import System, PluginManager

@PluginManager.register_system_modifier("add_storage")
def add_storage(system: System, capacity_mw: float = 100.0, **kwargs) -> System:
    """Add storage components to the system."""
    # Add storage logic
    return system

@PluginManager.register_system_modifier()
def scale_renewables(system: System, factor: float = 1.5, **kwargs) -> System:
    """Scale renewable capacity by a factor."""
    # Scaling logic
    return system
```

### Registering Filter Functions

```python
import polars as pl
from r2x_core import PluginManager

@PluginManager.register_filter("rename_columns")
def rename_columns(data: pl.LazyFrame, mapping: dict[str, str]) -> pl.LazyFrame:
    """Rename columns in a dataframe."""
    return data.rename(mapping)

@PluginManager.register_filter("filter_by_year")
def filter_by_year(data: pl.LazyFrame, year: int) -> pl.LazyFrame:
    """Filter data by year."""
    return data.filter(pl.col("year") == year)
```

### Using Registered Plugins

```python
# Access the singleton
manager = PluginManager()

# Load parser and exporter classes
parser_class = manager.load_parser("my_model")
exporter_class = manager.load_exporter("my_model")

# Get file mapping path
mapping_path = manager.get_file_mapping_path("my_model")

# Access modifiers and filters
modifier = manager.registered_modifiers["add_storage"]
filter_func = manager.registered_filters["rename_columns"]

# List available plugins
print(manager.registered_models)
print(manager.registered_modifiers.keys())
print(manager.registered_filters.keys())
```

### Entry Point Discovery

Register plugins in external packages via `pyproject.toml`:

```toml
[project.entry-points.r2x_plugin]
my_model = "my_package.plugins:my_plugin_component"
```

Then in your package:

```python
# my_package/plugins.py
from r2x_core import PluginComponent
from .parser import MyParser
from .exporter import MyExporter
from .config import MyConfig

my_plugin_component = PluginComponent(
    name="my_model",
    parser=MyParser,
    exporter=MyExporter,
    config=MyConfig,
)
```

Plugins are automatically discovered when PluginManager is first instantiated:

```python
from r2x_core import PluginManager

# Entry points are loaded automatically
manager = PluginManager()
parser = manager.load_parser("my_model")  # Discovered from entry point
```

## Design Patterns

### Singleton Pattern

PluginManager uses a singleton pattern to ensure a single source of truth:

```python
manager1 = PluginManager()
manager2 = PluginManager()
assert manager1 is manager2  # Same instance
```

### Flexible Modifier Signatures

System modifiers accept **kwargs for flexible context passing:

```python
@PluginManager.register_system_modifier()
def my_modifier(
    system: System,
    param1: int,
    param2: str = "default",
    **kwargs  # Can receive additional context
) -> System:
    # Access optional context
    config = kwargs.get("config")
    data_store = kwargs.get("data_store")
    return system
```

## See Also

- {doc}`../how-tos/plugin-registration` - Detailed plugin registration guide
- {doc}`../how-tos/plugin-standards` - Plugin development standards
- {doc}`parser` - BaseParser reference
- {doc}`exporter` - BaseExporter reference
