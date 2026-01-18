# Plugin System

The r2x plugin system uses a **capability-based design** where plugins implement only the hooks they need. The plugin lifecycle runs hooks in a fixed order, skipping any that aren't implemented.

This approach provides:
- **Flexibility**: Plugins do only what they need (build, transform, translate, export)
- **Clarity**: Required context fields are declared via type hints
- **Discoverability**: ast-grep can extract plugin config types and capabilities
- **Type Safety**: Generic `Plugin[ConfigT]` provides typed config access

## Creating a Simple Plugin

Plugins inherit from `Plugin[ConfigT]` where `ConfigT` is your configuration class:

```python doctest
>>> from r2x_core import Plugin, PluginContext, PluginConfig, System
>>> from rust_ok import Ok

>>> class MyConfig(PluginConfig):
...     name: str
...     count: int = 1

>>> class MyPlugin(Plugin[MyConfig]):
...     def on_build(self):
...         system = System(name=self.config.name)
...         return Ok(system)

>>> # Create context and run
>>> ctx = PluginContext(config=MyConfig(name="test"))
>>> plugin = MyPlugin.from_context(ctx)
>>> result_ctx = plugin.run()
>>> result_ctx.system.name
'test'
```

## Plugin Lifecycle

The plugin lifecycle consists of seven optional hooks, called in this fixed order:

1. **on_validate()** - Validate inputs and configuration
2. **on_prepare()** - Load data, setup resources
3. **on_build()** - Create a new system from scratch
4. **on_transform()** - Modify an existing system in-place
5. **on_translate()** - Convert source system to target system
6. **on_export()** - Write system to files
7. **on_cleanup()** - Cleanup resources

Each hook returns `Result[None | System, Exception]`. If any hook returns an error, execution stops and a `PluginError` is raised.

### Complete Lifecycle Example

```python doctest
>>> from r2x_core import Plugin, PluginContext, PluginConfig, System
>>> from rust_ok import Ok, Err, Result

>>> class FullConfig(PluginConfig):
...     input_name: str
...     scale_factor: float = 1.0
...     output_dir: str = "/tmp"

>>> class FullPlugin(Plugin[FullConfig]):
...     def on_validate(self) -> Result[None, Exception]:
...         if self.config.scale_factor <= 0:
...             return Err(ValueError("scale_factor must be positive"))
...         return Ok(None)
...
...     def on_prepare(self) -> Result[None, Exception]:
...         # Load data, setup
...         return Ok(None)
...
...     def on_build(self) -> Result[System, Exception]:
...         system = System(name=self.config.input_name)
...         return Ok(system)
...
...     def on_transform(self) -> Result[System, Exception]:
...         # Modify system
...         return Ok(self.system)
...
...     def on_cleanup(self) -> None:
...         pass

>>> ctx = PluginContext(config=FullConfig(input_name="example", scale_factor=2.0))
>>> plugin = FullPlugin.from_context(ctx)
>>> result = plugin.run()
>>> result.system.name
'example'
```

## Required vs Optional Context Fields

Plugins indicate which context fields they need via **property return types**:

- **Non-Optional return type** (e.g., `-> System`) = **required** - raises `PluginError` if missing
- **Optional return type** (e.g., `-> System | None`) = **optional** - returns None if missing

### Example: Parser (Requires config, store)

```python doctest
>>> from r2x_core import Plugin, PluginContext, PluginConfig, System, DataStore
>>> from pathlib import Path
>>> from rust_ok import Ok, Result

>>> class ParserConfig(PluginConfig):
...     input_file: str

>>> class SimpleParser(Plugin[ParserConfig]):
...     @property
...     def store(self) -> DataStore:  # Non-Optional = required
...         if self._ctx.store is None:
...             raise RuntimeError("DataStore required for parsing")
...         return self._ctx.store
...
...     def on_build(self) -> Result[System, Exception]:
...         system = System(name="parsed_system")
...         return Ok(system)

>>> store = DataStore()
>>> ctx = PluginContext(config=ParserConfig(input_file="data.csv"), store=store)
>>> parser = SimpleParser.from_context(ctx)
>>> result = parser.run()
>>> result.system.name
'parsed_system'
```

### Example: Exporter (Requires config, system, store)

```python doctest
>>> from r2x_core import Plugin, PluginContext, PluginConfig, System, DataStore
>>> from rust_ok import Ok, Result

>>> class ExporterConfig(PluginConfig):
...     output_dir: str

>>> class SimpleExporter(Plugin[ExporterConfig]):
...     @property
...     def system(self) -> System:  # Non-Optional = required
...         if self._ctx.system is None:
...             raise RuntimeError("System required for export")
...         return self._ctx.system
...
...     def on_export(self) -> Result[None, Exception]:
...         # Export system to files
...         return Ok(None)

>>> system = System(name="my_system")
>>> store = DataStore()
>>> ctx = PluginContext(config=ExporterConfig(output_dir="/tmp"), system=system, store=store)
>>> exporter = SimpleExporter.from_context(ctx)
>>> result = exporter.run()
>>> result.system.name
'my_system'
```

## Plugin Capabilities (Inferred from Hooks)

Plugin capabilities are automatically inferred from which hooks are implemented:

- **Build plugin**: Implements `on_build()` - Creates systems from data
- **Transform plugin**: Implements `on_transform()` - Modifies existing systems
- **Translate plugin**: Implements `on_translate()` - Converts source→target format
- **Export plugin**: Implements `on_export()` - Writes systems to files
- **Multi-capability plugin**: Implements multiple hooks

### Example: Multi-Capability Plugin

```python doctest
>>> from r2x_core import Plugin, PluginContext, PluginConfig, System
>>> from rust_ok import Ok, Result

>>> class TranslateExportConfig(PluginConfig):
...     format: str = "json"

>>> class Plexos2SiennaExporter(Plugin[TranslateExportConfig]):
...     def on_translate(self) -> Result[System, Exception]:
...         # Create target system from source
...         target = System(name="sienna_system")
...         return Ok(target)
...
...     def on_export(self) -> Result[None, Exception]:
...         # Also export the result
...         return Ok(None)

>>> source = System(name="plexos_system")
>>> ctx = PluginContext(config=TranslateExportConfig(), source_system=source)
>>> plugin = Plexos2SiennaExporter.from_context(ctx)
>>> result = plugin.run()
>>> result.target_system.name
'sienna_system'
```

## Configuration with Type Safety

Plugin config types are extracted via generics, enabling:
- Type-safe access to plugin-specific fields
- ast-grep discovery of config schemas
- Automatic validation via Pydantic

### Required vs Optional Config Fields

```python doctest
>>> from r2x_core import PluginConfig

>>> class FullConfig(PluginConfig):
...     model_year: int              # Required - no default
...     input_folder: str            # Required - no default
...     scenario: str = "base"       # Optional - has default
...     verbose: bool = False        # Optional - has default

>>> # Valid: provides all required fields
>>> cfg = FullConfig(model_year=2030, input_folder="/data")
>>> cfg.scenario
'base'

>>> # Invalid: missing required field
>>> try:
...     bad_cfg = FullConfig(model_year=2030)
... except Exception as e:
...     "input_folder" in str(e)
True
```

## Plugin Discovery

Plugins can be discovered using ast-grep rules that extract:
1. **Config type** from generic parameter: `class MyPlugin(Plugin[MyConfig])`
2. **Implemented hooks** from method names: `on_validate`, `on_build`, etc.
3. **Required context fields** from non-Optional property return types
4. **Config schema** from Pydantic field definitions

See `docs/plugin-discovery.md` for complete discovery rules.

## Passing Context Through Pipelines

Use the `evolve()` method for memory-efficient context updates:

```python doctest
>>> from r2x_core import Plugin, PluginContext, PluginConfig, System
>>> from rust_ok import Ok, Result

>>> class Config(PluginConfig):
...     pass

>>> # Build a system
>>> build_ctx = PluginContext(config=Config())
>>> system = System(name="built")

>>> # Pass to next step
>>> transform_ctx = build_ctx.evolve(system=system)
>>> transform_ctx.system.name
'built'

>>> # Continue pipeline
>>> export_ctx = transform_ctx.evolve(metadata={"exported": True})
>>> export_ctx.system.name
'built'
>>> export_ctx.metadata
{'exported': True}
```

## Error Handling

Plugins use `Result[T, E]` for error handling. If any hook returns `Err`, execution stops:

```python doctest
>>> from r2x_core import Plugin, PluginContext, PluginConfig
>>> from rust_ok import Ok, Err, Result

>>> class FailConfig(PluginConfig):
...     should_fail: bool = False

>>> class FailPlugin(Plugin[FailConfig]):
...     def on_validate(self) -> Result[None, Exception]:
...         if self.config.should_fail:
...             return Err(ValueError("Validation failed!"))
...         return Ok(None)

>>> # Success case
>>> ctx1 = PluginContext(config=FailConfig(should_fail=False))
>>> result1 = FailPlugin.from_context(ctx1).run()
>>> result1 is not None
True

>>> # Failure case
>>> ctx2 = PluginContext(config=FailConfig(should_fail=True))
>>> try:
...     FailPlugin.from_context(ctx2).run()
... except Exception as e:
...     "Validation failed" in str(e)
True
```

## Introspection for Plugin Discovery

Extract plugin metadata programmatically:

```python doctest
>>> from r2x_core import Plugin, PluginConfig
>>> from rust_ok import Ok

>>> class MyConfig(PluginConfig):
...     name: str

>>> class MyPlugin(Plugin[MyConfig]):
...     def on_validate(self):
...         return Ok(None)
...
...     def on_build(self):
...         return Ok(None)

>>> # Get config type
>>> MyPlugin.get_config_type().__name__
'MyConfig'

>>> # Get implemented hooks
>>> sorted(MyPlugin.get_implemented_hooks())
['on_build', 'on_validate']
```

## Best Practices

1. **Implement only needed hooks** - Don't implement hooks you don't need
2. **Use type hints for context fields** - Indicate required vs optional via return types
3. **Validate early** - Use `on_validate()` to catch errors before heavy operations
4. **Clean up resources** - Use `on_cleanup()` for resource management
5. **Use evolve() for pipelines** - Efficiently pass context between plugins
6. **Return specific errors** - Use appropriate exception types for better error handling
7. **Document config fields** - Add docstrings to config classes for discoverability

## Next Steps

- See `docs/plugin-context.md` for detailed context usage patterns
- See `docs/plugin-discovery.md` for ast-grep plugin discovery
- Check `tests/test_plugin*.py` for additional examples
