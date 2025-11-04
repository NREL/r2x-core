# Create JSON configurations

```python
import json
from r2x_core import DataFile

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

with open("data_config.json", "w") as f:
    json.dump(config, f, indent=2)
```

## Load DataStore from configuration

```python
from r2x_core import DataStore

store = DataStore.from_json("data_config.json", folder_path="/path/to/data")
print(store.list_data())
```
