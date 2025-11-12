# Plugin System

For complete API documentation of plugin classes, see {doc}`api`.

## Overview

The R2X Core plugin system provides models for discovering and managing parser, exporter, and upgrader plugins. Plugins are discovered automatically via entry points defined in `pyproject.toml`.

## Quick Reference

- {py:class}`~r2x_core.PluginManifest` - Package-level registry exported by entry points
- {py:class}`~r2x_core.PluginSpec` - Declarative description of a single plugin
- {py:class}`~r2x_core.InvocationSpec` - How to instantiate/call the entry point
- {py:class}`~r2x_core.IOContract` - Inputs/outputs consumed or produced
- {py:class}`~r2x_core.ResourceSpec` - Configuration/DataStore requirements
- {py:class}`~r2x_core.PluginConfig` - Base class for type-safe model-specific configuration

## Builder Helpers

Plugin authors rarely need to populate every field of :class:`PluginSpec` manually. Use the helper constructors:

- :meth:`PluginSpec.parser` - describe a typical `config + store -> system` parser
- :meth:`PluginSpec.exporter` - describe an exporter that consumes a system
- :meth:`PluginSpec.function` - declare a simple function modifier
- :meth:`PluginSpec.upgrader` - wrap an upgrader class and re-use its registered steps

These helpers set sensible defaults (method names, IO contracts, store/config requirements) while still producing a full manifest for CLI tooling.

## Usage Examples

### Creating a PluginConfig

:class:`PluginConfig` is a Pydantic-based configuration class designed for model-specific parameters.
It automatically resolves the config directory and supports loading defaults from JSON files.

```python
from r2x_core import PluginConfig
from pydantic import field_validator

class MyModelConfig(PluginConfig):
    """Configuration for MyModel plugin."""

    folder: str
    year: int
    scenario: str = "base"

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        if v < 2020 or v > 2050:
            raise ValueError("Year must be between 2020 and 2050")
        return v

# Use it
config = MyModelConfig(folder="/path/to/data", year=2030)

# Load defaults from config/defaults.json
defaults = config.load_defaults()

# Load file mappings from config/file_mapping.json
file_mappings = config.load_file_mapping()
```

### Implementing a Parser and Exporter

Create implementations of `BaseParser` and `BaseExporter`:

```python
from r2x_core import BaseParser, BaseExporter, PluginConfig

class MyModelConfig(PluginConfig):
    folder: str
    year: int

class MyParser(BaseParser):
    def build_system_components(self):
        # Build components
        pass

    def build_time_series(self):
        # Add time series
        pass

class MyExporter(BaseExporter):
    def prepare_export(self):
        # Export logic
        pass
```


### Entry Point Discovery

Register plugins in external packages via `pyproject.toml`:

```toml
[project.entry-points.r2x_plugin]
my_model = "my_package.plugins"
```

Plugins are discovered by loading the entry point and reading a `PluginManifest`. A manifest exports a list of :class:`PluginSpec` objects, each of which contains all the metadata downstream tooling needs (call signatures, resource requirements, IO contracts, etc.). Tools such as the CLI can parse the manifest file statically (via `ast-grep` or JSON artifacts) without executing arbitrary plugin code.

### Manifest Export Utility

Use the bundled CLI to emit a JSON artifact for downstream apps or packaging workflows:

```bash
r2x-export-manifest --module my_package.plugins --output plugins.json
```

This command loads the manifest attribute, validates it, and writes a JSON file that other runtimes (Rust CLI, pipelines, etc.) can consume without importing Python code.

### Configuration Directory Structure

:class:`PluginConfig` expects the following directory structure relative to the config class module:

```
config/
├── file_mapping.json    # Maps input files to processing rules
├── defaults.json        # Default model parameters and constants
└── (other config files)
```

## PluginConfig Features

- **Automatic path resolution** - Config directory defaults to `config/` subdirectory relative to the config class
- **JSON defaults loading** - Load model parameters from `config/defaults.json`
- **File mapping support** - Load input/output file mappings from `config/file_mapping.json`
- **Pydantic validation** - Full support for Pydantic field validators and configuration
- **Type safety** - IDE support and runtime validation for all model parameters

## See Also

- {doc}`../how-tos/plugin-registration` - Detailed plugin registration guide
- {doc}`../how-tos/plugin-standards` - Plugin development standards
- {doc}`../explanations/plugin-system` - Deep dive into plugin architecture
- {doc}`parser` - BaseParser reference
- {doc}`exporter` - BaseExporter reference
