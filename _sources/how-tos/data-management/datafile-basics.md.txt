# Create a Basic DataFile

```python
from r2x_core import DataFile

data_file = DataFile(
    name="generators",
    fpath="generators.csv",
    description="Generator capacity data"
)
```

# Map Column Names During Loading

```python
data_file = DataFile(
    name="capacity_data",
    fpath="capacity.csv",
    proc_spec={"column_mapping": {"old_tech": "technology", "cap_mw": "capacity"}}
)
```

# Filter Data During Loading

```python
data_file = DataFile(
    name="regional_data",
    fpath="data.csv",
    proc_spec={"filter_by": {"year": 2030, "region": ["CA", "TX"]}}
)
```
