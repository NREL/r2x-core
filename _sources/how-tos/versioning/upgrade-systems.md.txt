# Create a SYSTEM Upgrader

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
        return None
```

# Register SYSTEM Upgrade Steps

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def upgrade_system_to_v2(system: System) -> System:
    """Upgrade System to version 2."""
    system.metadata["version"] = "2.0.0"

    from infrasys import Component
    for component in system.get_components(Component):
        component.ext["upgraded"] = True

    return system
```

# Modify Component Properties

```python
from infrasys import ACBus, Generator

@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM
)
def upgrade_components(system: System) -> System:
    """Upgrade component properties."""
    system.metadata["version"] = "2.0.0"

    for bus in system.get_components(ACBus):
        bus.base_voltage *= 1.0

    for gen in system.get_components(Generator):
        gen.active_power_limits.max *= 1.05
        gen.ext["upgraded_capacity"] = True

    return system
```

# Combine FILE And SYSTEM Upgrades

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

@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
)
def upgrade_data_v2(folder: Path) -> Path:
    """Upgrade raw data files."""
    config_file = folder / "config.json"
    # Update configuration file
    return folder

@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.SYSTEM,
)
def upgrade_system_v2(system: System) -> System:
    """Upgrade system object."""
    system.metadata["version"] = "2.0.0"
    return system
```
