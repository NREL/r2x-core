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



R2X Core is a model-agnostic framework for building power system model translators.
It provides the core infrastructure, data models, plugin architecture, and APIs that enable translation between different power system modeling platforms like ReEDS, PLEXOS, SWITCH, Sienna, and more.

## Features

- Plugin-based architecture with automatic discovery and registration
- Support for multiple file formats: CSV, HDF5, Parquet, JSON, and XML
- Standardized power system component models via [infrasys](https://github.com/NREL/infrasys)
- Abstract base classes (`BaseParser`, `BaseExporter`) for implementing model translators
- Type-safe configuration management with Pydantic models
- Built-in data transformations, filters, and validations
- Flexible data store with automatic format detection
- System modifiers for applying transformations to power system models

## Quick Start

```console
pip install r2x-core
```

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

👉 [See the full tutorial](https://nrel.github.io/r2x-core/tutorials/getting-started/) for a complete example.

## Documentation

- [Getting Started Tutorial](https://nrel.github.io/r2x-core/tutorials/getting-started/) - Step-by-step guide to building your first translator
- [Plugin System Guide](https://nrel.github.io/r2x-core/explanations/plugin-system/) - Understanding the plugin architecture
- [How-To Guides](https://nrel.github.io/r2x-core/how-tos/) - Task-oriented guides for common workflows
- [API Reference](https://nrel.github.io/r2x-core/references/) - Complete API documentation

## Roadmap

If you're curious about what we're working on, check out the roadmap:

- [Active issues](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3A%22Working+on+it+%F0%9F%92%AA%22+sort%3Aupdated-asc): Issues that we are actively working on.
- [Prioritized backlog](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3ABacklog): Issues we'll be working on next.
- [Nice-to-have](https://github.com/NREL/r2x-core/labels/Optional): Nice to have features or Issues to fix. Anyone can start working on (please let us know before you do).
- [Ideas](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3AIdea): Future work or ideas for R2X Core.
