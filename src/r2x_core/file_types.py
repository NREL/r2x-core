from typing import TypeAlias

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


@dataclass(slots=True)
class FileType:  # type: ignore
    """Base class for file data types."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TableFile(FileType):
    """Data model for tabular data (CSV, H5, etc.)."""

    ...


class H5File(FileType):
    """Data model for HDF5 data."""

    ...


class JSONFile(FileType):
    """Data model for JSON data."""

    ...


class XMLFile(FileType):
    """Data model for XML data."""

    ...


# Mapping of files to FileType
EXTENSION_MAPPING: dict[str, type[FileType]] = {
    ".csv": TableFile,
    ".tsv": TableFile,
    ".h5": H5File,
    ".hdf5": H5File,
    ".json": JSONFile,
    ".xml": XMLFile,
}

TableDataFileType: TypeAlias = TableFile | H5File
