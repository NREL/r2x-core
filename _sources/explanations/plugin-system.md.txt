# Plugin System Architecture

This document explains the design and architecture of the r2x-core plugin system, providing insight into how it works and why it was designed this way.

## Purpose and Goals

The plugin system enables **extensibility** and **modularity** in r2x-core by allowing applications and external packages to register custom components without modifying the core library. This separation of concerns provides:

- **Model-agnostic workflows**: Parse from any input model, export to any output model
- **Decentralized development**: Model-specific code lives in separate packages
- **Dynamic discovery**: Automatically find and load installed plugins
- **Reusable components**: Share parsers, exporters, and transformations across applications

## Architecture Overview

The plugin system consists of three main layers:

### 1. Plugin Types

r2x-core supports three distinct plugin types, each serving a different purpose:

#### Model Plugins
Model plugins register parser and/or exporter classes for specific energy models (e.g., ReEDS, PLEXOS, Sienna). Each model plugin consists of:

- **Configuration**: A `PluginConfig` subclass defining model-specific parameters with automatic path resolution and JSON defaults loading
- **Parser** (optional): A `BaseParser` subclass to read model input files
- **Exporter** (optional): A `BaseExporter` subclass to write model output files

**Rationale**: Separating parser and exporter allows flexible model translation workflows (input-only, output-only, or bidirectional).

**PluginConfig Features**:
- Automatic configuration directory discovery (looks for `config/` subdirectory relative to the config class)
- Load default parameters from `config/defaults.json`
- Load file mappings from `config/file_mapping.json`
- Pydantic-based validation and type safety
- Full IDE support for field completion

```{seealso}
See :doc:`../how-tos/plugin-standards` for configuration best practices and standards.
```

#### System Modifier Plugins
System modifiers are functions that post-process a `System` after parsing. They enable:

- Adding components (storage, electrolyzers, etc.)
- Removing or filtering components
- Adding time series from external sources
- Setting constraints or limits
- Modifying attributes based on scenarios

**Rationale**: System modifiers provide a hook for custom logic without requiring parser subclassing. This allows combining base model parsers with application-specific customizations.

**Signature**: `(system: System, **kwargs) -> System`

The flexible `**kwargs` allows modifiers to accept optional context:
- `config`: Configuration object
- `parser`: Parser instance that built the system
- Custom parameters specific to the modifier

#### Filter Plugins
Filters are data transformation functions applied during parsing. They operate on raw data (typically `polars.LazyFrame` or `dict`) before component creation.

**Rationale**: Filters provide reusable data transformations that can be shared across parsers and models. Common operations (rename columns, filter rows, convert units) become first-class, discoverable functions.

**Signature**: `(data: Any, **kwargs) -> Any`

The flexible signature supports polymorphic filters that work with multiple data types.

### 2. Plugin Registry (PluginManager)

The `PluginManager` is a **singleton** that maintains centralized registries for all plugin types.

#### Singleton Pattern
Why singleton?
- **Global registry**: All parts of an application see the same registered plugins
- **Initialization once**: External plugins discovered only once at startup
- **Consistent state**: No risk of registry inconsistency across instances

#### Storage Structure
```python
_registry: dict[str, PluginComponent]           # Model plugins by name
_modifier_registry: dict[str, SystemModifier]   # System modifiers by name
_filter_registry: dict[str, Callable]           # Filters by name
```

#### Registration Methods
Plugins register using class methods (available before instantiation):

```python
@classmethod
def register_model_plugin(cls, name, config, parser, exporter) -> None
@classmethod
def register_system_modifier(cls, name) -> Callable  # Decorator
@classmethod
def register_filter(cls, name) -> Callable           # Decorator
```

**Rationale**: Class methods allow registration before the singleton is instantiated, which is important for external plugins discovered via entry points.

#### Discovery Methods
Applications query the registry to discover available plugins:

```python
@property
def registered_parsers(self) -> list[str]
@property
def registered_exporters(self) -> list[str]
@property
def registered_modifiers(self) -> list[str]
@property
def registered_filters(self) -> list[str]
```

### 3. External Plugin Discovery

The plugin system uses Python's **entry point** mechanism for automatic plugin discovery.

#### Entry Point Group: `r2x_plugin`

External packages declare entry points in `pyproject.toml`:

```toml
[project.entry-points.r2x_plugin]
my_model = "my_package.plugins:register_plugins"
```

#### Discovery Process

When `PluginManager()` is first instantiated:

1. Scan for entry points in the `r2x_plugin` group
2. Load each entry point (imports the module and gets the function)
3. Call the registration function
4. Log success or failure for each plugin

**Rationale**: Entry points are a standard Python mechanism for plugin discovery. They enable:
- Automatic discovery of installed packages
- No explicit imports required in r2x-core
- Clean separation between core and plugins
- Standard pip installation workflow

## Data Flow

### Parsing Workflow with Plugins

```
1. Application loads parser class
   PluginManager.load_parser("reeds") → ReEDSParser

2. Parser initialization
   parser = ReEDSParser(config, data_store)

3. Build system
   system = parser.build_system()
   ├── parser.build_system_components()
   │   ├── read_data_file() → raw data
   │   ├── apply filters from registry
   │   └── create_component() → add to system
   └── parser.build_time_series()

4. Apply system modifiers
   modifier = PluginManager.get_system_modifier("add_storage")
   system = modifier(system, config=config, parser=parser)

5. Export
   Exporter = PluginManager.load_exporter("plexos")
   exporter = Exporter(config, system, data_store)
   exporter.export()
```

### Filter Application

Filters are applied within parsers during data processing:

```
Raw Data → Filter 1 → Filter 2 → ... → Filter N → Components
```

Example:
```
CSV File
  → rename_columns({"gen_name": "name"})
  → filter_by_year(2030)
  → convert_units("capacity", 1000)
  → create_component(Generator, row)
```

## Design Decisions

### Why Not Abstract Base Classes for Plugins?

We use **registration** rather than requiring plugins to inherit from abstract base classes.

**Advantages**:
- Plugins can be plain functions (modifiers, filters)
- No inheritance complexity
- Works with third-party code that can't be modified
- Simpler mental model

### Why Flexible Signatures?

System modifiers and filters use flexible `**kwargs` rather than strict typed signatures.

**Rationale**:
- Different modifiers need different context (some need parser, some don't)
- Filters may work with different data types (LazyFrame, dict, etc.)
- Easier to extend without breaking existing plugins
- Applications can pass custom parameters

**Trade-off**: Less type safety, but more flexibility. We rely on documentation and runtime checking.

### Why Separate Model Plugins from Modifiers?

Model plugins (parser/exporter) are **model-specific**, while modifiers are often **cross-cutting** (work with any model).

**Example**:
- `ReEDSParser` is specific to ReEDS input format
- `add_storage` modifier can work with systems from any parser

This separation allows:
- Mixing and matching: ReEDS parser + storage modifier + PLEXOS exporter
- Reusing modifiers across models
- Installing only needed components

### Why Allow Plugins Without Parser or Exporter?

Some plugins only provide modifiers and filters without model I/O.

**Use case**: A package like `r2x-storage-plugins` might only provide:
- `add_battery_storage` modifier
- `add_pumped_hydro` modifier
- `storage_aggregation` filter

This is valid because the plugin adds value without defining a complete model.

## CLI Integration Pattern

While r2x-core provides the registry, applications build CLIs on top of it:

```python
# Application's CLI (not in r2x-core)
def build_cli():
    manager = PluginManager()

    # Dynamic model selection based on installed plugins
    parser.add_argument(
        "--input-model",
        choices=manager.registered_parsers,  # Discovered dynamically
        required=True
    )

    # Dynamic config fields based on selected model
    plugin = manager.get_plugin(args.input_model)
    for field in plugin.config.model_fields:
        # Add CLI argument for each config field
        ...
```

**Workflow**:
```bash
# User installs plugins
pip install r2x-reeds r2x-plexos

# CLI automatically discovers them
r2x run --input-model=reeds --output-model=plexos ...
```

## Extension Points

The plugin system provides several extension points:

### 1. Parser Hooks
Parsers can override hooks for custom behavior:
- `validate_inputs()`: Pre-parsing validation
- `build_system_components()`: Component creation (required)
- `build_time_series()`: Time series attachment (required)
- `post_process_system()`: Post-parsing modifications

### 2. System Modifiers
Applications can chain modifiers for complex workflows:
```python
for modifier_name in ["add_storage", "emission_cap", "electrolyzers"]:
    modifier = manager.get_system_modifier(modifier_name)
    system = modifier(system, ...)
```

### 3. Filter Composition
Filters can be composed into pipelines:
```python
filters = [
    ("rename_columns", {...}),
    ("filter_by_year", {...}),
    ("convert_units", {...}),
]
for name, kwargs in filters:
    filter_func = manager.get_filter(name)
    data = filter_func(data, **kwargs)
```

## Security Considerations

### Trusted Plugins Only

The plugin system executes code from external packages. Only install plugins from **trusted sources**.

### Entry Point Validation

PluginManager validates entry points during discovery:
- Catches and logs errors if a plugin fails to load
- Continues initialization even if one plugin fails
- Provides clear error messages for debugging

### No Sandboxing

Plugins run with full application privileges. There is **no sandboxing** or permission system.

**Mitigation**: Document clearly which plugins are official/trusted, and encourage users to review plugin code before installation.

## Future Considerations

### Plugin Dependencies

Currently, plugins can have dependencies on each other implicitly (e.g., a modifier might expect certain filters to be registered). Future versions could:
- Add explicit dependency declaration
- Validate plugin dependencies at registration
- Provide dependency resolution

### Plugin Versioning

Future versions could support:
- Version requirements for plugins
- Compatibility checking (plugin API version)
- Migration paths for breaking changes

### Plugin Configuration

Future versions could add:
- Plugin-level configuration
- Enable/disable plugins dynamically
- Plugin priority/ordering for modifiers

## See Also

- :doc:`../how-tos/plugin-registration` : How to register plugins
- :doc:`../how-tos/plugin-usage` : How to use registered plugins
- :doc:`../how-tos/filter-examples` : Filter registry examples
- :doc:`../reference/plugin-api` : Plugin API reference
