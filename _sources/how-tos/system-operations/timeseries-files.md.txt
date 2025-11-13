# Mark a File as Time Series

```python
from r2x_core import DataFile

timeseries_file = DataFile(
    name="generation_profiles",
    file_path="data/profiles.csv",
    is_timeseries=True,
)

component_file = DataFile(
    name="generators",
    file_path="data/generators.csv",
    is_timeseries=False,
)
```

# Configure Time Series Files In Datastore

```python
from r2x_core import DataFile, DataStore

data_store = DataStore(
    data_files={
        "generators": DataFile(
            name="generators",
            file_path="inputs/generators.csv",
        ),
        "cf_profiles": DataFile(
            name="cf_profiles",
            file_path="inputs/profiles.h5",
            is_timeseries=True,
        ),
    },
    folder="/path/to/data",
)
```

# Filter Time Series Files In Parser

```python
from r2x_core import BaseParser

class MyParser(BaseParser):
    def build_time_series(self) -> None:
        timeseries_files = [
            df for df in self.data_store.list_data()
            if df.info and df.info.is_timeseries
        ]

        for datafile in timeseries_files:
            ts_data = self.read_data_file(datafile.name)
            for col in ts_data.columns:
                component = self.system.get_component_by_name(col)
                if component:
                    self.add_time_series(component, ts_data[col])
```
