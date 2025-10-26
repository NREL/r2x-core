# ... create a DataStore

```python
from r2x_core import DataStore
from pathlib import Path

# With specific folder
store = DataStore(folder_path="/path/to/data")

# Use current directory
store = DataStore()
```

# ... add files to a DataStore

```python
from r2x_core import DataFile

# Single file
data_file = DataFile(name="generators", fpath="gen.csv")
store.add_data(data_file)

# Multiple files
files = [
    DataFile(name="generators", fpath="gen.csv"),
    DataFile(name="loads", fpath="load.csv")
]
store.add_data(*files)
```

# ... read data from a DataStore

```python
# Load specific file
data = store.read_data("generators")

# Load without cache
data = store.read_data("generators", use_cache=False)
```

# ... manage DataStore contents

```python
# List all files
file_names = store.list_data()

# Check if file exists
if "generators" in store:
    print("File exists")

# Get file configuration
config = store["generators"]

# Remove files
store.remove_data("generators")
store.remove_data("loads", "transmission")
```

# ... save and load DataStore configurations

```python
# Save store configuration
store.to_json("config.json")

# Load from configuration
store = DataStore.from_json("config.json", folder_path="/path/to/data")
```
