# Working with HDF5 Files

# ... read an HDF5 file with default settings

```python
from r2x_core import DataFile
from pathlib import Path

# Reads the first dataset automatically
datafile = DataFile(
    name="simple_data",
    fpath=Path("data.h5"),
    file_type="H5Format"
)
```

# ... read tabular HDF5 data with column names

```python
# For files with separate data and column name datasets
datafile = DataFile(
    name="tabular_data",
    fpath=Path("tabular.h5"),
    file_type="H5Format",
    reader_kwargs={
        "data_key": "values",        # 2D data array
        "columns_key": "col_names"   # Column name strings
    }
)
```

# ... read HDF5 time series data

```python
# For files with datetime indices
datafile = DataFile(
    name="timeseries",
    fpath=Path("timeseries.h5"),
    file_type="H5Format",
    reader_kwargs={
        "data_key": "data",
        "columns_key": "columns",
        "datetime_key": "timestamps",
        "datetime_column_name": "timestamp"
    }
)
```

# ... read HDF5 files with metadata fields

```python
# Include additional datasets as columns
datafile = DataFile(
    name="complex_data",
    fpath=Path("complex.h5"),
    file_type="H5Format",
    reader_kwargs={
        "data_key": "measurements",
        "columns_key": "sensors",
        "datetime_key": "time",
        "additional_keys": ["location", "depth", "quality_flag"]
    }
)
```

# ... configure HDF5 reading in JSON

```json
{
  "name": "load_data",
  "fpath": "data/load.h5",
  "file_type": "H5Format",
  "reader_kwargs": {
    "data_key": "data",
    "columns_key": "columns",
    "datetime_key": "index_datetime",
    "additional_keys": ["index_year"]
  }
}
```

# ... create a DataStore with multiple HDF5 files

```json
{
  "name": "my_datastore",
  "datafiles": [
    {
      "name": "scientific_data",
      "fpath": "experiments/results.h5",
      "file_type": "H5Format",
      "reader_kwargs": {
        "data_key": "measurements",
        "columns_key": "sensors",
        "datetime_key": "timestamps",
        "additional_keys": ["experiment_id", "lab_location"]
      }
    },
    {
      "name": "simple_data",
      "fpath": "data/simple.h5",
      "file_type": "H5Format"
    }
  ]
}
```

# ... process HDF5 data with datetime filtering

```python
from r2x_core import DataFile, DataStore
from pathlib import Path
import polars as pl

# Define file structure
datafile = DataFile(
    name="load_data",
    fpath=Path("load_data.h5"),
    file_type="H5Format",
    reader_kwargs={
        "data_key": "data",
        "columns_key": "columns",
        "datetime_key": "index_datetime",
        "additional_keys": ["index_year"]
    }
)

# Read and filter
store = DataStore(name="loads", datafiles=[datafile])
df_lazy = store.read_file("load_data")

# Filter by year
df = df_lazy.filter(
    pl.col("datetime").dt.year() == 2007
).collect()
```
