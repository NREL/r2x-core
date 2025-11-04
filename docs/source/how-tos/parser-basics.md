# ... create a basic parser

```python
from r2x_core.parser import BaseParser
from r2x_core.plugin_config import PluginConfig
from r2x_core.store import DataStore

class MyModelConfig(PluginConfig):
    """Configuration for MyModel parser."""
    model_year: int
    scenario_name: str

class MyModelParser(BaseParser):
    """Parser for MyModel data."""

    def __init__(self, config: MyModelConfig, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)

    def validate_inputs(self) -> None:
        """Validate configuration."""
        if self.model_year < 2020:
            raise ValueError("Model year must be >= 2020")

    def build_system_components(self) -> None:
        """Create system components."""
        bus_data = self.read_data_file("buses")
        for row in bus_data.iter_rows(named=True):
            bus = self.create_component(ACBus, name=row["name"])
            self.add_component(bus)

    def build_time_series(self) -> None:
        """Attach time series to components."""
        load_data = self.read_data_file("load_profiles")
        # Process and attach time series...

config = MyModelConfig(model_year=2030, scenario_name="base")
data_store = DataStore.from_json("mappings.json", folder="/data")
parser = MyModelParser(config, data_store)
system = parser.build_system()
```

# ... validate inputs before building

```python
class MyModelParser(BaseParser):

    def validate_inputs(self) -> None:
        """Validate configuration and data availability."""
        required_files = ["buses", "generators", "branches"]
        for file_name in required_files:
            if file_name not in self.data_store.list_data():
                raise ValueError(f"Required file '{file_name}' not found")
```

# ... create components from data

```python
class MyModelParser(BaseParser):

    def build_system_components(self) -> None:
        """Create validated components."""
        bus_data = self.read_data_file("buses")
        for row in bus_data.iter_rows(named=True):
            bus = self.create_component(
                ACBus,
                name=row["bus_name"],
                voltage=row["voltage_kv"],
            )
            self.add_component(bus)
```

# ... attach time series to components

```python
from infrasys.time_series_models import SingleTimeSeries

class MyModelParser(BaseParser):

    def build_time_series(self) -> None:
        """Attach time series data to components."""
        load_profiles = self.read_data_file("hourly_loads")

        for bus_name in load_profiles.columns:
            bus = self.system.get_component(ACBus, bus_name)
            time_series = SingleTimeSeries(
                data=load_profiles[bus_name].to_numpy(),
                variable_name="max_active_power",
            )
            self.add_time_series(bus, time_series)
```
