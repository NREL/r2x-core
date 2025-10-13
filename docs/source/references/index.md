# Reference

R2X Core provides data file management, parser, and exporter framework classes:

## Core Classes

- {py:class}`~r2x_core.System` - Core system container
- {py:class}`~r2x_core.DataStore` - Data file storage
- {py:class}`~r2x_core.DataReader` - Data reading utility
- {py:class}`~r2x_core.BaseParser` - Parser base class
- {py:class}`~r2x_core.PluginConfig` - Configuration base
- {py:class}`~r2x_core.BaseExporter` - Exporter base class
- {py:class}`~r2x_core.PluginManager` - Plugin management
- {py:class}`~r2x_core.PluginComponent` - Plugin container
- {py:class}`~r2x_core.FileFormat` - File format enum

## Versioning and Upgrades

- {py:class}`~r2x_core.VersioningStrategy` - Versioning protocol
- {py:class}`~r2x_core.SemanticVersioningStrategy` - Semantic versioning
- {py:class}`~r2x_core.GitVersioningStrategy` - Git-based versioning
- {py:class}`~r2x_core.FileModTimeStrategy` - File time versioning
- {py:class}`~r2x_core.UpgradeContext` - Upgrade context enum
- {py:class}`~r2x_core.UpgradeStep` - Upgrade step definition
- {py:class}`~r2x_core.UpgradeResult` - Upgrade result with rollback
- {py:func}`~r2x_core.apply_upgrade` - Apply single upgrade
- {py:func}`~r2x_core.apply_upgrades` - Apply multiple upgrades
- {py:func}`~r2x_core.apply_upgrades_with_rollback` - Apply with rollback

For detailed API documentation with examples and method signatures, see the [Complete API Documentation](./api.md).

## Documentation Coverage

```{eval-rst}
.. report:doc-coverage::
   :reportid: src
```

```{toctree}
:maxdepth: 1
:hidden:

api
system
units
parser
exporter
plugins
versioning
upgrader
processors
utils
exceptions
file-formats
file-types
models
```
