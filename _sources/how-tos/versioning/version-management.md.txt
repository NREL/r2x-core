# Manage Versions in Data

```python
from r2x_core import SemanticVersioningStrategy

strategy = SemanticVersioningStrategy(version_field="version")

data = {"version": "1.2.3", "config": {...}}
current = strategy.get_version(data)
print(f"Current version: {current}")

if strategy.compare(current, "2.0.0") < 0:
    print("Upgrade required")
```

# Compare Versions

```python
from r2x_core import SemanticVersioningStrategy

strategy = SemanticVersioningStrategy()

strategy.compare("1.0.0", "2.0.0")  # -1 (needs upgrade)
strategy.compare("2.0.0", "1.0.0")  # 1 (downgrade)
strategy.compare("1.0.0", "1.0.0")  # 0 (equal)
```

# Use Custom Version Fields

```python
from r2x_core import SemanticVersioningStrategy
from pydantic import BaseModel

class Config(BaseModel):
    schema_version: str = "1.0.0"
    name: str

strategy = SemanticVersioningStrategy(version_field="schema_version")

config = Config(name="test")
strategy.set_version(config, "2.0.0")
assert config.schema_version == "2.0.0"
```
