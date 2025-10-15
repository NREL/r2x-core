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
    priority=100
)
def upgrade_to_v2(folder: Path) -> Path:
    """Upgrade configuration from v1 to v2."""
    old_config = folder / "config.json"
    new_config = folder / "settings.json"
    if old_config.exists():
        old_config.rename(new_config)
    return folder
```

# ... use upgrader with DataStore

```python
from r2x_core import DataStore, PluginManager

# Register plugin with upgrader
PluginManager.register_model_plugin(
    name="my_model",
    config=MyModelConfig,
    parser=MyModelParser,
    upgrader=MyModelUpgrader
)

# Upgrader applied automatically during data loading
store = DataStore.from_json(
    "config.json",
    folder="/data",
    upgrader=MyModelUpgrader
)
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

# ... restructure configuration files

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.1.0",
    upgrade_type=UpgradeType.FILE
)
def restructure_config(folder: Path) -> Path:
    """Restructure configuration file."""
    import json

    config_file = folder / "config.json"
    if config_file.exists():
        data = json.loads(config_file.read_text())

        # Nest related fields
        if "host" in data and "port" in data:
            data["connection"] = {
                "host": data.pop("host"),
                "port": data.pop("port")
            }

        data["schema_version"] = "2.1.0"
        config_file.write_text(json.dumps(data, indent=2))

    return folder
```

# ... order multiple upgrade steps with priority

```python
# Priority 50 runs first
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
    priority=50
)
def rename_files_v2(folder: Path) -> Path:
    """Rename files first."""
    (folder / "old.csv").rename(folder / "new.csv")
    return folder

# Priority 100 runs second
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
    priority=100
)
def update_structure_v2(folder: Path) -> Path:
    """Update structure after rename."""
    import json
    config_file = folder / "new.csv"
    # Process the renamed file
    return folder

# Priority 150 runs third
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
    priority=150
)
def finalize_v2(folder: Path) -> Path:
    """Finalize upgrade."""
    (folder / "VERSION").write_text("2.0.0")
    return folder
```

# ... move files to new locations

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE
)
def reorganize_structure(folder: Path) -> Path:
    """Move files to new directory structure."""
    import shutil

    # Create new directories
    data_dir = folder / "data"
    config_dir = folder / "config"
    data_dir.mkdir(exist_ok=True)
    config_dir.mkdir(exist_ok=True)

    # Move data files
    for csv_file in folder.glob("*.csv"):
        shutil.move(str(csv_file), str(data_dir / csv_file.name))

    # Move config files
    for json_file in folder.glob("*.json"):
        shutil.move(str(json_file), str(config_dir / json_file.name))

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
        # Read old format
        df = pl.read_csv(generators_file)

        # Rename columns
        df = df.rename({"gen_name": "name", "cap_mw": "capacity"})

        # Transform values
        df = df.with_columns(
            (pl.col("capacity") * 1000).alias("capacity_kw")
        )

        # Write new format
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

        # Restructure nested data
        if "database" in data:
            db_config = data.pop("database")
            data["connections"] = {
                "primary": db_config
            }

        # Update schema version
        data["schema_version"] = "3.0.0"

        config_file.write_text(json.dumps(data, indent=2))

    return folder
```

# ... detect version from multiple sources

```python
class MyModelUpgrader(DataUpgrader):
    strategy = SemanticVersioningStrategy()

    @staticmethod
    def detect_version(folder: Path) -> str | None:
        """Detect version from multiple sources."""
        # Try VERSION file first
        version_file = folder / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()

        # Try config.json
        config_file = folder / "config.json"
        if config_file.exists():
            import json
            data = json.loads(config_file.read_text())
            if "schema_version" in data:
                return data["schema_version"]

        # Try metadata.yaml
        metadata_file = folder / "metadata.yaml"
        if metadata_file.exists():
            import yaml
            data = yaml.safe_load(metadata_file.read_text())
            if "version" in data:
                return data["version"]

        # No version found
        return None
```

# ... use Git-based versioning

```python
from r2x_core.versioning import GitVersioningStrategy

class MyModelUpgrader(DataUpgrader):
    """Use Git tags for versioning."""

    strategy = GitVersioningStrategy()

    @staticmethod
    def detect_version(folder: Path) -> str | None:
        """Detect version from git describe."""
        import subprocess

        try:
            result = subprocess.run(
                ["git", "describe", "--tags"],
                cwd=folder,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
```

# ... handle missing version gracefully

```python
class MyModelUpgrader(DataUpgrader):
    strategy = SemanticVersioningStrategy()

    @staticmethod
    def detect_version(folder: Path) -> str | None:
        """Detect version or return default."""
        version_file = folder / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()

        # Assume oldest version if no version found
        # This allows upgrading legacy data
        return "1.0.0"
```

# ... validate upgraded data

```python
@MyModelUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
    priority=200  # Run after other upgrades
)
def validate_upgraded_data(folder: Path) -> Path:
    """Validate data after upgrade."""
    import json

    config_file = folder / "config.json"
    if config_file.exists():
        data = json.loads(config_file.read_text())

        # Validate required fields
        required_fields = ["schema_version", "name", "year"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Validate version
        if data["schema_version"] != "2.0.0":
            raise ValueError("Version mismatch after upgrade")

    return folder
```
