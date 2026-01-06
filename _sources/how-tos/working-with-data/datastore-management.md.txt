# Create a DataStore

```python
from r2x_core import DataStore

store = DataStore(path="/path/to/data")
```

# Add Files To A Datastore

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

# Read Data From A Datastore

```python
data = store.read_data("generators")
data = store.read_data("generators", use_cache=False)
```
