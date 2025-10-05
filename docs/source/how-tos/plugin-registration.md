# ... register a complete model plugin

```python
from pydantic import BaseModel
from r2x_core import BaseParser, BaseExporter, PluginManager, DataStore, System

class MyModelConfig(BaseModel):
    input_folder: str
    output_folder: str
    weather_year: int = 2012

class MyModelParser(BaseParser):
    def __init__(self, config: MyModelConfig, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)
        self.weather_year = config.weather_year

    def build_system_components(self) -> None:
        generators = self.read_data_file("generators")
        buses = self.read_data_file("buses")

        for row in buses.iter_rows(named=True):
            bus = self.create_component(Bus, row)
            self.add_component(bus)

        for row in generators.iter_rows(named=True):
            gen = self.create_component(Generator, row)
            self.add_component(gen)

    def build_time_series(self) -> None:
        pass

class MyModelExporter(BaseExporter):
    def __init__(self, config: MyModelConfig, system: System, data_store: DataStore, **kwargs):
        super().__init__(config, system, data_store, **kwargs)

    def export(self) -> None:
        gen_file = self.data_store.data_files["generators"]
        self.system.export_components_to_csv(
            file_path=gen_file.file_path,
            filter_func=lambda c: isinstance(c, Generator),
        )

        bus_file = self.data_store.data_files["buses"]
        self.system.export_components_to_csv(
            file_path=bus_file.file_path,
            filter_func=lambda c: isinstance(c, Bus),
        )

    def export_time_series(self) -> None:
        pass

PluginManager.register_model_plugin(
    name="my_model",
    config=MyModelConfig,
    parser=MyModelParser,
    exporter=MyModelExporter,
)
```

# ... register a parser-only plugin

```python
PluginManager.register_model_plugin(
    name="reeds",
    config=ReEDSConfig,
    parser=ReEDSParser,
)
```

# ... register an exporter-only plugin

```python
PluginManager.register_model_plugin(
    name="plexos",
    config=PlexosConfig,
    exporter=PlexosExporter,
)
```

# ... register a system modifier

```python
from r2x_core import PluginManager, System
from loguru import logger

# With explicit name
@PluginManager.register_system_modifier("add_storage")
def add_storage_devices(system: System, capacity_mw: float = 100.0, **kwargs) -> System:
    logger.info(f"Adding {capacity_mw} MW of storage")

    for bus in system.get_components(Bus):
        storage = BatteryStorage(
            name=f"battery_{bus.name}",
            bus=bus,
            active_power=capacity_mw,
        )
        system.add_component(storage)

    return system

# Without explicit name (uses function name)
@PluginManager.register_system_modifier
def scale_generation(system: System, factor: float = 1.0, **kwargs) -> System:
    """Modifier registered as 'scale_generation'."""
    for gen in system.get_components(Generator):
        gen.active_power *= factor
    return system
```

# ... register a system modifier with context

```python
@PluginManager.register_system_modifier("emission_cap")
def add_emission_constraint(system: System, limit_tonnes: float | None = None, **kwargs) -> System:
    parser = kwargs.get("parser")

    if limit_tonnes is None and parser is not None:
        limit_tonnes = parser.data.get("co2_cap", {}).get("value")

    if limit_tonnes is None:
        logger.warning("No emission limit specified")
        return system

    constraint = EmissionConstraint(name="annual_co2_cap", limit=limit_tonnes)
    system.add_component(constraint)

    return system
```

# ... register filter functions

```python
import polars as pl
from r2x_core import PluginManager

# With explicit name
@PluginManager.register_filter("rename_columns")
def rename_columns(data: pl.LazyFrame, mapping: dict[str, str]) -> pl.LazyFrame:
    return data.rename(mapping)

# Without explicit name (uses function name)
@PluginManager.register_filter
def filter_by_year(data: pl.LazyFrame, year: int | list[int], year_column: str = "year") -> pl.LazyFrame:
    """Filter registered as 'filter_by_year'."""
    if isinstance(year, int):
        return data.filter(pl.col(year_column) == year)
    return data.filter(pl.col(year_column).is_in(year))
```

# ... register a polymorphic filter

```python
from typing import Any

@PluginManager.register_filter("select_fields")
def select_fields(data: dict | pl.LazyFrame, fields: list[str]) -> Any:
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in fields}
    elif isinstance(data, pl.LazyFrame):
        return data.select(fields)
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")
```

# ... create an external plugin package

Create package structure:

```
my_model_plugin/
├── pyproject.toml
├── src/
│   └── my_model/
│       ├── __init__.py
│       ├── config.py
│       ├── parser.py
│       ├── exporter.py
│       └── plugins.py
└── tests/
```

Configure entry point in `pyproject.toml`:

```toml
[project]
name = "r2x-my-model"
version = "0.1.0"
dependencies = ["r2x-core>=0.1.0"]

[project.entry-points.r2x_plugin]
my_model = "my_model.plugins:register_plugins"
```

Implement registration in `src/my_model/plugins.py`:

```python
from r2x_core import PluginManager
from .config import MyModelConfig
from .parser import MyModelParser
from .exporter import MyModelExporter
from .modifiers import add_custom_component
from .filters import custom_filter

def register_plugins():
    PluginManager.register_model_plugin(
        name="my_model",
        config=MyModelConfig,
        parser=MyModelParser,
        exporter=MyModelExporter,
    )

    PluginManager.register_system_modifier("my_custom_modifier")(add_custom_component)
    PluginManager.register_filter("my_custom_filter")(custom_filter)
```

# ... test plugin registration

```python
import pytest
from r2x_core import PluginManager, BaseParser

def test_plugin_registered():
    manager = PluginManager()

    assert "my_model" in manager.registered_parsers
    assert "my_model" in manager.registered_exporters
    assert "my_custom_modifier" in manager.system_modifiers
    assert "my_custom_filter" in manager.filter_functions

def test_load_parser():
    manager = PluginManager()
    parser_class = manager.load_parser("my_model")

    assert parser_class is not None
    assert issubclass(parser_class, BaseParser)
```
