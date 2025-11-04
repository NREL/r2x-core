# Create a Basic Exporter

```python
from r2x_core.exporter import BaseExporter
from r2x_core.system import System
from r2x_core.store import DataStore
from pydantic import BaseModel

class MyModelConfig(BaseModel):
    model_year: int
    scenario_name: str

class MyModelExporter(BaseExporter):
    """Exporter for MyModel format."""

    def export(self) -> None:
        """Export system to model format."""
        self._export_generators()
        self._export_buses()
        self.export_time_series()

    def _export_generators(self) -> None:
        pass

    def _export_buses(self) -> None:
        pass

    def export_time_series(self) -> None:
        pass

config = MyModelConfig(model_year=2030, scenario_name="base")
system = System()
data_store = DataStore(folder_path="/path/to/output")
exporter = MyModelExporter(config, system, data_store)
exporter.export()
```

# Export Components To CSV

```python
from r2x_core.exporter import BaseExporter

class MyModelExporter(BaseExporter):

    def _export_generators(self) -> None:
        from my_components import Generator

        gen_file = self.data_store["generators"]
        self.system.export_components_to_csv(
            file_path=gen_file.fpath,
            filter_func=lambda c: isinstance(c, Generator),
        )
```

# Export Time Series

```python
from r2x_core.exporter import BaseExporter
from r2x_core.file_types import TableFile, H5File, ParquetFile
import polars as pl

class MyModelExporter(BaseExporter):

    def export_time_series(self) -> None:
        """Export time series to files."""
        timeseries_files = [
            df for df in self.data_store.list_data()
            if df.info and df.info.is_timeseries
        ]

        for datafile in timeseries_files:
            ts_data = self._collect_timeseries_data(datafile.name)

            match datafile.file_type:
                case TableFile():
                    ts_data.write_csv(datafile.fpath)
                case H5File():
                    ts_data.write_parquet(datafile.fpath)
                case ParquetFile():
                    ts_data.write_parquet(datafile.fpath)

    def _collect_timeseries_data(self, name: str) -> pl.DataFrame:
        return pl.DataFrame()
```
