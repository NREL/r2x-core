### r2x-core

> Extensible framework for power system model translation
>
> [![image](https://img.shields.io/pypi/v/r2x.svg)](https://pypi.python.org/pypi/r2x-core)
> [![image](https://img.shields.io/pypi/l/r2x.svg)](https://pypi.python.org/pypi/r2x-core)
> [![image](https://img.shields.io/pypi/pyversions/r2x.svg)](https://pypi.python.org/pypi/r2x-core)
> [![CI](https://github.com/NREL/r2x/actions/workflows/CI.yaml/badge.svg)](https://github.com/NREL/r2x/actions/workflows/ci.yaml)
> [![codecov](https://codecov.io/gh/NREL/r2x-core/branch/main/graph/badge.svg)](https://codecov.io/gh/NREL/r2x-core)
> [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
> [![Documentation](https://github.com/NREL/r2x-core/actions/workflows/docs.yaml/badge.svg?branch=main)](https://nrel.github.io/r2x-core/)
> [![Docstring Coverage](https://nrel.github.io/r2x-core/_static/docstr_coverage_badge.svg)](https://nrel.github.io/r2x-core/)

R2X Core is a model-agnostic framework for building power system model translators. It provides the core infrastructure, data models, plugin architecture, and APIs that enable translation between different power system modeling platforms.

## About R2X Core

R2X Core serves as the foundation for building translators between power system models like ReEDS, PLEXOS, SWITCH, Sienna, and more. It provides a plugin-based architecture where you can register parsers, exporters, and transformations to create custom translation workflows.

## Features

- Capability-based plugin architecture - Plugins implement only the hooks they need (validate, prepare, build, transform, translate, export, cleanup)
- Declarative rule system - Define model translations through configuration, not code
- Rule filters for selective translation - Composable filters to control which components rules process
- Standardized component models - Power system components via [infrasys](https://github.com/NREL/infrasys)
- Multiple file format support - Native support for CSV, HDF5, Parquet, JSON, and XML
- Configurable HDF5 reader - Flexible configuration-driven approach for any HDF5 structure
- Type-safe configuration - Pydantic-based `PluginConfig` with automatic validation
- Per-unit system - Automatic unit handling with device-base, natural units, and system-base display modes
- Flexible data store - Automatic format detection, intelligent caching, and component tracking
- Entry point discovery - External packages can register plugins via setuptools/pyproject.toml entry points

## Installation

```console
pip install r2x-core
```

Or with [uv](https://docs.astral.sh/uv/):

```console
uv add r2x-core
```

**Python version support:** 3.11, 3.12, 3.13

## Quick Start

### Using the DataStore

The `DataStore` provides a high-level interface for managing and loading data files:

```python
from r2x_core import DataStore, DataFile

# Create a DataStore pointing to your data directory
store = DataStore(path="/path/to/data")

# Add files to the store
data_file = DataFile(name="generators", fpath="gen.csv")
store.add_data(data_file)

# Or add multiple files at once
files = [
    DataFile(name="generators", fpath="gen.csv"),
    DataFile(name="loads", fpath="load.csv"),
    DataFile(name="buses", fpath="buses.h5")
]
store.add_data(*files)

# Read data from the store
gen_data = store.read_data("generators")

# List all available data files
available_files = store.list_data()

# Remove a data file
store.remove_data("generators")
```

### Building a Model Translator with Plugins

Create a plugin to translate power system models:

```python
from r2x_core import Plugin, PluginConfig, PluginContext, Rule, System, DataStore
from rust_ok import Ok

# Define type-safe configuration
class MyModelConfig(PluginConfig):
    input_folder: str
    model_year: int
    scenario: str = "base"

# Implement your translator plugin
class MyModelTranslator(Plugin[MyModelConfig]):
    def on_prepare(self):
        # Load data and setup resources
        return Ok(None)

    def on_build(self):
        # Create system from input data
        system = System(name=f"{self.config.scenario}_{self.config.model_year}")
        return Ok(system)

    def on_translate(self):
        # Define translation rules
        rules = [
            Rule(
                name="translate_generators",
                source_type="SourceGenerator",
                target_type="Generator",
                version=1,
                field_map={
                    "name": "name",
                    "capacity": "p_max_mw",
                    "location": "zone",
                }
            ),
        ]
        # Apply rules to create target system
        return Ok(self.system)

# Execute the translation
config = MyModelConfig(input_folder="/path/to/data", model_year=2030)
context = PluginContext(config=config)
plugin = MyModelTranslator.from_context(context)
result = plugin.run()
print(f"Translated system: {result.system.name}")
```

### Plugin Registration and Discovery

Register plugins via `pyproject.toml` entry points for automatic discovery:

```toml
[project.entry-points.r2x_plugin]
my_model_translator = "my_package.plugins:MyModelTranslator"
my_model_builder = "my_package.plugins:MyModelBuilder"
```

The plugin system automatically discovers and introspects plugins to extract their capabilities:

```python
from r2x_core import Plugin

# Get plugin metadata programmatically
config_type = MyModelTranslator.get_config_type()
print(f"Config type: {config_type.__name__}")

# Discover which hooks are implemented
hooks = MyModelTranslator.get_implemented_hooks()
print(f"Implemented hooks: {hooks}")
# Output: ['on_prepare', 'on_build', 'on_translate']

# Introspect config fields
import inspect
fields = config_type.model_fields
for field_name, field_info in fields.items():
    print(f"  {field_name}: {field_info.annotation}")
```

Plugins are discovered, instantiated, and executed through a shared registry that handles dependency injection and lifecycle management.

## Documentation

Comprehensive documentation is available at [nrel.github.io/r2x-core](https://nrel.github.io/r2x-core/):

- **[Getting Started Tutorial](https://nrel.github.io/r2x-core/tutorials/getting-started/)** - Step-by-step guide to building your first translator
- **[Installation Guide](https://nrel.github.io/r2x-core/install/)** - Detailed installation instructions and options
- **[How-To Guides](https://nrel.github.io/r2x-core/how-tos/)** - Task-oriented guides for common workflows:
  - [Read Data Files](https://nrel.github.io/r2x-core/how-tos/read-data-files/)
  - [Configure Data Files](https://nrel.github.io/r2x-core/how-tos/configure-data-files/)
  - [Define Rule Mappings](https://nrel.github.io/r2x-core/how-tos/define-rule-mappings/)
  - [Apply Rules](https://nrel.github.io/r2x-core/how-tos/apply-rules/)
  - [Register Plugins](https://nrel.github.io/r2x-core/how-tos/register-plugins/)
  - [Manage DataStores](https://nrel.github.io/r2x-core/how-tos/manage-datastores/)
  - [Manage Systems](https://nrel.github.io/r2x-core/how-tos/manage-systems/)
  - [Convert Units](https://nrel.github.io/r2x-core/how-tos/convert-units/)
- **[Explanations](https://nrel.github.io/r2x-core/explanations/)** - Deep dives into key concepts:
  - [Plugin System Architecture](https://nrel.github.io/r2x-core/explanations/plugin-system/)
  - [Rule System Architecture](https://nrel.github.io/r2x-core/explanations/rules-system/)
  - [Unit System Design](https://nrel.github.io/r2x-core/explanations/unit-system/)
  - [HDF5 Reader System](https://nrel.github.io/r2x-core/explanations/h5-readers/)
  - [Data Management](https://nrel.github.io/r2x-core/explanations/data-management/)
- **[Tutorials](https://nrel.github.io/r2x-core/tutorials/)** - In-depth walkthroughs:
  - [Plugin System](https://nrel.github.io/r2x-core/tutorials/plugin-system/)
  - [Plugin Context](https://nrel.github.io/r2x-core/tutorials/plugin-context/)
  - [Plugin Discovery](https://nrel.github.io/r2x-core/tutorials/plugin-discovery/)
  - [Working with Units](https://nrel.github.io/r2x-core/tutorials/working-with-units/)
- **[API Reference](https://nrel.github.io/r2x-core/references/)** - Complete API documentation

## Roadmap

Curious about what we're working on? Check out the roadmap:

- [Active issues](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3A%22Working+on+it+%F0%9F%92%AA%22+sort%3Aupdated-asc) - Issues that we are actively working on
- [Prioritized backlog](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3ABacklog) - Issues we'll be working on next
- [Nice-to-have](https://github.com/NREL/r2x-core/labels/Optional) - Features or fixes anyone can start working on (please let us know before you do)
- [Ideas](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3AIdea) - Future work or ideas for R2X Core

## Contributing

We welcome contributions! Please see our [Contributing Guide](https://nrel.github.io/r2x-core/contributing/) for guidelines on how to contribute to R2X Core.

## License

R2X Core is released under the BSD 3-Clause License. See [LICENSE.txt](LICENSE.txt) for details.
