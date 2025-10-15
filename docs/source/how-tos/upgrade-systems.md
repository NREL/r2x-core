# ... create a SYSTEM upgrader

```python
from pathlib import Path
from r2x_core.upgrader import DataUpgrader, UpgradeType
from r2x_core.versioning import SemanticVersioningStrategy
from r2x_core import System

class MyModelUpgrader(DataUpgrader):
    """Upgrader for my_model plugin."""

    strategy = SemanticVersioningStrategy(version_field="metadata.version")

    @staticmethod
    def detect_version(folder: Path) -> str | None:
        # For SYSTEM upgrades, version typically in system metadata
        return None
```

# ... register SYSTEM upgrade steps

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def upgrade_system_to_v2(system: System) -> System:
    """Upgrade System to version 2."""
    system.metadata["version"] = "2.0.0"
    system.metadata["upgraded_at"] = "2024-10-13"

    from infrasys import Component
    for component in system.get_components(Component):
        component.ext["upgraded"] = True

    return system
```

# ... use SYSTEM upgrader

```python
from r2x_core import System, PluginManager

# Register plugin with upgrader
PluginManager.register_model_plugin(
    name="my_model",
    config=MyModelConfig,
    parser=MyModelParser,
    upgrader=MyModelUpgrader
)

# System upgrades applied automatically during loading
system = System.from_json(
    "system.json",
    upgrader=MyModelUpgrader
)
```

# ... modify component properties

```python
from infrasys import ACBus, Generator

@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def upgrade_components(system: System) -> System:
    """Upgrade component properties."""
    system.metadata["version"] = "2.0.0"

    # Update all buses
    for bus in system.get_components(ACBus):
        bus.base_voltage *= 1.0  # Ensure float type
        bus.ext["zone"] = bus.ext.get("area", "default")

    # Update all generators
    for gen in system.get_components(Generator):
        gen.active_power_limits.max *= 1.05  # 5% capacity increase
        gen.ext["upgraded_capacity"] = True

    return system
```

# ... combine FILE and SYSTEM upgrades

```python
from pathlib import Path
from r2x_core.upgrader import DataUpgrader, UpgradeType
from r2x_core import System

class MyModelUpgrader(DataUpgrader):
    strategy = SemanticVersioningStrategy()

    @staticmethod
    def detect_version(folder: Path) -> str | None:
        version_file = folder / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return None


# FILE upgrade runs during DataStore.from_json
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
    priority=100
)
def upgrade_data_v2(folder: Path) -> Path:
    """Upgrade raw data files."""
    config_file = folder / "config.json"
    # Update configuration file
    return folder


# SYSTEM upgrade runs during System.from_json
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM,
    priority=100
)
def upgrade_system_v2(system: System) -> System:
    """Upgrade system object."""
    system.metadata["version"] = "2.0.0"
    # Apply system-level transformations
    return system
```

# ... update system metadata

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def update_metadata(system: System) -> System:
    """Update system metadata structure."""
    # Add new metadata fields
    system.metadata["version"] = "2.0.0"
    system.metadata["upgrade_date"] = "2024-10-13"

    # Restructure existing metadata
    if "old_field" in system.metadata:
        system.metadata["new_field"] = system.metadata.pop("old_field")

    # Add computed fields
    system.metadata["component_count"] = len(system.get_components())

    return system
```

# ... add new components during upgrade

```python
from infrasys import ACBus, BatteryStorage

@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def add_storage_devices(system: System) -> System:
    """Add battery storage to each bus."""
    system.metadata["version"] = "2.0.0"

    for bus in system.get_components(ACBus):
        storage = BatteryStorage(
            name=f"battery_{bus.name}",
            bus=bus,
            active_power=100.0,
            energy_capacity=400.0
        )
        system.add_component(storage)

    return system
```

# ... remove deprecated components

```python
from infrasys import Component

@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def remove_deprecated_components(system: System) -> System:
    """Remove deprecated component types."""
    system.metadata["version"] = "2.0.0"

    # Remove components marked as deprecated
    components_to_remove = [
        comp for comp in system.get_components(Component)
        if comp.ext.get("deprecated", False)
    ]

    for comp in components_to_remove:
        system.remove_component(comp)

    return system
```

# ... update time series data

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def upgrade_time_series(system: System) -> System:
    """Update time series metadata."""
    system.metadata["version"] = "2.0.0"

    from infrasys import Component
    for component in system.get_components(Component):
        # Update time series metadata for each component
        for ts in system.get_time_series(component):
            ts.metadata["upgraded"] = True
            ts.metadata["version"] = "2.0.0"

    return system
```

# ... migrate component relationships

```python
from infrasys import Generator, ACBus

@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def update_relationships(system: System) -> System:
    """Update component relationships."""
    system.metadata["version"] = "2.0.0"

    # Update generator bus references
    for gen in system.get_components(Generator):
        old_bus_name = gen.ext.get("old_bus_id")
        if old_bus_name:
            new_bus = system.get_component_by_name(ACBus, old_bus_name)
            if new_bus:
                gen.bus = new_bus
                del gen.ext["old_bus_id"]

    return system
```

# ... order SYSTEM upgrades with priority

```python
# Priority 50 runs first
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM,
    priority=50
)
def prepare_system(system: System) -> System:
    """Prepare system for upgrades."""
    system.metadata["version"] = "2.0.0"
    system.metadata["upgrading"] = True
    return system

# Priority 100 runs second
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM,
    priority=100
)
def main_system_upgrade(system: System) -> System:
    """Main system transformations."""
    # Perform main upgrades
    return system

# Priority 150 runs third
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM,
    priority=150
)
def finalize_system(system: System) -> System:
    """Finalize system after upgrades."""
    system.metadata["upgrading"] = False
    system.metadata["upgrade_complete"] = True
    return system
```

# ... validate system after upgrade

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM,
    priority=200  # Run last
)
def validate_system(system: System) -> System:
    """Validate system after upgrade."""
    # Check metadata
    if system.metadata.get("version") != "2.0.0":
        raise ValueError("Version not updated")

    # Validate component count
    from infrasys import Component
    if len(system.get_components(Component)) == 0:
        raise ValueError("No components in system")

    # Validate required components exist
    from infrasys import ACBus
    if len(system.get_components(ACBus)) == 0:
        raise ValueError("No buses in system")

    return system
```
