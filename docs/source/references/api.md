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

## Units

The units module provides type-safe unit handling with automatic conversion and flexible display modes.

### Unit Specifications

```{eval-rst}
.. autoclass:: r2x_core.units.UnitSpec
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autofunction:: r2x_core.units.Unit
```

### Mixin Classes

```{eval-rst}
.. autoclass:: r2x_core.units.HasUnits
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: r2x_core.units.HasPerUnit
   :members:
   :undoc-members:
   :show-inheritance:
```

### Display Modes

```{eval-rst}
.. autoclass:: r2x_core.units.UnitSystem
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autofunction:: r2x_core.units.get_unit_system
```

```{eval-rst}
.. autofunction:: r2x_core.units.set_unit_system
```

```{eval-rst}
.. autofunction:: r2x_core.units.unit_system
```

## Data Management

```{eval-rst}
.. autoclass:: r2x_core.DataStore
   :members:
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
```

```{eval-rst}
.. autopydantic_model:: r2x_core.PluginConfig
   :model-show-json: False
   :model-show-config-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False
   :field-list-validators: False
```

## Exporter Framework

```{eval-rst}
.. autoclass:: r2x_core.BaseExporter
   :members:
   :undoc-members:
   :show-inheritance:
```

## Plugin System

```{eval-rst}
.. autoclass:: r2x_core.PluginManager
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: r2x_core.PluginComponent
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: r2x_core.SystemModifier
   :members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: r2x_core.FilterFunction
   :members:
   :show-inheritance:
```

## File Types

```{eval-rst}
.. autoclass:: r2x_core.FileFormat
   :members:
   :undoc-members:
   :show-inheritance:
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

## Utilities

```{eval-rst}
.. autofunction:: r2x_core.utils.filter_valid_kwargs
```

```{eval-rst}
.. autofunction:: r2x_core.utils.validate_file_extension
```

## Data Processors

See {doc}`processors` for complete processor documentation.
