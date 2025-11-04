# ... register a complete model plugin

```python
from r2x_core import BaseParser, BaseExporter, PluginManager, PluginConfig, DataStore, System

class MyModelConfig(PluginConfig):
    input_folder: str
    output_folder: str
    weather_year: int = 2012

class MyModelParser(BaseParser):
    def __init__(self, config: MyModelConfig, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)
        self.weather_year = config.weather_year

    def build_system_components(self) -> None:
        buses = self.read_data_file("buses")
        generators = self.read_data_file("generators")

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

    def export_time_series(self) -> None:
        pass

PluginManager.register_model_plugin(
    name="my_model",
    config=MyModelConfig,
    parser=MyModelParser,
    exporter=MyModelExporter,
)
```

# ... register a system modifier

```python
from r2x_core import PluginManager, System

@PluginManager.register_system_modifier("add_storage")
def add_storage_devices(system: System, capacity_mw: float = 100.0, **kwargs) -> System:
    """Add battery storage to each bus."""
    for bus in system.get_components(Bus):
        storage = BatteryStorage(
            name=f"battery_{bus.name}",
            bus=bus,
            active_power=capacity_mw,
        )
        system.add_component(storage)

    return system
```

# ... register a filter function

```python
@PluginManager.register_filter("rename_columns")
def rename_columns_filter(data, mapping: dict[str, str]) -> Any:
    """Rename data columns."""
    return data.rename(mapping)
```
