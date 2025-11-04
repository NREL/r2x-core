# ... create a DataStore

```python
from r2x_core import DataStore

store = DataStore(folder_path="/path/to/data")
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
data = store.read_data("generators")
data = store.read_data("generators", use_cache=False)
```
