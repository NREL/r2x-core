# ... discover registered plugins

```python
from r2x_core import PluginManager

manager = PluginManager()

parsers = manager.registered_parsers
exporters = manager.registered_exporters
modifiers = manager.registered_modifiers

print(f"Available parsers: {list(parsers.keys())}")
print(f"Available exporters: {list(exporters.keys())}")
print(f"Available modifiers: {list(modifiers.keys())}")
```

# ... load and use a parser

```python
from r2x_core import PluginManager, DataStore

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
from r2x_core import DataStore

exporter_class = manager.load_exporter("plexos")

config = PlexosConfig(output_folder="./output/plexos")
data_store = DataStore(folder="./output/plexos")
exporter = exporter_class(config=config, system=system, data_store=data_store)
exporter.export()
```

# ... apply a system modifier

```python
from r2x_core import System

system = System()

modifier = manager.registered_modifiers.get("add_storage")
if modifier:
    modified_system = modifier(system, capacity_mw=200.0, duration_hours=4.0)
```

# ... chain multiple modifiers

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
```

# ... apply a filter to data

```python
import polars as pl

data = pl.scan_csv("generators.csv")
rename_filter = manager.registered_filters.get("rename_columns")

if rename_filter:
    filtered_data = rename_filter(
        data,
        mapping={"gen_name": "name", "gen_type": "technology"}
    )
    result = filtered_data.collect()
```
