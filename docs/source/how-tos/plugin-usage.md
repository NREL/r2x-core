# ... discover registered plugins

```python
from r2x_core import PluginManager

manager = PluginManager()

parsers = manager.registered_parsers
exporters = manager.registered_exporters
modifiers = manager.registered_modifiers
filters = manager.registered_filters

print(f"Available parsers: {list(parsers.keys())}")
print(f"Available exporters: {list(exporters.keys())}")
print(f"Available modifiers: {list(modifiers.keys())}")
print(f"Available filters: {list(filters.keys())}")
```

# ... load and use a parser

```python
from r2x_core import PluginManager, DataStore
from my_app.config import SwitchConfig

manager = PluginManager()
parser_class = manager.load_parser("switch")

config = SwitchConfig(input_folder="./data/switch")
data_store = DataStore.from_json("switch_mappings.json", folder="./data/switch")
parser = parser_class(config=config, data_store=data_store)
system = parser.build_system()

print(f"Loaded {len(system.components)} components")
```

# ... load and use an exporter

```python
from r2x_core import DataStore, DataFile

exporter_class = manager.load_exporter("plexos")

config = PlexosConfig(output_folder="./output/plexos")
data_store = DataStore(
    data_files={
        "generators": DataFile(name="generators", file_path="generators.csv"),
        "buses": DataFile(name="buses", file_path="buses.csv"),
    },
    folder="./output/plexos"
)
exporter = exporter_class(config=config, system=system, data_store=data_store)
exporter.export()
```

# ... apply a system modifier

```python
from r2x_core import System
from loguru import logger

system = System()

modifier = manager.registered_modifiers.get("add_storage")
if modifier:
    modified_system = modifier(system, capacity_mw=200.0, duration_hours=4.0)
    logger.info("Storage added to system")
```

# ... apply multiple modifiers in sequence

```python
pipeline = [
    ("emission_cap", {"limit_tonnes": 1_000_000}),
    ("add_storage", {"capacity_mw": 150.0}),
    ("renewable_target", {"target_pct": 80.0}),
]

modified_system = system
for modifier_name, params in pipeline:
    modifier_func = manager.registered_modifiers.get(modifier_name)
    if modifier_func:
        modified_system = modifier_func(modified_system, **params)
        logger.info(f"Applied: {modifier_name}")
    else:
        logger.warning(f"Not found: {modifier_name}")
```

# ... apply modifiers with context

```python
from my_app.config import AppConfig
from r2x_core import DataStore

config = AppConfig(scenario="high_renewable")
data_store = DataStore.from_json("mappings.json", folder="./data")
parser = MyParser(config=config, data_store=data_store)
system = parser.build_system()

modifier = manager.registered_modifiers.get("scenario_adjustments")
if modifier:
    modified_system = modifier(system, config=config, parser=parser)
```

# ... apply a filter to data

```python
import polars as pl

data = pl.scan_csv("generators.csv")
rename_filter = manager.registered_filters.get("rename_columns")

if rename_filter:
    filtered_data = rename_filter(
        data,
        mapping={"gen_name": "name", "gen_type": "technology", "gen_capacity": "capacity_mw"}
    )
    result = filtered_data.collect()
```

# ... chain multiple filters

```python
year_filter = manager.registered_filters.get("filter_by_year")
tech_filter = manager.registered_filters.get("filter_by_technology")
rename_filter = manager.registered_filters.get("rename_columns")

data = pl.scan_csv("generators.csv")

if year_filter and tech_filter and rename_filter:
    data = year_filter(data, year=2030)
    data = tech_filter(data, technologies=["solar", "wind"])
    data = rename_filter(data, mapping={"gen_name": "name"})
    result = data.collect()
```

# ... use filters in parser

```python
from r2x_core import BaseParser, DataStore

class MyParser(BaseParser):
    def __init__(self, config, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)

    def build_system_components(self) -> None:
        manager = PluginManager()
        year_filter = manager.registered_filters.get("filter_by_year")

        generators = self.read_data_file(
            name="generators",
            filters=[(year_filter, {"year": 2030})] if year_filter else None,
        )

        for row in generators.iter_rows(named=True):
            gen = self.create_component(Generator, row)
            self.add_component(gen)

    def build_time_series(self) -> None:
        pass
```

# ... discover plugins from entry points

```python
from importlib.metadata import entry_points

discovered = entry_points(group="r2x_plugin")

print(f"Found {len(discovered)} plugin packages:")
for ep in discovered:
    print(f"  - {ep.name} from {ep.value}")

manager = PluginManager()
manager._load_entry_point_plugins()

print(f"Total parsers: {len(manager.registered_parsers)}")
print(f"Total exporters: {len(manager.registered_exporters)}")
print(f"Total modifiers: {len(manager.registered_modifiers)}")
print(f"Total filters: {len(manager.registered_filters)}")
```

# ... build a translation application

```python
from pathlib import Path
from loguru import logger
from r2x_core import PluginManager

def translate(
    source_model: str,
    target_model: str,
    input_folder: Path,
    output_folder: Path,
    modifiers: list[tuple[str, dict]] | None = None,
):
    manager = PluginManager()

    parser_class = manager.load_parser(source_model)
    if not parser_class:
        raise ValueError(f"Parser not found: {source_model}")

    exporter_class = manager.load_exporter(target_model)
    if not exporter_class:
        raise ValueError(f"Exporter not found: {target_model}")

    parser_config = AppConfig(input_folder=input_folder)
    input_store = DataStore.from_json(f"{source_model}_mappings.json", folder=input_folder)
    parser = parser_class(config=parser_config, data_store=input_store)

    logger.info(f"Parsing {source_model} from {input_folder}")
    system = parser.build_system()
    logger.info(f"Loaded {len(system.components)} components")

    if modifiers:
        for modifier_name, params in modifiers:
            modifier_func = manager.registered_modifiers.get(modifier_name)
            if modifier_func:
                logger.info(f"Applying: {modifier_name}")
                system = modifier_func(system, config=parser_config, parser=parser, **params)

    exporter_config = AppConfig(output_folder=output_folder)
    output_store = DataStore.from_json(f"{target_model}_mappings.json", folder=output_folder)
    exporter = exporter_class(config=exporter_config, system=system, data_store=output_store)

    logger.info(f"Exporting to {target_model} in {output_folder}")
    exporter.export()
    logger.info("Translation complete")

translate(
    source_model="switch",
    target_model="plexos",
    input_folder=Path("./data/switch"),
    output_folder=Path("./output/plexos"),
    modifiers=[
        ("emission_cap", {"limit_tonnes": 500_000}),
        ("add_storage", {"capacity_mw": 100.0}),
    ],
)
```

# ... handle missing plugins gracefully

```python
def safe_load_plugin(plugin_name: str, plugin_type: str = "parser"):
    manager = PluginManager()

    if plugin_type == "parser":
        plugin_class = manager.load_parser(plugin_name)
        available = manager.registered_parsers
    elif plugin_type == "exporter":
        plugin_class = manager.load_exporter(plugin_name)
        available = manager.registered_exporters
    else:
        raise ValueError(f"Unknown plugin type: {plugin_type}")

    if plugin_class is None:
        logger.error(f"{plugin_type.title()} '{plugin_name}' not found")
        logger.info(f"Available: {list(available.keys())}")
        return None

    return plugin_class

parser_class = safe_load_plugin("my_model", "parser")
if parser_class:
    data_store = DataStore.from_json("mappings.json", folder="./data")
    parser = parser_class(config=config, data_store=data_store)
    system = parser.build_system()
```

# ... validate translation path

```python
def validate_translation_path(source: str, target: str) -> bool:
    manager = PluginManager()

    if source not in manager.registered_parsers:
        logger.error(f"Source not available: {source}")
        logger.info(f"Available: {list(manager.registered_parsers.keys())}")
        return False

    if target not in manager.registered_exporters:
        logger.error(f"Target not available: {target}")
        logger.info(f"Available: {list(manager.registered_exporters.keys())}")
        return False

    logger.info(f"Translation path valid: {source} → {target}")
    return True

if validate_translation_path("switch", "plexos"):
    translate(...)
```
