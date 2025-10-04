# ... mark a file as time series

```python
from r2x_core import DataFile

# Time series file
timeseries_file = DataFile(
    name="generation_profiles",
    file_path="data/profiles.csv",
    is_timeseries=True,
)

# Component file (default)
component_file = DataFile(
    name="generators",
    file_path="data/generators.csv",
    is_timeseries=False,  # Default
)

print(f"Time series file type: {timeseries_file.file_type}")
print(f"Component file type: {component_file.file_type}")
```

# ... configure time series files in DataStore

```python
from pydantic import BaseModel
from r2x_core import DataFile, DataStore

class ReEDSConfig(BaseModel):
    """Configuration for ReEDS model."""

    model_year: int
    scenario: str
    include_timeseries: bool = True

# Create DataStore with time series files
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

# ... validate time series file formats

```python
from r2x_core import DataFile

# Valid - CSV supports time series
valid_ts = DataFile(
    name="profiles",
    file_path="data/profiles.csv",
    is_timeseries=True,
)
print(f"Valid time series file type: {valid_ts.file_type}")

# Invalid - JSON doesn't support time series
try:
    invalid_ts = DataFile(
        name="profiles",
        file_path="data/profiles.json",
        is_timeseries=True,
    )
    # Accessing file_type triggers validation
    _ = invalid_ts.file_type
except ValueError as e:
    print(f"Error: {e}")
    # Output: File type JSONFile does not support time series data
```

# ... store multi-year time series in a single file

```python
from r2x_core import DataFile

# Single file with multi-year data
multi_year_load = DataFile(
    name="load_profiles",
    file_path="inputs/load_2020_2050.h5",
    is_timeseries=True,
)
```

# ... filter time series files in a parser

```python
from loguru import logger
from r2x_core import BaseParser

class MyParser(BaseParser):
    """Custom parser for my model."""

    def build_time_series(self) -> None:
        """Build time series from marked files."""
        # Only process if config enables time series
        if not self.config.include_timeseries:
            logger.info("Skipping time series (disabled in config)")
            return

        # Get only time series files from DataStore
        timeseries_files = [
            df for df in self.data_store.data_files.values()
            if df.is_timeseries
        ]

        logger.info(f"Processing {len(timeseries_files)} time series files")

        for datafile in timeseries_files:
            # Read time series data
            ts_data = self.read_data_file(datafile.name)

            # Attach to components
            for component in self.system.get_components():
                if component.name in ts_data.columns:
                    component_ts = ts_data[component.name]
                    self.add_time_series(component, component_ts)
```

# ... handle different time series file types

```python
from r2x_core import DataFile, BaseParser
from r2x_core.file_types import TableFile, H5File, ParquetFile
import polars as pl

class MyParser(BaseParser):
    """Parser with file type handling."""

    def _read_timeseries(self, datafile: DataFile) -> pl.DataFrame:
        """Read time series based on file type."""
        match datafile.file_type:
            case TableFile():
                # Handle CSV/TSV
                return pl.read_csv(datafile.file_path)
            case H5File():
                # Handle HDF5
                import h5py
                with h5py.File(datafile.file_path, "r") as f:
                    # Read HDF5 structure and convert to DataFrame
                    data = {name: f[name][:] for name in f.keys()}
                    return pl.DataFrame(data)
            case ParquetFile():
                # Handle Parquet
                return pl.read_parquet(datafile.file_path)
            case _:
                msg = f"Unexpected file type: {datafile.file_type}"
                raise ValueError(msg)
```

# ... export time series files

```python
from loguru import logger
from r2x_core import BaseExporter

class MyExporter(BaseExporter):
    """Custom exporter for my model."""

    def export(self) -> None:
        """Export system to model format."""
        # Export components first
        self._export_components()

        # Get time series files from DataStore
        timeseries_files = [
            df for df in self.data_store.data_files.values()
            if df.is_timeseries
        ]

        logger.info(f"Exporting {len(timeseries_files)} time series files")

        # Export time series
        for datafile in timeseries_files:
            self._export_timeseries(datafile)
            logger.info(f"Exported {datafile.name} to {datafile.file_path}")

    def _export_components(self) -> None:
        """Export component data."""
        # Implementation here
        pass

    def _export_timeseries(self, datafile) -> None:
        """Export single time series file."""
        # Implementation here
        pass
```

# ... add support for a new time series format

```python
# In file_types.py
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

@dataclass(slots=True)
class NetCDFFile(FileType):
    """Data model for NetCDF data."""

    supports_timeseries: bool = True

# Add to mapping
EXTENSION_MAPPING: dict[str, type[FileType]] = {
    # ... existing mappings ...
    ".nc": NetCDFFile,
    ".netcdf": NetCDFFile,
}
```
