# Plugin System

For complete API documentation of plugin classes, see {doc}`./api`.

## Overview

The R2X Core plugin system provides models for discovering and managing parser, exporter, and upgrader plugins. Plugins are discovered automatically via entry points defined in `pyproject.toml`.

## Quick Reference

- {py:class}`~r2x_core.PluginConfig` - Base class for type-safe model-specific configuration
- {py:class}`~r2x_core.Plugin` - Plugin base class for extending r2x-core
- {py:class}`~r2x_core.PluginContext` - Execution context with source and target systems

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

### Entry Point Discovery

Register plugins in external packages via `pyproject.toml`:

```toml
[project.entry-points.r2x_plugin]
my_model = "my_package.plugins"
```

Plugins are discovered by loading the entry point and reading a `PluginManifest`. A manifest exports a list of :class:`PluginSpec` objects, each of which contains all the metadata downstream tooling needs (call signatures, resource requirements, IO contracts, etc.). Tools such as the CLI can parse the manifest file statically (via `ast-grep` or JSON artifacts) without executing arbitrary plugin code.

### Manifest Export Utility

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

- {doc}`../how-tos/register-plugins` - Detailed plugin registration guide
- {doc}`../how-tos/structure-plugin-directories` - Plugin development standards
- {doc}`../explanations/plugin-system` - Deep dive into plugin architecture
