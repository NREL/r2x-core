# ... read tabular HDF5 data with column names

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

# ... read HDF5 time series data

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

# ... process HDF5 data with datetime filtering

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
