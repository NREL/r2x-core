# ... read data files with DataReader

```python
from r2x_core import DataReader, DataFile
from pathlib import Path

reader = DataReader()
data_file = DataFile(name="data", fpath="data.csv")
data = reader.read_data_file(Path("."), data_file)
```

# ... configure data caching

```python
reader = DataReader(max_cache_size=50)

reader.clear_cache()

cache_info = reader.get_cache_info()
print(f"Cache size: {cache_info['size']}")
print(f"Cache hits: {cache_info['hits']}")
```
