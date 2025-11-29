# Read Tabular HDF5 Data with Column Names

```python
from r2x_core import DataFile
from pathlib import Path

datafile = DataFile(
    name="tabular_data",
    fpath=Path("tabular.h5"),
    file_type="H5Format",
    reader_kwargs={
        "data_key": "values",
        "columns_key": "col_names"
    }
)
```

# Read HDF5 Time Series Data

```python
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

# Process HDF5 Data With Datetime Filtering

```python
from r2x_core import DataFile, DataStore
from pathlib import Path
import polars as pl

datafile = DataFile(
    name="load_data",
    fpath=Path("load_data.h5"),
    file_type="H5Format",
    reader_kwargs={
        "data_key": "data",
        "columns_key": "columns",
        "datetime_key": "index_datetime",
    }
)

store = DataStore(name="loads", datafiles=[datafile])
df_lazy = store.read_file("load_data")

df = df_lazy.filter(
    pl.col("datetime").dt.year() == 2007
).collect()
```
