from typing import TypeAlias

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


@dataclass(slots=True)
class FileType:
    """Base class for file data types.

    Attributes
    ----------
    supports_timeseries : bool
        Whether this file type can store time series data. Default is False.
    """

    supports_timeseries: bool = False
    model_config = ConfigDict(arbitrary_types_allowed=True)


class TableFile(FileType):
    """Data model for tabular data (CSV, TSV, etc.).

    Supports time series data storage.
    """

    supports_timeseries: bool = True


class H5File(FileType):
    """Data model for HDF5 data.

    Supports time series data storage with hierarchical organization.
    """

    supports_timeseries: bool = True


class ParquetFile(FileType):
    """Data model for Apache Parquet data.

    Supports time series data storage with columnar compression.
    """

    supports_timeseries: bool = True


class JSONFile(FileType):
    """Data model for JSON data.

    Does not support time series (typically used for component definitions).
    """

    supports_timeseries: bool = False


class XMLFile(FileType):
    """Data model for XML data.

    Does not support time series (typically used for hierarchical component data).
    """

    supports_timeseries: bool = False


# Mapping of files to FileType
EXTENSION_MAPPING: dict[str, type[FileType]] = {
    ".csv": TableFile,
    ".tsv": TableFile,
    ".h5": H5File,
    ".hdf5": H5File,
    ".parquet": ParquetFile,
    ".json": JSONFile,
    ".xml": XMLFile,
}

TableDataFileType: TypeAlias = TableFile | H5File | ParquetFile
