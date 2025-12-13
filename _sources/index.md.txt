```{toctree}
:maxdepth: 3
:hidden:

install
tutorials/index
how-tos/index
explanations/index
references/index
contributing
CHANGELOG
```

# R2X Core Documentation

[![Docstring Coverage](https://img.shields.io/badge/docstring%20coverage-100%25-brightgreen.svg)](_static/docstr_coverage_badge.svg)

R2X Core is a model-agnostic framework for building power system model translators. It provides the core infrastructure, data models, plugin architecture, and APIs that enable translation between different power system modeling platforms.

## About R2X Core

R2X Core serves as the foundation for building translators between power system models like ReEDS, PLEXOS, SWITCH, Sienna, and more. It provides a plugin-based architecture where you can register parsers, exporters, and transformations to create custom translation workflows.

### Key Features

R2X Core offers the following capabilities:

- **Plugin-based architecture** - Singleton registry with automatic discovery and registration of parsers, exporters, system modifiers, and filters
- **Standardized component models** - Power system components via [infrasys](https://github.com/NREL/infrasys)
- **Multiple file format support** - Native support for CSV, HDF5, Parquet, JSON, and XML
- **Type-safe configuration** - Pydantic-based `PluginConfig` for model-specific parameters with defaults loading
- **Data transformation pipeline** - Built-in filters, column mapping, and reshaping operations
- **Abstract base classes** - `BaseParser` and `BaseExporter` for implementing translators
- **System modifiers** - Apply transformations to entire power system models with flexible context passing
- **Filter functions** - Register custom data processing functions for reusable transformations
- **Flexible data store** - Automatic format detection and intelligent caching
- **Entry point discovery** - External packages can register plugins via setuptools/pyproject.toml entry points

## Quick Start

```python
from r2x_core import PluginManager, BaseParser, BaseExporter, PluginConfig

# Define type-safe configuration
class MyModelConfig(PluginConfig):
    folder: str
    year: int

# Register your model plugin
PluginManager.register_model_plugin(
    name="my_model",
    config=MyModelConfig,
    parser=MyModelParser,
    exporter=MyModelExporter,
)

# Use it
manager = PluginManager()
parser_class = manager.load_parser("my_model")
config = MyModelConfig(folder="/path/to/data", year=2030)
system = parser_class(config, data_store=data_store).build_system()
```

👉 [See the full tutorial](tutorials/getting-started.md) for a complete example.

### Plugin Discovery

Plugins can be registered programmatically or discovered from entry points. External packages register via `pyproject.toml`:

```toml
[project.entry-points.r2x_plugin]
my_model = "my_package.plugins:my_plugin_component"
```

See {doc}`references/plugins` for detailed examples and {doc}`how-tos/plugin-system/plugin-registration` for advanced patterns.

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
