# ... create a basic DataFile

```python
from r2x_core import DataFile
from pathlib import Path

# Basic CSV file
data_file = DataFile(
    name="generators",
    fpath="generators.csv",
    description="Generator capacity data"
)
```

# ... map column names during loading

```python
# Map column names during loading
data_file = DataFile(
    name="capacity_data",
    fpath="capacity.csv",
    column_mapping={"old_tech": "technology", "cap_mw": "capacity"}
)
```

# ... filter data during loading

```python
# Filter rows by specific values
data_file = DataFile(
    name="regional_data",
    fpath="data.csv",
    filter_by={"year": 2030, "region": ["CA", "TX"]}
)
```

# ... work with different file types

```python
# CSV files
csv_file = DataFile(name="data", fpath="data.csv")

# HDF5 files
h5_file = DataFile(name="timeseries", fpath="timeseries.h5")

# JSON configuration
json_file = DataFile(name="config", fpath="config.json")

# XML data
xml_file = DataFile(name="model", fpath="model.xml")
```

# ... use custom reader functions

```python
# Custom reader function
def custom_reader(file_path):
    # Custom loading logic
    return file_path.read_text().strip().split("\n")

data_file = DataFile(
    name="custom_data",
    fpath="data.txt",
    reader_function=custom_reader
)
```
