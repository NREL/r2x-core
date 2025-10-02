# ... read data files with DataReader

```python
from r2x_core import DataReader, DataFile
from pathlib import Path

# Create reader
reader = DataReader()

# Read file directly
data_file = DataFile(name="data", fpath="data.csv")
data = reader.read_data_file(Path("."), data_file)
```

# ... configure data caching

```python
# Set cache size limit
reader = DataReader(max_cache_size=50)

# Clear cache
reader.clear_cache()

# Get cache information
cache_info = reader.get_cache_info()
print(f"Cache size: {cache_info['size']}")
print(f"Cache hits: {cache_info['hits']}")
```

# ... handle different file types

```python
# CSV/TSV files automatically use Polars
csv_data = reader.read_data_file(folder, csv_file)

# HDF5 files use h5py
h5_data = reader.read_data_file(folder, h5_file)

# JSON files use standard json module
json_data = reader.read_data_file(folder, json_file)
```

# ... work with optional files

```python
# Mark file as optional
optional_file = DataFile(
    name="optional_data",
    fpath="might_not_exist.csv",
    is_optional=True
)

# Won't raise error if file missing
try:
    data = reader.read_data_file(folder, optional_file)
except FileNotFoundError:
    data = None  # Handle gracefully
```
