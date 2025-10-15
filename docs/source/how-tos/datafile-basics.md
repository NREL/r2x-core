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

# ... use glob patterns to match files

```python
# Match a single XML file with unknown name
# Useful when the file name varies (e.g., user-renamed model files)
model_file = DataFile(
    name="plexos_model",
    glob="*.xml",
    description="Plexos model XML file"
)

# Match files with specific prefix
output_file = DataFile(
    name="results",
    glob="output_*.csv"
)

# Match files with wildcard in the middle
data_file = DataFile(
    name="scenario_data",
    glob="scenario_?_data.csv"  # Matches scenario_1_data.csv, scenario_2_data.csv, etc.
)
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
