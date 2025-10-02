# ... perform column operations

```python
from r2x_core import DataFile

# Rename columns
data_file = DataFile(
    name="data",
    fpath="data.csv",
    column_mapping={"old_name": "new_name", "col1": "column_1"}
)

# Drop unwanted columns
data_file = DataFile(
    name="data",
    fpath="data.csv",
    drop_columns=["unused_col", "temp_col"]
)

# Define column schema for headerless files
data_file = DataFile(
    name="data",
    fpath="data.csv",
    column_schema={"col1": "string", "col2": "int", "col3": "float"}
)
```

# ... filter data during loading

```python
# Filter by single value
data_file = DataFile(
    name="yearly_data",
    fpath="data.csv",
    filter_by={"year": 2030}
)

# Filter by multiple values
data_file = DataFile(
    name="regional_data",
    fpath="data.csv",
    filter_by={"region": ["CA", "TX", "NY"]}
)

# Combine filters
data_file = DataFile(
    name="filtered_data",
    fpath="data.csv",
    filter_by={"year": 2030, "status": "active", "region": ["CA", "TX"]}
)
```

# ... reshape data with pivot operations

```python
# Reshape data by pivoting on column
data_file = DataFile(
    name="wide_data",
    fpath="long_data.csv",
    pivot_on="metric_name",
    aggregate_function="sum"
)
```

# ... select specific columns

```python
# Define index and value columns
data_file = DataFile(
    name="structured_data",
    fpath="data.csv",
    index_columns=["region", "year"],
    value_columns=["capacity", "generation"]
)
```
