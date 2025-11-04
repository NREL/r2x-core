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

- Plugin-based architecture - Singleton registry with automatic discovery and registration of parsers, exporters, system modifiers, and filters
- Standardized component models - Power system components via [infrasys](https://github.com/NREL/infrasys)
- Multiple file format support - Native support for CSV, HDF5, Parquet, JSON, and XML
- Type-safe configuration - Pydantic-based `PluginConfig` for model-specific parameters with defaults loading
- Data transformation pipeline - Built-in filters, column mapping, and reshaping operations
- Abstract base classes - `BaseParser` and `BaseExporter` for implementing translators
- Flexible data store - Automatic format detection and intelligent caching
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
store = DataStore(folder_path="/path/to/data")

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

### Building a Model Translator

Create parsers and exporters for your power system model:

```python
from r2x_core import BaseParser, BaseExporter, PluginConfig, DataStore

# Define type-safe configuration
class MyModelConfig(PluginConfig):
    folder: str
    year: int

# Implement your parser
class MyModelParser(BaseParser):
    def build_system_components(self):
        # Load data and build system components
        gen_data = self.data_store.read_data("generators")
        # ... create system components
        return Ok(None)

    def build_time_series(self):
        # Attach time series data
        return Ok(None)

# Create a data store and parser
config = MyModelConfig(folder="/path/to/data", year=2030)
store = DataStore(folder_path=config.folder)
parser = MyModelParser(config, data_store=store)
system = parser.build_system()
```

### Plugin Registration and Discovery

Create a registration function that returns a `Package` with your plugins:

```python
from r2x_core import Package, ParserPlugin, ExporterPlugin

def register_plugins() -> Package:
    """Register all plugins for this package."""
    # Create plugin metadata
    parser_plugin = ParserPlugin(
        name="my-model-parser",
        obj=MyModelParser,
        call_method="build_system",
        config=MyModelConfig,
        requires_store=True,
    )

    exporter_plugin = ExporterPlugin(
        name="my-model-exporter",
        obj=MyModelExporter,
        call_method="export",
        config=MyModelConfig,
    )

    # Package plugins together
    return Package(
        name="my-model-plugin",
        plugins=[parser_plugin, exporter_plugin],
        metadata={"version": "1.0.0", "author": "Your Name"},
    )
```

Make plugins discoverable via `pyproject.toml`:

```toml
[project.entry-points.r2x_plugins]
my_model = "my_package.plugins:register_plugins"
```

## Documentation

Comprehensive documentation is available at [nrel.github.io/r2x-core](https://nrel.github.io/r2x-core/):

- **[Getting Started Tutorial](https://nrel.github.io/r2x-core/tutorials/getting-started/)** - Step-by-step guide to building your first translator
- **[Installation Guide](https://nrel.github.io/r2x-core/install/)** - Detailed installation instructions and options
- **[How-To Guides](https://nrel.github.io/r2x-core/how-tos/)** - Task-oriented guides for common workflows:
  - [Configuration Management](https://nrel.github.io/r2x-core/how-tos/configuration/)
  - [Data Reading](https://nrel.github.io/r2x-core/how-tos/data-reading/)
  - [DataStore Management](https://nrel.github.io/r2x-core/how-tos/datastore-management/)
  - [File Operations](https://nrel.github.io/r2x-core/how-tos/file-operations/)
  - [Plugin Registration](https://nrel.github.io/r2x-core/how-tos/plugin-registration/)
  - [System Operations](https://nrel.github.io/r2x-core/how-tos/system-operations/)
  - [Unit Operations](https://nrel.github.io/r2x-core/how-tos/unit-operations/)
- **[Explanations](https://nrel.github.io/r2x-core/explanations/)** - Deep dives into key concepts:
  - [Plugin System Architecture](https://nrel.github.io/r2x-core/explanations/plugin-system/)
  - [Unit System](https://nrel.github.io/r2x-core/explanations/unit-system/)
  - [HDF5 Readers](https://nrel.github.io/r2x-core/explanations/h5-readers/)
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
