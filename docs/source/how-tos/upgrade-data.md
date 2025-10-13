# ... create a simple upgrade

```python
from r2x_core import UpgradeStep, UpgradeContext, apply_upgrade
from r2x_core import SemanticVersioningStrategy

# Define upgrade function
def upgrade_to_v2(data: dict) -> dict:
    """Upgrade configuration from v1 to v2."""
    data["version"] = "2.0.0"
    data["new_field"] = "default"
    return data

# Create upgrade step
step = UpgradeStep(
    name="upgrade_v1_to_v2",
    func=upgrade_to_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    context=UpgradeContext.DATA
)

# Apply upgrade
old_data = {"version": "1.0.0", "name": "test"}
new_data, applied = apply_upgrade(old_data, step)

if applied:
    print(f"Upgraded to {new_data['version']}")
```

# ... migrate data structure

```python
from r2x_core import UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

def restructure_config(data: dict) -> dict:
    """Restructure configuration for v2."""
    data["version"] = "2.0.0"

    # Rename fields
    if "old_name" in data:
        data["new_name"] = data.pop("old_name")

    # Nest related fields
    if "host" in data and "port" in data:
        data["connection"] = {
            "host": data.pop("host"),
            "port": data.pop("port")
        }

    # Add defaults for new fields
    data.setdefault("timeout", 30)
    data.setdefault("retry_count", 3)

    return data

step = UpgradeStep(
    name="restructure_v2",
    func=restructure_config,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    context=UpgradeContext.DATA
)
```

# ... apply multiple upgrades

```python
from r2x_core import apply_upgrades, UpgradeContext
from r2x_core import SemanticVersioningStrategy

strategy = SemanticVersioningStrategy()

# Define upgrade chain
steps = [
    UpgradeStep(
        name="v1_to_v2",
        func=upgrade_to_v2,
        target_version="2.0.0",
        versioning_strategy=strategy,
        priority=100,
        context=UpgradeContext.DATA
    ),
    UpgradeStep(
        name="v2_to_v3",
        func=upgrade_to_v3,
        target_version="3.0.0",
        versioning_strategy=strategy,
        priority=200,
        context=UpgradeContext.DATA
    ),
]

# Apply all upgrades
data = {"version": "1.0.0"}
final, applied = apply_upgrades(
    data,
    steps,
    context=UpgradeContext.DATA,
    upgrade_type="data"
)

print(f"Applied {len(applied)} upgrades: {applied}")
```

# ... upgrade with rollback

```python
from r2x_core import apply_upgrades_with_rollback, UpgradeContext

# Apply with rollback capability
result = apply_upgrades_with_rollback(
    data,
    steps,
    context=UpgradeContext.DATA,
    stop_on_error=True
)

# Validate upgraded data
try:
    validate_data(result.current_data)
    final_data = result.current_data
except ValidationError:
    # Rollback on validation failure
    print("Validation failed, rolling back")
    final_data = result.rollback()
```

# ... register upgrades with plugin

```python
from r2x_core import PluginManager, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

# Define upgrade
def upgrade_my_model_v2(data: dict) -> dict:
    data["version"] = "2.0.0"
    data["model_settings"] = {
        "solver": "default",
        "tolerance": 1e-6
    }
    return data

# Create step
step = UpgradeStep(
    name="my_model_v2",
    func=upgrade_my_model_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    context=UpgradeContext.DATA,
    upgrade_type="data"
)

# Register with plugin manager
PluginManager.register_upgrade_step("my_model", step)

# Automatically applied during data loading
from r2x_core import DataStore

store = DataStore.from_json(
    "config.json",
    folder="/data",
    upgrader="my_model"  # Triggers upgrade
)
```

# ... use version constraints

```python
from r2x_core import UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

# Only upgrade if between min and max versions
step = UpgradeStep(
    name="patch_v2_1",
    func=apply_patch,
    target_version="2.1.0",
    versioning_strategy=SemanticVersioningStrategy(),
    min_version="2.0.0",  # Only if >= 2.0.0
    max_version="2.0.9",  # Only if <= 2.0.9
    context=UpgradeContext.DATA
)

# Upgrade skipped if version < 2.0.0 or > 2.0.9
```

# ... handle complex transformations

```python
from r2x_core import UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

def complex_upgrade(data: dict) -> dict:
    """Complex upgrade with conditional logic."""
    data["version"] = "3.0.0"

    # Conditional field migration
    if "legacy_format" in data:
        legacy = data.pop("legacy_format")
        data["modern_format"] = convert_legacy(legacy)

    # Transform nested structures
    if "buses" in data:
        data["buses"] = [
            {**bus, "upgraded": True}
            for bus in data["buses"]
        ]

    # Add feature flags
    data["features"] = {
        "new_solver": True,
        "experimental": False
    }

    # Validate transformation
    validate_upgraded_structure(data)

    return data

step = UpgradeStep(
    name="complex_v3_upgrade",
    func=complex_upgrade,
    target_version="3.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    context=UpgradeContext.DATA
)
```

# ... control upgrade priority

```python
from r2x_core import UpgradeStep, UpgradeContext, apply_upgrades
from r2x_core import SemanticVersioningStrategy

strategy = SemanticVersioningStrategy()

steps = [
    # Runs first (lower priority number)
    UpgradeStep(
        name="prepare_upgrade",
        func=prepare_data,
        target_version="2.0.0",
        versioning_strategy=strategy,
        priority=50,  # Run early
        context=UpgradeContext.DATA
    ),
    # Runs second
    UpgradeStep(
        name="main_upgrade",
        func=main_transformation,
        target_version="2.0.0",
        versioning_strategy=strategy,
        priority=100,  # Normal priority
        context=UpgradeContext.DATA
    ),
    # Runs last (higher priority number)
    UpgradeStep(
        name="finalize_upgrade",
        func=finalize_data,
        target_version="2.0.0",
        versioning_strategy=strategy,
        priority=200,  # Run late
        context=UpgradeContext.DATA
    ),
]

# Applies in priority order: 50 -> 100 -> 200
final, applied = apply_upgrades(data, steps, context=UpgradeContext.DATA)
```

# ... skip already upgraded data

```python
from r2x_core import apply_upgrade, UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

step = UpgradeStep(
    name="upgrade_to_v2",
    func=upgrade_to_v2,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    context=UpgradeContext.DATA
)

# Already at v2.0.0 or higher - skipped
data = {"version": "2.0.0", "config": {...}}
result, applied = apply_upgrade(data, step)
assert not applied  # Skipped

# Needs upgrade - applied
old_data = {"version": "1.0.0", "config": {...}}
result, applied = apply_upgrade(old_data, step)
assert applied  # Upgraded
```

# ... handle upgrade errors

```python
from r2x_core import apply_upgrades_with_rollback, UpgradeContext

def risky_upgrade(data: dict) -> dict:
    """Upgrade that might fail."""
    data["version"] = "2.0.0"

    if "required_field" not in data:
        raise ValueError("Missing required field")

    return data

# Stop on error and rollback
result = apply_upgrades_with_rollback(
    data,
    [step],
    stop_on_error=True  # Rollback on any error
)

# Continue on errors (default)
result = apply_upgrades_with_rollback(
    data,
    [step1, step2, step3],
    stop_on_error=False  # Skip failed, continue with others
)

print(f"Successful upgrades: {result.applied_steps}")
```

# ... validate before and after upgrade

```python
from r2x_core import apply_upgrades_with_rollback, UpgradeContext

def validate_v1_data(data: dict) -> bool:
    """Validate v1 data structure."""
    return "old_field" in data and data["version"] == "1.0.0"

def validate_v2_data(data: dict) -> bool:
    """Validate v2 data structure."""
    return "new_field" in data and data["version"] == "2.0.0"

# Validate before upgrade
if not validate_v1_data(data):
    raise ValueError("Invalid v1 data")

# Apply upgrade with rollback
result = apply_upgrades_with_rollback(data, steps)

# Validate after upgrade
if validate_v2_data(result.current_data):
    final_data = result.current_data
else:
    # Rollback if validation fails
    final_data = result.rollback()
    raise ValueError("Upgrade validation failed")
```

# ... create idempotent upgrades

```python
from r2x_core import UpgradeStep, UpgradeContext
from r2x_core import SemanticVersioningStrategy

def idempotent_upgrade(data: dict) -> dict:
    """Upgrade that can be applied multiple times safely."""
    data["version"] = "2.0.0"

    # Safe to apply multiple times
    data.setdefault("new_field", "default")

    # Check before transformation
    if "old_field" in data and "new_field" not in data:
        data["new_field"] = data.pop("old_field")

    return data

# Can be applied multiple times without errors
step = UpgradeStep(
    name="idempotent_v2",
    func=idempotent_upgrade,
    target_version="2.0.0",
    versioning_strategy=SemanticVersioningStrategy(),
    context=UpgradeContext.DATA
)
```
