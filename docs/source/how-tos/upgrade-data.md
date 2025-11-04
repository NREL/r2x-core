# ... create a basic upgrader class

```python
from pathlib import Path
from r2x_core.upgrader import DataUpgrader, UpgradeType
from r2x_core.versioning import SemanticVersioningStrategy

class MyModelUpgrader(DataUpgrader):
    """Upgrader for my_model plugin data."""

    strategy = SemanticVersioningStrategy(version_field="schema_version")

    @staticmethod
    def detect_version(folder: Path) -> str | None:
        """Detect version from version file."""
        version_file = folder / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return None
```

# ... register FILE upgrade steps

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
)
def upgrade_to_v2(folder: Path) -> Path:
    """Upgrade configuration from v1 to v2."""
    old_config = folder / "config.json"
    new_config = folder / "settings.json"
    if old_config.exists():
        old_config.rename(new_config)
    return folder
```

# ... rename files during upgrade

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE
)
def rename_input_files(folder: Path) -> Path:
    """Rename buses.csv to nodes.csv."""
    old_file = folder / "buses.csv"
    new_file = folder / "nodes.csv"

    if old_file.exists():
        old_file.rename(new_file)

    return folder
```

# ... transform CSV data during upgrade

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE
)
def update_csv_format(folder: Path) -> Path:
    """Update CSV column names and values."""
    import polars as pl

    generators_file = folder / "generators.csv"
    if generators_file.exists():
        df = pl.read_csv(generators_file)
        df = df.rename({"gen_name": "name", "cap_mw": "capacity"})
        df = df.with_columns(
            (pl.col("capacity") * 1000).alias("capacity_kw")
        )
        df.write_csv(generators_file)

    return folder
```

# ... update JSON schema during upgrade

```python
@MyModelUpgrader.upgrade_step(
    target_version="3.0.0",
    upgrade_type=UpgradeType.FILE
)
def migrate_json_schema(folder: Path) -> Path:
    """Migrate JSON to new schema."""
    import json

    config_file = folder / "config.json"
    if config_file.exists():
        data = json.loads(config_file.read_text())

        # Remove deprecated fields
        data.pop("legacy_option", None)

        # Add new required fields with defaults
        data.setdefault("solver", "gurobi")
        data.setdefault("threads", 4)

        data["schema_version"] = "3.0.0"
        config_file.write_text(json.dumps(data, indent=2))

    return folder
```
