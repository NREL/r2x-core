```{toctree}
:maxdepth: 2
:hidden:

install
how-tos/index
references/index
contributing
CHANGELOG
```

# R2X Core Documentation

R2X Core is a foundational data file management framework that provides declarative configuration and efficient loading of structured data files.

## About R2X Core

R2X Core provides declarative configuration and efficient loading of structured data files. It serves as the foundation for data management across different power system modeling frameworks, enabling seamless data workflows and reproducible analysis.

### Key Features

R2X Core offers the following capabilities:

- **Declarative data file configuration** - Define how files should be read and processed using simple Python objects
- **Multiple file format support** - Native support for CSV, HDF5, JSON, XML with extensible architecture for custom formats
- **Data transformation pipeline** - Apply filters, column mapping, and reshaping operations during data loading
- **Intelligent caching system** - Optimize performance with configurable LRU caching and memory management
- **Configuration management** - Save, load, and share data setups through JSON serialization for reproducible workflows

## Quick Start

```python
from r2x_core import DataFile, DataStore

# Create a data store
store = DataStore(folder="/path/to/data")

# Configure a data file with transformations
data_file = DataFile(
    name="generators",
    fpath="generators.csv",
    description="Power plant data",
    filter_by={"year": 2030},
    column_mapping={"old_name": "new_name"}
)

# Add to store and load data
store.add_data_file(data_file)
data = store.read_data_file("generators")
```

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
