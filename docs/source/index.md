```{toctree}
:maxdepth: 2
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

R2X Core is a model-agnostic framework for building power system model translators. It provides the core infrastructure, data models, plugin architecture, and APIs that enable translation between different power system modeling platforms.

## About R2X Core

R2X Core serves as the foundation for building translators between power system models like ReEDS, PLEXOS, SWITCH, Sienna, and more. It provides a plugin-based architecture where you can register parsers, exporters, and transformations to create custom translation workflows.

### Key Features

R2X Core offers the following capabilities:

- **Plugin-based architecture** - Automatic discovery and registration of parsers, exporters, and transformations
- **Standardized component models** - Power system components via [infrasys](https://github.com/NREL/infrasys)
- **Multiple file format support** - Native support for CSV, HDF5, Parquet, JSON, and XML
- **Type-safe configuration** - Pydantic models for validation and IDE support
- **Data transformation pipeline** - Built-in filters, column mapping, and reshaping operations
- **Abstract base classes** - `BaseParser` and `BaseExporter` for implementing translators
- **System modifiers** - Apply transformations to entire power system models
- **Flexible data store** - Automatic format detection and intelligent caching

## Quick Start

```python
from r2x_core import PluginManager, BaseParser

# Register your model plugin
PluginManager.register_model_plugin(
    name="my_model",
    config=MyModelConfig,
    parser=MyModelParser,
    exporter=MyModelExporter,
)

# Use it
manager = PluginManager()
parser = manager.load_parser("my_model")
system = parser(config, data_store).build_system()
```

👉 [See the full tutorial](tutorials/getting-started.md) for a complete example.

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
