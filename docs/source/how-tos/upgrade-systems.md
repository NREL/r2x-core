# ... upgrade System instances

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

def upgrade_system_to_v2(system: System) -> System:
    """Upgrade System to version 2."""
    # Update system metadata
    system.metadata["version"] = "2.0.0"
    system.metadata["upgraded_at"] = "2024-10-13"

    # Modify components
    from infrasys import Component
    for component in system.get_components(Component):
        component.ext["upgraded"] = True

    return system

step = UpgradeStep(
    name="system_v2_upgrade",
    func=upgrade_system_to_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

# ... modify components during upgrade

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy
from infrasys import ACBus, Generator

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

step = UpgradeStep(
    name="component_upgrade_v2",
    func=upgrade_components,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

# ... register system upgrades

```python
from r2x_core import PluginManager, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy, System

def upgrade_my_model_system(system: System) -> System:
    """System-level upgrade for my_model."""
    system.metadata["version"] = "2.0.0"
    system.metadata["model_type"] = "upgraded"
    return system

# Register system upgrade
step = UpgradeStep(
    name="my_model_system_v2",
    func=upgrade_my_model_system,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)

PluginManager.register_upgrade_step("my_model", step)

# Automatically applied during System loading
system = System.from_json(
    "system.json",
    upgrader="my_model"  # Triggers system upgrade
)
```

# ... combine data and system upgrades

```python
from r2x_core import UpgradeStep, UpgradeContext, PluginManager
from r2x_core import SemanticVersioningStrategy, System

strategy = SemanticVersioningStrategy()

# Phase 1: Data upgrade (before System creation)
def upgrade_data_v2(data: dict) -> dict:
    data["version"] = "2.0.0"
    data["new_config"] = {"solver": "default"}
    return data

data_step = UpgradeStep(
    name="data_upgrade_v2",
    func=upgrade_data_v2,
    target_version="2.0.0",
    versioning_strategy=strategy,
    priority=100,
    context=UpgradeContext.DATA,
    upgrade_type="data"
)

# Phase 2: System upgrade (after System creation)
def upgrade_system_v2(system: System) -> System:
    system.metadata["version"] = "2.0.0"
    # Apply system-level transformations
    return system

system_step = UpgradeStep(
    name="system_upgrade_v2",
    func=upgrade_system_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    priority=100,
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)

# Register both phases
PluginManager.register_upgrade_step("my_model", data_step)
PluginManager.register_upgrade_step("my_model", system_step)
```

# ... update system base power

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy
from infrasys import Component

def update_base_power(system: System) -> System:
    """Update system base power and component values."""
    old_base = system.base_power
    new_base = 100.0  # MVA

    system.base_power = new_base
    ratio = new_base / old_base

    # Scale per-unit values
    for component in system.get_components(Component):
        if hasattr(component, '_system_base'):
            component._system_base = new_base

    system.metadata["version"] = "2.0.0"
    system.metadata["base_power_updated"] = True

    return system

step = UpgradeStep(
    name="base_power_upgrade",
    func=update_base_power,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

# ... add new component types

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy
from infrasys import ACBus, StorageDevice

def add_storage_components(system: System) -> System:
    """Add storage to all buses."""
    system.metadata["version"] = "2.0.0"

    for bus in system.get_components(ACBus):
        # Create storage device
        storage = StorageDevice(
            name=f"Storage_{bus.name}",
            bus=bus,
            capacity=100.0,  # MWh
            efficiency=0.95
        )
        system.add_component(storage)

    system.metadata["storage_added"] = True
    return system

step = UpgradeStep(
    name="add_storage_v2",
    func=add_storage_components,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

# ... migrate component extensions

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy
from infrasys import Component

def migrate_extensions(system: System) -> System:
    """Migrate component extension data."""
    system.metadata["version"] = "2.0.0"

    for component in system.get_components(Component):
        ext = component.ext

        # Migrate old extension format
        if "old_metadata" in ext:
            metadata = ext.pop("old_metadata")
            ext["metadata"] = {
                "source": metadata.get("src", "unknown"),
                "created": metadata.get("timestamp"),
                "legacy": True
            }

        # Add new extension fields
        ext.setdefault("version", "2.0.0")
        ext.setdefault("validated", False)

    return system

step = UpgradeStep(
    name="migrate_extensions_v2",
    func=migrate_extensions,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

# ... filter and modify specific components

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy
from infrasys import Generator

def upgrade_renewable_generators(system: System) -> System:
    """Upgrade only renewable generators."""
    system.metadata["version"] = "2.0.0"

    # Filter renewable generators
    def is_renewable(gen: Generator) -> bool:
        fuel_type = gen.ext.get("fuel_type", "")
        return fuel_type in ["solar", "wind", "hydro"]

    renewables = list(system.get_components(
        Generator,
        filter_func=is_renewable
    ))

    # Upgrade renewable properties
    for gen in renewables:
        gen.ext["renewable"] = True
        gen.ext["priority"] = "high"
        # Update capacity factor
        if "capacity_factor" in gen.ext:
            gen.ext["capacity_factor"] *= 1.1  # 10% improvement

    system.metadata["renewables_upgraded"] = len(renewables)
    return system

step = UpgradeStep(
    name="upgrade_renewables_v2",
    func=upgrade_renewable_generators,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

# ... handle system validation during upgrade

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

def validate_and_upgrade(system: System) -> System:
    """Upgrade with validation checks."""
    # Pre-upgrade validation
    from infrasys import ACBus
    buses = list(system.get_components(ACBus))
    if not buses:
        raise ValueError("System has no buses")

    # Apply upgrades
    system.metadata["version"] = "2.0.0"

    for bus in buses:
        # Validate before modification
        if bus.base_voltage <= 0:
            raise ValueError(f"Invalid base voltage for {bus.name}")

        # Update
        bus.ext["validated"] = True

    # Post-upgrade validation
    assert system.metadata["version"] == "2.0.0"

    return system

step = UpgradeStep(
    name="validated_upgrade_v2",
    func=validate_and_upgrade,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

# ... access system time series during upgrade

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

def upgrade_time_series(system: System) -> System:
    """Update time series metadata."""
    system.metadata["version"] = "2.0.0"

    # Access time series store
    ts_manager = system.time_series_manager

    # Update time series metadata
    for ts_metadata in ts_manager.list_time_series():
        # Add upgrade markers
        ts_metadata["upgraded"] = True
        ts_metadata["upgrade_version"] = "2.0.0"

    system.metadata["time_series_upgraded"] = True
    return system

step = UpgradeStep(
    name="time_series_upgrade_v2",
    func=upgrade_time_series,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```

# ... create conditional system upgrades

```python
from r2x_core import System, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

def conditional_system_upgrade(system: System) -> System:
    """Apply conditional upgrades based on system properties."""
    system.metadata["version"] = "2.0.0"

    # Check system features
    has_storage = system.metadata.get("has_storage", False)
    has_renewables = system.metadata.get("has_renewables", False)

    if has_storage:
        # Storage-specific upgrades
        from infrasys import StorageDevice
        for storage in system.get_components(StorageDevice):
            storage.ext["optimized"] = True

    if has_renewables:
        # Renewable-specific upgrades
        from infrasys import Generator
        for gen in system.get_components(Generator):
            if gen.ext.get("fuel_type") in ["solar", "wind"]:
                gen.ext["renewable_upgraded"] = True

    return system

step = UpgradeStep(
    name="conditional_upgrade_v2",
    func=conditional_system_upgrade,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(
        version_field="metadata.version"
    ),
    context=UpgradeContext.SYSTEM,
    upgrade_type="system"
)
```
