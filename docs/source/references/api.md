(api-reference)=

# API Reference

Complete API documentation for all r2x-core classes and functions.

## System

```{eval-rst}
.. autoclass:: r2x_core.System
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. automodule:: r2x_core.units
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
```

## Data Management

```{eval-rst}
.. autoclass:: r2x_core.DataStore
   :members:
   :no-index:
```

```{eval-rst}
.. autoclass:: r2x_core.DataReader
   :members:
```

```{eval-rst}
.. autopydantic_model:: r2x_core.DataFile
   :model-show-json: False
   :model-show-config-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False
   :field-list-validators: False
```

## Parser Framework

```{eval-rst}
.. autoclass:: r2x_core.BaseParser
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
```

```{eval-rst}
.. autopydantic_model:: r2x_core.PluginConfig
   :model-show-json: False
   :model-show-config-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False
   :field-list-validators: False
   :no-index:
```

## Exporter Framework

```{eval-rst}
.. autoclass:: r2x_core.BaseExporter
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
```

## Plugin System

The plugin system is extended through subclasses of the parser, exporter, and upgrader frameworks.

## File Types

```{eval-rst}
.. autoclass:: r2x_core.FileFormat
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
```

## Exceptions

```{eval-rst}
.. autoclass:: r2x_core.ParserError
   :members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: r2x_core.ValidationError
   :members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: r2x_core.ComponentCreationError
   :members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: r2x_core.ExporterError
   :members:
   :show-inheritance:
```

## Versioning and Upgrades

```{eval-rst}
.. autoclass:: r2x_core.SemanticVersioningStrategy
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: r2x_core.GitVersioningStrategy
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: r2x_core.UpgradeStep
   :members:
   :show-inheritance:
```

```{eval-rst}
.. autofunction:: r2x_core.run_upgrade_step
```

## Utilities

```{eval-rst}
.. autofunction:: r2x_core.utils.filter_valid_kwargs
```

```{eval-rst}
.. autofunction:: r2x_core.utils.validate_file_extension
```

## Data Processors

See {doc}`processors` for complete processor documentation.
