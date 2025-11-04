# ... perform column operations

```python
from r2x_core import DataFile

# Rename columns
data_file = DataFile(
    name="data",
    fpath="data.csv",
    proc_spec={"column_mapping": {"old_name": "new_name", "col1": "column_1"}}
)

# Drop unwanted columns
data_file = DataFile(
    name="data",
    fpath="data.csv",
    proc_spec={"drop_columns": ["unused_col", "temp_col"]}
)
```

# ... filter data during loading

```python
# Filter by single value
data_file = DataFile(
    name="yearly_data",
    fpath="data.csv",
    proc_spec={"filter_by": {"year": 2030}}
)

# Filter by multiple values
data_file = DataFile(
    name="regional_data",
    fpath="data.csv",
    proc_spec={"filter_by": {"region": ["CA", "TX", "NY"]}}
)
```
