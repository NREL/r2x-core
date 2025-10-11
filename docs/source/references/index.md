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
processors
utils
exceptions
file-formats
file-types
models
```
