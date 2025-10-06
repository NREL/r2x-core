# ... create a basic parser

```python
from pydantic import BaseModel
from r2x_core.parser import BaseParser
from r2x_core.plugin_config import PluginConfig
from r2x_core.store import DataStore
from r2x_core.exceptions import ValidationError, ParserError, ComponentCreationError

# Define configuration
class MyModelConfig(PluginConfig):
    """Configuration for MyModel parser."""

    model_year: int
    scenario_name: str

# Create parser class
class MyModelParser(BaseParser):
    """Parser for MyModel data."""

    def __init__(self, config: MyModelConfig, data_store: DataStore, **kwargs):
        super().__init__(config, data_store, **kwargs)
        self.model_year = config.model_year

    def validate_inputs(self) -> None:
        """Validate configuration."""
        if self.model_year < 2020:
            raise ValidationError("Model year must be >= 2020")

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

# Use the parser
config = MyModelConfig(model_year=2030, scenario_name="base")
data_store = DataStore.from_json("mappings.json", folder="/data")
parser = MyModelParser(config, data_store)
system = parser.build_system()
```

# ... validate inputs before building

```python
from r2x_core.exceptions import ValidationError, ParserError

class MyModelParser(BaseParser):

    def validate_inputs(self) -> None:
        """Validate configuration and data availability."""
        # Check required data files are present
        required_files = ["buses", "generators", "branches"]
        for file_name in required_files:
            if file_name not in self.data_store._data_files:
                raise ParserError(f"Required file '{file_name}' not in data store")

        # Validate model year
        years_data = self.get_data("available_years")
        available = years_data["year"].to_list()
        if self.config.model_year not in available:
            raise ValidationError(
                f"Year {self.config.model_year} not in {available}"
            )
```

# ... create components with validation

```python
from r2x_core.exceptions import ComponentCreationError

def build_system_components(self) -> None:
    """Create validated components."""
    # Read bus data
    bus_data = self.read_data_file("buses")

    # Create buses with validation
    for row in bus_data.iter_rows(named=True):
        try:
            bus = self.create_component(
                ACBus,
                name=row["bus_name"],
                voltage=row["voltage_kv"],
                bus_type=ACBusTypes.PV,
            )
            self.add_component(bus)
        except Exception as e:
            raise ComponentCreationError(
                f"Failed to create bus {row['bus_name']}: {e}"
            )
```

# ... skip validation for performance

```python
# Create parser with validation skipped
parser = MyModelParser(
    config=config,
    data_store=data_store,
    skip_validation=True  # Skip pydantic validation
)

# Or skip for specific components
def build_system_components(self) -> None:
    """Create components without validation."""
    # Temporarily disable validation
    original_skip = self.skip_validation
    self.skip_validation = True

    try:
        for row in large_dataset.iter_rows(named=True):
            component = self.create_component(Generator, **row)
            self.add_component(component)
    finally:
        self.skip_validation = original_skip
```

# ... attach time series to components

```python
def build_time_series(self) -> None:
    """Attach time series data to components."""
    from infrasys.time_series_models import SingleTimeSeries

    # Read time series data
    load_profiles = self.read_data_file("hourly_loads")

    # Attach to each bus
    for bus_name in load_profiles.columns:
        bus = self.system.get_component(ACBus, bus_name)

        time_series = SingleTimeSeries(
            data=load_profiles[bus_name].to_numpy(),
            variable_name="max_active_power",
        )

        self.add_time_series(bus, time_series)
```

# ... post-process the system

```python
class MyModelParser(BaseParser):

    def post_process_system(self) -> None:
        """Custom post-processing after system built."""
        # Log summary
        logger.info(f"System '{self.system.name}' built successfully")
        logger.info(f"  Buses: {len(self.system.get_components(ACBus))}")
        logger.info(f"  Generators: {len(self.system.get_components(Generator))}")

        # Validate connectivity
        self._validate_connectivity()

        # Add metadata
        self.system.metadata = {
            "model_year": self.config.model_year,
            "scenario": self.config.scenario_name,
            "created": datetime.now().isoformat(),
        }

    def _validate_connectivity(self) -> None:
        """Ensure all generators connected to valid buses."""
        buses = set(self.system.get_components(ACBus))
        for gen in self.system.get_components(Generator):
            if gen.bus not in buses:
                raise ValidationError(f"Generator {gen.name} has invalid bus")
```

# ... use parser with plugin system

```python
# Plugin can call methods individually
def build_from_plugin(parser_class, config, data_store):
    """Build system using plugin orchestration."""
    # Create parser
    parser = parser_class(config, data_store)

    # Validate separately
    parser.validate_inputs()

    # Build components only
    parser.build_system_components()

    # Apply plugin modifications
    modify_components(parser.system)

    # Build time series
    parser.build_time_series()

    # Finalize
    parser.post_process_system()

    return parser.system
```

# ... handle errors gracefully

```python
from r2x_core.exceptions import ParserError, ValidationError, ComponentCreationError

class MyModelParser(BaseParser):

    def build_system_components(self) -> None:
        """Create components with error handling."""
        try:
            bus_data = self.get_data("buses")
        except KeyError:
            raise ParserError("Required file 'buses' not found in data store")

        for idx, row in enumerate(bus_data.iter_rows(named=True)):
            try:
                bus = self.create_component(ACBus, **row)
                self.add_component(bus)
            except Exception as e:
                logger.error(f"Failed at row {idx}: {row}")
                raise ComponentCreationError(f"Bus creation failed: {e}") from e
```

# ... customize component creation

```python
class MyModelParser(BaseParser):

    def create_component(self, component_class, **field_values):
        """Override to add model-specific defaults."""
        # Add defaults for thermal generators
        if component_class == ThermalGen:
            field_values.setdefault("fuel_type", "natural_gas")
            field_values.setdefault("efficiency", 0.5)
            field_values.setdefault("min_up_time", 4.0)

        # Add defaults for renewable generators
        elif component_class == RenewableGen:
            field_values.setdefault("power_factor", 1.0)

        # Call parent implementation
        return super().create_component(component_class, **field_values)
```

# ... work with multiple model years

```python
class MultiYearConfig(PluginConfig):
    """Configuration supporting multiple years."""

    model_years: list[int]
    scenario_name: str

class MultiYearParser(BaseParser):

    def build_system_components(self) -> None:
        """Create components for multiple years."""
        for year in self.config.model_years:
            # Read year-specific data
            gen_data = self.read_data_file(
                "generators",
                use_cache=False  # Don't cache year-specific data
            )

            # Filter for this year
            year_data = gen_data.filter(pl.col("year") == year)

            # Create components for this year
            for row in year_data.iter_rows(named=True):
                gen = self.create_component(
                    Generator,
                    name=f"{row['name']}_{year}",
                    **row
                )
                self.add_component(gen)
```

# ... integrate with DataStore transformations

```python
# Define transformations in DataFile
from r2x_core import DataFile

data_store = DataStore(folder="/data")
data_store.add_data_file(DataFile(
    name="generators",
    fpath="raw_generators.csv",
    transformations=[
        {"type": "rename", "column_mapping": {"gen_id": "name", "cap": "capacity"}},
        {"type": "filter", "filters": {"status": "active"}},
        {"type": "cast_schema", "schema": {"capacity": "float64"}},
    ]
))

# Parser automatically uses transformed data
class MyModelParser(BaseParser):

    def build_system_components(self) -> None:
        # Data is already transformed according to DataFile config
        gen_data = self.read_data_file("generators")

        # Column names are already renamed, filtered, and cast
        for row in gen_data.iter_rows(named=True):
            gen = self.create_component(
                Generator,
                name=row["name"],  # Was "gen_id" in file
                capacity=row["capacity"],  # Already float64
            )
            self.add_component(gen)
```

# ... use plugin standards for configuration

:::{seealso}
For complete details on plugin standards, see the [Plugin Standards Guide](plugin-standards.md).
:::

```python
from r2x_core import PluginConfig, BaseParser

class MyModelConfig(PluginConfig):
    """Model configuration with defaults."""

    solve_year: int
    scenario: str = "reference"

# Load defaults from config/constants.json
defaults = MyModelConfig.load_defaults()
config = MyModelConfig(solve_year=2030, defaults=defaults)

# Access default values
excluded_techs = config.defaults.get("excluded_techs", [])
default_capacity = config.defaults.get("default_capacity", 100.0)
```

# ... discover file mappings

```python
# Get file mapping path for your parser
mapping_path = MyModelParser.get_file_mapping_path()
print(f"File mappings at: {mapping_path}")

# Load mappings and create DataStore
if mapping_path.exists():
    data_store = DataStore.from_json(mapping_path, folder="/data/mymodel")
```

# ... generate CLI schemas

```python
# Generate CLI-friendly schema
schema = MyModelConfig.get_cli_schema()

# Use for building CLI tools
for field_name, field_info in schema["properties"].items():
    print(f"{field_name} -> {field_info['cli_flag']}")
    # solve_year -> --solve-year
    # scenario -> --scenario
```
