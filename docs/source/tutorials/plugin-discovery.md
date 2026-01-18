# Plugin Discovery

Plugins can be automatically discovered and cataloged using ast-grep rules. This
enables:

- Plugin registry generation
- CLI help text generation
- Documentation generation
- Type checking and validation

## Discovery Information

For each plugin, we can extract:

1. **Config Type**: From generic parameter `class MyPlugin(Plugin[MyConfig])`
2. **Implemented Hooks**: From method names (`on_validate`, `on_build`, etc.)
3. **Required Context Fields**: From non-Optional property return types
4. **Config Schema**: Field names, types, defaults, and metadata

## Example: Discovering ReEDSParser

Given this plugin:

```python
from r2x_core import Plugin, PluginContext, PluginConfig, System, DataStore
from rust_ok import Ok, Result

class ReEDSConfig(PluginConfig):
    """Configuration for ReEDS parser."""
    model_year: int
    scenario: str = "base"
    input_folder: str
    skip_buses: bool = False

class ReEDSParser(Plugin[ReEDSConfig]):
    """Parses ReEDS model data."""

    @property
    def config(self) -> ReEDSConfig:
        return self._ctx.config

    @property
    def store(self) -> DataStore:  # Non-Optional = required
        if self._ctx.store is None:
            raise RuntimeError("DataStore required")
        return self._ctx.store

    def on_validate(self) -> Result[None, Exception]:
        if not self.config.input_folder:
            return Err(ValueError("input_folder required"))
        return Ok(None)

    def on_build(self) -> Result[System, Exception]:
        system = System(name=f"reeds_{self.config.model_year}")
        # ... build logic
        return Ok(system)
```

Discovery would extract:

```json
{
  "ReEDSParser": {
    "config_type": "ReEDSConfig",
    "file": "plugins/reeds_parser.py",
    "line": 12,
    "hooks": ["on_validate", "on_build"],
    "required_context": ["config", "store"],
    "accepts_stdin": false,
    "config_schema": {
      "model_year": {
        "type": "int",
        "required": true
      },
      "scenario": {
        "type": "str",
        "required": false,
        "default": "base"
      },
      "input_folder": {
        "type": "str",
        "required": true
      },
      "skip_buses": {
        "type": "bool",
        "required": false,
        "default": false
      }
    }
  }
}
```

## Programmatic Discovery

### Using Plugin Introspection

```python
from r2x_core import Plugin, PluginConfig
from rust_ok import Ok

class MyConfig(PluginConfig):
    value: int

class MyPlugin(Plugin[MyConfig]):
    def on_validate(self):
        return Ok(None)
...
    def on_build(self):
        return Ok(None)

# Get config type
config_type = MyPlugin.get_config_type()
config_type.__name__
'MyConfig'

# Get implemented hooks
hooks = MyPlugin.get_implemented_hooks()
sorted(list(hooks))
['on_build', 'on_validate']
```

### Detecting Capabilities

```python
def get_plugin_capabilities(plugin_class: type[Plugin]) -> list[str]:
    """Infer plugin capabilities from implemented hooks."""
    hooks = plugin_class.get_implemented_hooks()
    capabilities = []

    if 'on_build' in hooks:
        capabilities.append('build')
    if 'on_transform' in hooks:
        capabilities.append('transform')
    if 'on_translate' in hooks:
        capabilities.append('translate')
    if 'on_export' in hooks:
        capabilities.append('export')

    return capabilities

# Usage
caps = get_plugin_capabilities(MyPlugin)
# ['build', 'validate']
```

### Detecting Required Context

```python
import inspect

def get_required_context_fields(plugin_class: type[Plugin]) -> list[str]:
    """Extract required context fields from property return types."""
    required = ['config']  # Always required

    for name in ['store', 'system', 'source_system', 'target_system']:
        try:
            prop = getattr(plugin_class, name)
            if isinstance(prop, property):
                # Check return type annotation
                # Non-Optional return type = required
                # For now, assume all are required if property exists
                required.append(name)
        except AttributeError:
            pass

    return required

# Usage
fields = get_required_context_fields(MyPlugin)
# ['config', 'store', 'system']
```

## ast-grep Rules for Discovery

The following ast-grep rules can be used to discover plugins at scale:

### Rule 1: Find Plugin Classes

```yaml
id: discover-plugin-classes
language: python
severity: info
message: "Plugin class: $CLASS with config $CONFIG"
rule:
  kind: class_definition
  has:
    kind: identifier
    regex: ".*Plugin$"  # Classes ending in 'Plugin'
    stopBy: neighbor
  has:
    kind: argument_list
    has:
      kind: subscript
      pattern: Plugin[$CONFIG]
      stopBy: end
    stopBy: end
```

**Usage:**

```bash
ast-grep scan --rule discover_plugins.yml /path/to/plugins/
```

### Rule 2: Find Implemented Hooks

```yaml
id: discover-plugin-hooks
language: python
severity: info
message: "Hook: $NAME"
rule:
  kind: function_definition
  has:
    kind: identifier
    regex: "^on_(validate|prepare|build|transform|translate|export|cleanup)$"
    stopBy: neighbor
  inside:
    kind: class_definition
    has:
      pattern: Plugin[$_]
      stopBy: end
    stopBy: end
```

### Rule 3: Find Config Classes

```yaml
id: discover-config-classes
language: python
severity: info
message: "Config: $CLASS"
rule:
  kind: class_definition
  has:
    kind: identifier
    regex: ".*Config$"  # Classes ending in 'Config'
    stopBy: neighbor
  has:
    kind: argument_list
    has:
      kind: identifier
      regex: "^PluginConfig$"
      stopBy: end
    stopBy: end
```

### Rule 4: Find Required Context Properties

```yaml
id: discover-required-context
language: python
severity: info
message: "Required context field: $NAME"
rule:
  kind: function_definition
  all:
    # Has @property decorator
    - has:
        kind: decorator
        has:
          kind: identifier
          regex: "^property$"
        stopBy: end
    # Return type is NOT Optional
    - has:
        kind: type
        not:
          any:
            - has:
                pattern: "None"
                stopBy: end
            - has:
                pattern: "Optional[$_]"
                stopBy: end
            - pattern: "$_ | None"
        stopBy: end
    # Inside a Plugin class
    - inside:
        kind: class_definition
        has:
          pattern: Plugin[$_]
          stopBy: end
        stopBy: end
```

## Building a Plugin Registry

Here's a Python script that uses ast-grep to build a plugin registry:

```python
import json
import subprocess
from pathlib import Path
from typing import Any

def discover_plugins(plugin_dir: Path) -> dict[str, Any]:
    """Build a plugin registry using ast-grep."""

    registry = {}

    # Find all plugin classes
    result = subprocess.run([
        "ast-grep", "scan",
        "--inline-rules", """id: find-plugins
language: python
rule:
  kind: class_definition
  has:
    kind: argument_list
    has:
      kind: subscript
      pattern: Plugin[$CONFIG]
      stopBy: end
    stopBy: end""",
        "--json",
        str(plugin_dir)
    ], capture_output=True, text=True)

    if result.returncode != 0:
        return registry

    # Parse results
    for match in json.loads(result.stdout):
        plugin_name = match.get('name', 'Unknown')
        config_type = match.get('config_type', 'Unknown')
        file_path = match.get('file', '')

        # Find implemented hooks for this plugin
        hooks = []  # Would extract with another ast-grep call

        # Find required context fields
        required_ctx = ['config']  # Would extract with another ast-grep call

        registry[plugin_name] = {
            'config_type': config_type,
            'file': file_path,
            'hooks': hooks,
            'required_context': required_ctx,
        }

    return registry

# Usage
plugins = discover_plugins(Path('plugins/'))
print(json.dumps(plugins, indent=2))
```

## Integration with CLI

The discovery system enables auto-generated CLI help:

```
$ python -m cli plugins list

Discovered Plugins:
  ReEDSParser
    Config: ReEDSConfig
    Hooks: on_validate, on_build
    Requires: config, store
    Accepts stdin: No

  PlexosExporter
    Config: PlexosExportConfig
    Hooks: on_export
    Requires: config, system, store
    Accepts stdin: Yes

$ python -m cli run ReEDSParser --model-year 2030 --input-folder /data

$ python -m cli run PlexosExporter --output-dir /export < system.json
```
