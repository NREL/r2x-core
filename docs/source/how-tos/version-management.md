# ... manage versions in data

```python
from r2x_core import SemanticVersioningStrategy

# Create versioning strategy
strategy = SemanticVersioningStrategy(version_field="version")

# Get current version
data = {"version": "1.2.3", "config": {...}}
current = strategy.get_version(data)
print(f"Current version: {current}")

# Check if upgrade needed
if strategy.compare(current, "2.0.0") < 0:
    print("Upgrade required")
```

# ... compare versions

```python
from r2x_core import SemanticVersioningStrategy

strategy = SemanticVersioningStrategy()

# Compare semantic versions
strategy.compare("1.0.0", "2.0.0")  # -1 (needs upgrade)
strategy.compare("2.0.0", "1.0.0")  # 1  (downgrade)
strategy.compare("1.0.0", "1.0.0")  # 0  (equal)

# Handle missing versions
strategy.compare(None, "1.0.0")     # -1 (always needs upgrade)
```

# ... set version in data

```python
from r2x_core import SemanticVersioningStrategy

strategy = SemanticVersioningStrategy()

# Set version in dictionary
data = {"name": "test", "value": 10}
data = strategy.set_version(data, "2.0.0")
assert data["version"] == "2.0.0"

# Set version in object
from pydantic import BaseModel

class Config(BaseModel):
    version: str = "1.0.0"
    name: str

config = Config(name="test")
strategy.set_version(config, "2.0.0")
assert config.version == "2.0.0"
```

# ... use git-based versioning

```python
from r2x_core import GitVersioningStrategy

# Using commit hashes
strategy = GitVersioningStrategy(version_field="git_commit")

data = {
    "git_commit": "abc123def456",
    "config": {...}
}

current = strategy.get_version(data)
data = strategy.set_version(data, "def456ghi789")
```

# ... use timestamp versioning

```python
from r2x_core import GitVersioningStrategy

# Using ISO timestamps
strategy = GitVersioningStrategy(
    version_field="updated_at",
    use_timestamps=True
)

data = {
    "updated_at": "2024-01-01T00:00:00Z",
    "config": {...}
}

# Compare timestamps
older = "2024-01-01T00:00:00Z"
newer = "2024-06-01T00:00:00Z"

if strategy.compare(older, newer) < 0:
    print("Data is outdated")
```

# ... track file modification times

```python
from pathlib import Path
from r2x_core import FileModTimeStrategy

strategy = FileModTimeStrategy()

# Get version from file path
config_file = Path("/data/config.json")
version = strategy.get_version(config_file)

# Compare file modification times
old_file = Path("/data/old_config.json")
new_file = Path("/data/new_config.json")

old_version = strategy.get_version(old_file)
new_version = strategy.get_version(new_file)

if strategy.compare(old_version, new_version) < 0:
    print("File has been updated")
```

# ... use custom version fields

```python
from r2x_core import SemanticVersioningStrategy

# Custom field for schema version
strategy = SemanticVersioningStrategy(
    version_field="schema_version",
    default_version="0.0.0"
)

data = {
    "schema_version": "2.1.0",
    "data": {...}
}

version = strategy.get_version(data)  # "2.1.0"

# Missing version uses default
data_no_version = {"data": {...}}
version = strategy.get_version(data_no_version)  # None
strategy.compare(None, "1.0.0")  # -1 (treated as 0.0.0)
```

# ... implement custom versioning strategy

```python
from typing import Any
from r2x_core.versioning import VersioningStrategy
from datetime import datetime

class CustomVersionStrategy(VersioningStrategy):
    """Custom versioning based on timestamp and build number."""

    def __init__(self):
        self.format = "%Y%m%d.%H%M"

    def get_version(self, data: Any) -> str | None:
        """Get version as timestamp.build."""
        if isinstance(data, dict):
            timestamp = data.get("timestamp")
            build = data.get("build_number", 0)
            if timestamp:
                return f"{timestamp}.{build}"
        return None

    def set_version(self, data: Any, version: str) -> Any:
        """Set version from timestamp.build format."""
        if isinstance(data, dict):
            timestamp, build = version.split(".")
            data["timestamp"] = timestamp
            data["build_number"] = int(build)
        return data

    def compare(self, current: str | None, target: str) -> int:
        """Compare timestamp.build versions."""
        if current is None:
            return -1

        # Parse versions
        curr_ts, curr_build = current.split(".")
        targ_ts, targ_build = target.split(".")

        # Compare timestamps first
        if curr_ts < targ_ts:
            return -1
        elif curr_ts > targ_ts:
            return 1

        # Same timestamp, compare build numbers
        curr_b = int(curr_build)
        targ_b = int(targ_build)

        if curr_b < targ_b:
            return -1
        elif curr_b > targ_b:
            return 1
        return 0

# Use custom strategy
strategy = CustomVersionStrategy()
data = {"timestamp": "20241001.1200", "build_number": 5}
version = strategy.get_version(data)  # "20241001.1200.5"
```

# ... check version compatibility

```python
from r2x_core import SemanticVersioningStrategy

def check_compatibility(data: dict, required_version: str) -> bool:
    """Check if data version meets requirements."""
    strategy = SemanticVersioningStrategy()

    current = strategy.get_version(data)
    if current is None:
        return False

    # Current must be >= required
    return strategy.compare(current, required_version) >= 0

# Usage
data = {"version": "2.1.0", "config": {...}}
if check_compatibility(data, "2.0.0"):
    print("Compatible version")
else:
    print("Version too old, upgrade required")
```

# ... validate version format

```python
from r2x_core import SemanticVersioningStrategy
from packaging.version import Version, InvalidVersion

def validate_semantic_version(version_str: str) -> bool:
    """Validate semantic version format."""
    try:
        Version(version_str)
        return True
    except InvalidVersion:
        return False

# Usage
valid = validate_semantic_version("1.2.3")      # True
invalid = validate_semantic_version("not.a.ver")  # False
```
