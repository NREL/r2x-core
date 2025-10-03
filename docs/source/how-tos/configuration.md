# ... create JSON configurations

```python
import json
from r2x_core import DataFile, DataStore

# Define file configurations
config = [
    {
        "name": "generators",
        "fpath": "gen_data.csv",
        "description": "Generator capacity data",
        "units": "MW"
    },
    {
        "name": "loads",
        "fpath": "load_data.csv",
        "description": "Load profiles",
        "filter_by": {"year": 2030}
    }
]

# Save configuration
with open("data_config.json", "w") as f:
    json.dump(config, f, indent=2)
```

# ... load DataStore from configuration

```python
# Load DataStore from JSON
store = DataStore.from_json("data_config.json", folder="/path/to/data")

# List loaded files
print(store.list_data_files())
```

# ... export existing configurations

```python
# Create store and add files
store = DataStore(folder="/path/to/data")
files = [
    DataFile(name="gen", fpath="generators.csv"),
    DataFile(name="load", fpath="loads.csv")
]
store.add_data_files(files)

# Export to JSON
store.to_json("exported_config.json")

# Export with custom options
store.to_json("config.json", exclude_none=True)
```

# ... validate configurations

```python
from pydantic import ValidationError

try:
    data_file = DataFile(
        name="test",
        fpath="nonexistent.xyz"  # Unsupported extension
    )
except ValidationError as e:
    print(f"Configuration error: {e}")
```

# ... manage environment-specific configurations

```python
# Development configuration
dev_config = [
    {"name": "test_data", "fpath": "test_small.csv", "is_optional": True}
]

# Production configuration
prod_config = [
    {"name": "prod_data", "fpath": "production_large.csv", "is_optional": False}
]

# Load based on environment
import os
config_file = "dev_config.json" if os.getenv("ENV") == "dev" else "prod_config.json"
store = DataStore.from_json(config_file, folder="/data")
```
