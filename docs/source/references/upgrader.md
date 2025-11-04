# Upgrade System

For complete API documentation of upgrade classes, see {doc}`api`.

## Quick Reference

- {py:class}`~r2x_core.UpgradeStep` - Upgrade step definition
- {py:class}`~r2x_core.UpgradeType` - Upgrade type enum (DATA or SYSTEM)
- {py:func}`~r2x_core.run_datafile_upgrades` - Execute file-based data upgrades
- {py:func}`~r2x_core.run_system_upgrades` - Execute system object upgrades
- {py:func}`~r2x_core.run_upgrade_step` - Execute a single upgrade step

## Overview

The upgrade system provides a flexible framework for migrating data and system objects between versions. It supports:

- **Data upgrades**: Transform raw configuration files and dictionaries
- **System upgrades**: Modify System instances and components
- **Version-aware**: Automatic version checking and comparison
- **Rollback support**: All-or-nothing rollback on failure
- **Priority ordering**: Control upgrade execution order
- **Context filtering**: Target specific upgrade phases

## Upgrade Types

Two types of upgrades are supported:

- **DATA**: Upgrades applied to raw data files before System creation
- **SYSTEM**: Upgrades applied to System objects after creation

## Usage Examples

### Define an Upgrade Step

Create an upgrade step for data transformation:

```python
from r2x_core import UpgradeStep, UpgradeType
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
    upgrade_type=UpgradeType.DATA
)
```

### System Upgrade

Modify System instances after creation:

```python
from r2x_core import System, UpgradeStep, UpgradeType
from r2x_core import SemanticVersioningStrategy
from infrasys.components import ACBus

def upgrade_system_to_v2(system: System) -> System:
    """Upgrade System components."""
    # Modify components
    for bus in system.get_components(ACBus):
        bus.description = f"Upgraded: {bus.description}"
    return system

step = UpgradeStep(
    name="upgrade_system_to_v2",
    func=upgrade_system_to_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    upgrade_type=UpgradeType.SYSTEM
)
```

### Apply Data Upgrades

Execute file-based data upgrades:

```python
from r2x_core import run_datafile_upgrades

# Define upgrade steps
steps = [step1, step2]  # From previous examples

# Apply upgrades to raw data
data = {"version": "1.0.0", "old_name": "test"}
upgraded_data = run_datafile_upgrades(data, steps)
```

### Apply System Upgrades

Execute system object upgrades:

```python
from r2x_core import run_system_upgrades, System

# Define system upgrade steps
steps = [system_step]  # From previous example

# Apply upgrades to System
system = System(100.0, name="Grid")
upgraded_system = run_system_upgrades(system, steps)
```

## See Also

- {doc}`versioning` - Versioning strategies
- {doc}`plugins` - Plugin system integration
- {doc}`../how-tos/upgrade-data` - Upgrade data guide
- {doc}`../how-tos/upgrade-systems` - Upgrade systems guide
- {doc}`api` - Complete API documentation
