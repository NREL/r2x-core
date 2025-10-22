# HDF5 Reader System

## Overview

The HDF5 reader in r2x-core uses a configuration-driven approach to read files with any structure. Instead of hardcoding logic for specific file formats, users describe their file's structure through configuration parameters.

## Design Philosophy

HDF5 files have no standard structure. Different models, tools, and users organize data differently. Dataset names vary between `data`, `values`, `measurements`, and countless other possibilities. Column names might be in separate datasets or embedded within the data. Datetime fields have different formats and timezone handling requirements. Metadata can be stored anywhere in the file hierarchy.

The reader addresses this variability through configuration. Users describe what their file contains and where to find it. A file with data in a dataset called `measurements` and column names in `sensor_names` needs only this configuration:

```python
reader_kwargs = {
    "data_key": "measurements",
    "columns_key": "sensor_names"
}
```

This approach keeps the library model-agnostic. The framework doesn't need to know about ReEDS, PLEXOS, or any specific model format. Users adapt the reader to their files through configuration rather than waiting for library updates or writing custom code.

## How the Reader Works

The `configurable_h5_reader()` function adapts its behavior based on the configuration provided.

### Default Behavior

When no configuration is provided, the reader finds the first dataset in the file and reads it. For 1D arrays, this creates a single column. For 2D arrays, it creates numbered columns like `col_0`, `col_1`, and so on.

```python
# No reader_kwargs provided
datafile = DataFile(name="data", fpath="file.h5")
```

### Specifying the Data Location

The `data_key` parameter tells the reader which dataset contains the main data. This is useful when files contain multiple datasets and you want a specific one rather than just the first.

```python
reader_kwargs = {"data_key": "measurements"}
```

### Adding Column Names

For 2D data arrays, the `columns_key` parameter points to a dataset containing column names. The reader splits the 2D array into named columns using these names. Byte strings are automatically decoded to UTF-8 for convenience.

```python
reader_kwargs = {
    "data_key": "values",
    "columns_key": "sensor_names"
}
```

### Parsing Datetime Fields

The `datetime_key` parameter identifies a dataset containing datetime strings. The reader parses these strings, stripping timezone information by default, and converts them to numpy `datetime64[us]` format for compatibility with Polars. The resulting column is named `datetime` by default, though this can be customized with `datetime_column_name`.

```python
reader_kwargs = {
    "data_key": "data",
    "datetime_key": "timestamps"
}
```

Timezone stripping handles the common case where energy models use a single reference timezone. Most datetime parsing in numpy and Polars is simpler without timezone information. Users who need to preserve the original timezone strings can set `strip_timezone=False`.

### Including Additional Metadata

The `additional_keys` parameter specifies other datasets to include as columns. The reader automatically formats these names for cleaner output, converting names like `index_year` to `solve_year`. If a specified key doesn't exist in the file, it's simply skipped.

```python
reader_kwargs = {
    "data_key": "data",
    "columns_key": "columns",
    "additional_keys": ["year", "scenario", "location"]
}
```

## Configuration Parameters

### Data Configuration

The `data_key` parameter (string, defaults to first dataset) specifies which dataset contains the main data array, whether 1D or 2D.

The `columns_key` parameter (string, optional) points to a dataset containing column names for 2D data arrays.

The `index_key` parameter (string, optional) identifies a dataset to include as an index column, separate from datetime indices.

### Datetime Configuration

The `datetime_key` parameter (string, optional) specifies a dataset containing datetime strings to parse.

The `datetime_column_name` parameter (string, defaults to "datetime") sets the name for the resulting datetime column.

The `strip_timezone` parameter (boolean, defaults to true) controls whether timezone information is removed before parsing datetime strings.

### Additional Data

The `additional_keys` parameter (list of strings, defaults to empty) lists other datasets to include as columns.

The `decode_bytes` parameter (boolean, defaults to true) controls whether byte strings are decoded to UTF-8.

## Automatic Behaviors

The reader automatically detects array dimensions. A 1D array creates a single column. A 2D array without column names creates numbered columns like `data_col_0` and `data_col_1`. A 2D array with column names creates named columns.

Column name formatting happens automatically. Dataset keys like `index_year` become `solve_year`, following energy model conventions. The prefix `index_` is stripped from keys like `index_region` to produce cleaner column names.

Byte string decoding converts HDF5 byte strings to Python Unicode strings automatically. HDF5 often stores strings as bytes, but Python 3 strings are Unicode by default, making automatic conversion convenient for data analysis.

## Architecture Decisions

### Configuration Over Custom Functions

The library could allow users to provide custom reader functions that contain arbitrary logic for reading files. While flexible, this approach doesn't work with JSON configuration files. Users would need to write Python code, making it harder to version control configurations separately from code. Testing would require understanding each custom function's logic. Configuration, by contrast, works seamlessly with JSON, requires no code, and is self-documenting.

### Single Generic Reader Over Multiple Reader Classes

The library could provide different reader classes for different model formats, like `ReedsH5Reader` or `PlexosH5Reader`. This would create coupling between the library and specific models. The library would need to know about every format and maintain code for each. Users would be locked into predefined formats. A single generic reader configured by users avoids all these issues while providing unlimited flexibility.

### Single Dispatch for File Types

The file reading system uses Python's `functools.singledispatch` to route different file formats to appropriate readers. Each file format type (`H5Format`, `TableFormat`, etc.) gets dedicated reading logic. This provides type-based routing at runtime, makes it easy to extend with new formats, and maintains clear separation of concerns between different file types.

## Trade-offs

Configuration requires users to specify file structure explicitly. This verbosity is acceptable because most users read the same files repeatedly, so configuration is written once. The explicitness prevents silent errors from wrong assumptions. Configuration serves as documentation of file structure and can be version controlled alongside data.

The reader doesn't validate that specified keys exist until files are actually read. Early validation would require opening files during configuration, which is expensive and unnecessary. Delayed validation provides better error messages with context about what failed during reading. Missing keys in lists like `additional_keys` are gracefully handled by skipping them.

Datetime parsing assumes ISO 8601 format with specific timezone handling. This covers the vast majority of HDF5 datetime storage. Edge cases can disable automatic parsing with `strip_timezone=False` and handle conversion manually. Complex datetime parsing belongs in preprocessing steps rather than the core library.

## Future Considerations

Chunk reading for very large files could improve memory efficiency by processing data in pieces. Lazy evaluation could defer reading until data is actually needed. Optional schema validation could check file structure against expected configurations. Automatic compression handling could simplify working with compressed datasets.

The library intentionally avoids auto-detecting file structure. Users should know their data. Format conversion between different HDF5 structures belongs in external tools. Model-specific logic defeats the purpose of a generic, configuration-driven approach.

## Examples of File Structures

### Energy Model Time Series

```
file.h5
├── data (8760 x 50)        # Hourly data, 50 regions
├── columns (50,)           # Region names
├── index_datetime (8760,)  # Timestamps
└── index_year (8760,)      # Solve year for each hour
```

**Configuration**:
```python
reader_kwargs = {
    "data_key": "data",
    "columns_key": "columns",
    "datetime_key": "index_datetime",
    "additional_keys": ["index_year"]
}
```

### Scientific Measurements

```
measurements.h5
├── temperature (1000,)     # 1D time series
├── pressure (1000,)        # 1D time series
├── timestamps (1000,)      # When measured
├── sensor_id (1000,)       # Which sensor
└── location (1000,)        # Where measured
```

**Configuration**:
```python
reader_kwargs = {
    "data_key": "temperature",
    "datetime_key": "timestamps",
    "additional_keys": ["pressure", "sensor_id", "location"]
}
```

### Simple Tabular Data

```
simple.h5
└── values (100 x 3)        # Just a 2D array
```

**Configuration**:
```python
# No configuration needed - uses default
reader_kwargs = {}
```

## Summary

The HDF5 reader achieves flexibility through configuration rather than code. The library remains model-agnostic with no hardcoded knowledge of specific formats. Users control everything through configuration parameters. The approach works seamlessly with JSON configuration files and is self-documenting. A single code path handles all formats, making the system maintainable. New formats need only new configuration, never code changes.
