# Upgrade System

For complete API documentation of upgrade classes, see {doc}`api`.

## Quick Reference

- {py:class}`~r2x_core.UpgradeContext` - Upgrade execution context enum
- {py:class}`~r2x_core.UpgradeStep` - Upgrade step definition
- {py:class}`~r2x_core.UpgradeResult` - Upgrade result with rollback
- {py:func}`~r2x_core.apply_upgrade` - Apply single upgrade
- {py:func}`~r2x_core.apply_upgrades` - Apply multiple upgrades
- {py:func}`~r2x_core.apply_upgrades_with_rollback` - Apply upgrades with rollback capability

## Overview

The upgrade system provides a flexible framework for migrating data and system objects between versions. It supports:

- **Data upgrades**: Transform raw configuration files and dictionaries
- **System upgrades**: Modify System instances and components
- **Version-aware**: Automatic version checking and comparison
- **Rollback support**: All-or-nothing rollback on failure
- **Priority ordering**: Control upgrade execution order
- **Context filtering**: Target specific upgrade phases

## Upgrade Contexts

Upgrades execute in different contexts depending on when they run:

```python
from r2x_core import UpgradeContext

# Before System creation (raw data)
UpgradeContext.DATA      # Configuration files, dictionaries

# After System creation (model instances)
UpgradeContext.SYSTEM    # System objects, components

# Can run in either context
UpgradeContext.BOTH      # Flexible upgrades
```

## Usage Examples

### Basic Data Upgrade

Create an upgrade step for raw configuration data:

```python
from r2x_core import UpgradeStep, UpgradeContext, apply_upgrade
from r2x_core import SemanticVersioningStrategy

# Define upgrade function
def upgrade_to_v2(data: dict) -> dict:
    """Upgrade data from v1 to v2."""
    data["version"] = "2.0.0"
    data["new_field"] = "default_value"
    # Rename old field
    if "old_name" in data:
        data["new_name"] = data.pop("old_name")
    return data

# Create upgrade step
step = UpgradeStep(
    name="upgrade_config_to_v2",
    func=upgrade_to_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    context=UpgradeContext.DATA,
    upgrade_type="data"
)

# Apply upgrade
data = {"version": "1.0.0", "old_name": "test"}
upgraded_data, was_applied = apply_upgrade(data, step)

if was_applied:
    print(f"Upgraded to {step.target_version}")
```

### System Upgrade

Modify System instances after creation:

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

def upgrade_system_to_v2(system: System) -> System:
    """Upgrade System components."""
    # Add metadata
    system.metadata["upgraded"] = True

    # Modify components
    for bus in system.get_components(ACBus):
        bus.description = f"Upgraded: {bus.description}"

    # Update system version
    system.metadata["version"] = "2.0.0"
    return system

step = UpgradeStep(
    name="upgrade_system_to_v2",
    func=upgrade_system_to_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

### Multiple Upgrades with Priority

Apply multiple upgrades in order:

```python
from r2x_core import apply_upgrades, UpgradeContext
from r2x_core import SemanticVersioningStrategy

strategy = SemanticVersioningStrategy()

# Define upgrade steps with priorities
steps = [
    UpgradeStep(
        name="upgrade_v1_to_v2",
        func=upgrade_to_v2,
        target_version="2.0.0",
        versioning_strategy=strategy,
        priority=100,  # Runs first
        context=UpgradeContext.DATA
    ),
    UpgradeStep(
        name="upgrade_v2_to_v3",
        func=upgrade_to_v3,
        target_version="3.0.0",
        versioning_strategy=strategy,
        priority=200,  # Runs second
        context=UpgradeContext.DATA
    ),
]

# Apply all applicable upgrades
data = {"version": "1.0.0"}
final_data, applied = apply_upgrades(
    data,
    steps,
    context=UpgradeContext.DATA,
    upgrade_type="data"
)

print(f"Applied {len(applied)} upgrades: {applied}")
```

### Upgrades with Rollback

Apply upgrades with automatic rollback on failure:

```python
from r2x_core import apply_upgrades_with_rollback, UpgradeContext

# Apply upgrades and get result with rollback capability
result = apply_upgrades_with_rollback(
    data,
    steps,
    context=UpgradeContext.DATA,
    upgrade_type="data",
    stop_on_error=True  # Stop and rollback on first error
)

# Validate upgraded data
if validate_data(result.current_data):
    # Success - use upgraded data
    final_data = result.current_data
    print(f"Applied: {result.applied_steps}")
else:
    # Validation failed - rollback to original
    print("Validation failed, rolling back")
    final_data = result.rollback()
```

### Version Constraints

Specify minimum and maximum version requirements:

```python
from r2x_core import UpgradeStep
from r2x_core import SemanticVersioningStrategy

step = UpgradeStep(
    name="upgrade_v2_to_v3",
    func=upgrade_to_v3,
    target_version="3.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    min_version="2.0.0",  # Only applies if >= v2.0.0
    max_version="2.9.9",  # Only applies if <= v2.9.9
    context=UpgradeContext.DATA
)

# Skipped if current version < 2.0.0 or > 2.9.9
```

## Plugin Integration

Register upgrade steps with the plugin system:

```python
from r2x_core import PluginManager, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

# Define upgrade function
def upgrade_my_model_v2(data: dict) -> dict:
    """Upgrade MyModel configuration to v2."""
    data["version"] = "2.0.0"
    data["new_setting"] = True
    return data

# Create upgrade step
step = UpgradeStep(
    name="my_model_v2_upgrade",
    func=upgrade_my_model_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    priority=100,
    context=UpgradeContext.DATA,
    upgrade_type="data"
)

# Register with plugin
PluginManager.register_upgrade_step("my_model", step)

# Use in DataStore loading
from r2x_core import DataStore

# Upgrades applied automatically
store = DataStore.from_json(
    "config.json",
    folder="/data",
    upgrader="my_model"  # Applies my_model upgrade steps
)
```

## Automatic Upgrades

### DataStore Upgrades

Data upgrades apply automatically during DataStore loading:

```python
from r2x_core import DataStore, PluginManager

# Register upgrade steps first
PluginManager.register_upgrade_step("my_plugin", data_upgrade_step)

# Load with automatic upgrades
store = DataStore.from_json(
    "mappings.json",
    folder="/data",
    upgrader="my_plugin"  # Triggers data upgrades
)

# Data files are upgraded before loading
```

### System Upgrades

System upgrades apply automatically during System deserialization:

```python
from r2x_core import System, PluginManager

# Register system upgrade steps
PluginManager.register_upgrade_step("my_plugin", system_upgrade_step)

# Load with automatic system upgrades
system = System.from_json(
    "system.json",
    upgrader="my_plugin"  # Triggers system upgrades
)

# System is upgraded after deserialization
```

## Advanced Usage

### Multi-Phase Upgrades

Combine data and system upgrades:

```python
from r2x_core import UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

strategy = SemanticVersioningStrategy()

# Phase 1: Data upgrade (before System creation)
data_step = UpgradeStep(
    name="upgrade_config_v2",
    func=upgrade_config_to_v2,
    target_version="2.0.0",
    versioning_strategy=strategy,
    priority=100,
    context=UpgradeContext.DATA,
    upgrade_type="data"
)

# Phase 2: System upgrade (after System creation)
system_step = UpgradeStep(
    name="upgrade_system_v2",
    func=upgrade_system_to_v2,
    target_version="2.0.0",
    versioning_strategy=strategy,
    priority=100,
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)

# Register both
PluginManager.register_upgrade_step("my_model", data_step)
PluginManager.register_upgrade_step("my_model", system_step)
```

### Conditional Upgrades

Implement conditional logic in upgrade functions:

```python
def smart_upgrade(data: dict) -> dict:
    """Apply conditional upgrades."""
    data["version"] = "2.0.0"

    # Conditional transformations
    if "legacy_field" in data:
        # Migrate legacy format
        data["modern_field"] = transform_legacy(data.pop("legacy_field"))

    if data.get("feature_flag"):
        # Feature-specific upgrade
        data["new_feature_config"] = initialize_feature()

    return data
```

### Error Handling

Control error handling behavior:

```python
from r2x_core import apply_upgrades_with_rollback

# Stop on first error and rollback
result = apply_upgrades_with_rollback(
    data,
    steps,
    stop_on_error=True  # Rollback on any error
)

# Continue on errors (default)
result = apply_upgrades_with_rollback(
    data,
    steps,
    stop_on_error=False  # Skip failed steps, continue with others
)

print(f"Applied: {result.applied_steps}")
```

## Upgrade Result

The `UpgradeResult` class tracks upgrade state:

```python
from r2x_core import apply_upgrades_with_rollback

result = apply_upgrades_with_rollback(data, steps)

# Access properties
print(f"Original: {result.original_data}")
print(f"Current: {result.current_data}")
print(f"Applied steps: {result.applied_steps}")

# Rollback to original state
if not validate(result.current_data):
    restored = result.rollback()
    print("Rolled back to original state")
```

## Best Practices

### Version Your Upgrades

Always include version information in your upgrade functions:

```python
def upgrade_to_v2(data: dict) -> dict:
    """Upgrade data to version 2.0.0."""
    data["version"] = "2.0.0"  # Set target version
    # ... transformation logic
    return data
```

### Use Priority for Ordering

Control execution order with priority values:

```python
# Lower numbers run first
early_step = UpgradeStep(..., priority=50)   # Runs first
middle_step = UpgradeStep(..., priority=100)  # Runs second
late_step = UpgradeStep(..., priority=200)    # Runs last
```

### Test with Rollback

Always test upgrade logic with rollback:

```python
# Test upgrade with rollback safety
result = apply_upgrades_with_rollback(test_data, steps)

# Verify upgrade worked
assert validate(result.current_data)

# Test rollback
restored = result.rollback()
assert restored == test_data  # Original preserved
```

### Document Breaking Changes

Document version requirements and breaking changes:

```python
step = UpgradeStep(
    name="breaking_change_v3",
    func=upgrade_with_breaking_changes,
    target_version="3.0.0",
    versioning_strategy=strategy,
    min_version="2.5.0",  # Requires at least 2.5.0
    context=UpgradeContext.DATA
)
# Document: "Breaking change in v3.0.0 - requires v2.5.0+"
```

## See Also

- {doc}`versioning` - Versioning strategies
- {doc}`plugins` - Plugin system integration
- {doc}`../how-tos/upgrade-data` - Upgrade data guide
- {doc}`../how-tos/upgrade-systems` - Upgrade systems guide
- {doc}`api` - Complete API documentation
