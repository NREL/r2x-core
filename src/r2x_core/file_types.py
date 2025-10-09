"""File format type definitions for model data files.

This module provides lightweight type markers for different file formats
used in model data processing. These types enable single dispatch patterns
for format-specific file reading and processing logic.
"""

from typing import Any, ClassVar, TypeAlias

from pydantic_core import core_schema


class FileFormat:
    """Lightweight base class for file format types.

    This is a minimal sentinel class designed to work with singledispatch.
    Subclasses act as type markers for dispatch without storing instance data.

    Attributes
    ----------
    supports_timeseries : bool
        Whether this file format can store time series data. Default is False.
    """

    __slots__ = ()  # Prevent instance attributes for minimal memory footprint
    supports_timeseries: ClassVar[bool] = False

    def __repr__(self) -> str:
        """Return string representation of the file format.

        Returns
        -------
        str
            Class name followed by empty parentheses.
        """
        return f"{self.__class__.__name__}()"

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        """Generate Pydantic schema for FileFormat instances.

        This allows FileFormat instances to be used in Pydantic models.
        They are serialized as their class name string.
        """
        python_schema = core_schema.is_instance_schema(cls)

        return core_schema.no_info_after_validator_function(
            lambda x: x,
            python_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: instance.__class__.__name__,
                return_schema=core_schema.str_schema(),
            ),
        )


class TableFormat(FileFormat):
    """Tabular data format (CSV, TSV, etc.).

    Supports time series data storage.
    """

    __slots__ = ()
    supports_timeseries: ClassVar[bool] = True


class H5Format(FileFormat):
    """HDF5 data format.

    Supports time series data storage with hierarchical organization.
    Use reader_kwargs to configure how the file is read.
    """

    __slots__ = ()
    supports_timeseries: ClassVar[bool] = True


class ParquetFormat(FileFormat):
    """Apache Parquet data format.

    Supports time series data storage with columnar compression.
    """

    __slots__ = ()
    supports_timeseries: ClassVar[bool] = True


class JSONFormat(FileFormat):
    """JSON data format.

    Does not support time series (typically used for component definitions).
    """

    __slots__ = ()
    supports_timeseries: ClassVar[bool] = False


class XMLFormat(FileFormat):
    """XML data format.

    Does not support time series (typically used for hierarchical component data).
    """

    __slots__ = ()
    supports_timeseries: ClassVar[bool] = False


# Mapping of file extensions to format classes
EXTENSION_MAPPING: dict[str, type[FileFormat]] = {
    ".csv": TableFormat,
    ".tsv": TableFormat,
    ".h5": H5Format,
    ".hdf5": H5Format,
    ".parquet": ParquetFormat,
    ".json": JSONFormat,
    ".xml": XMLFormat,
}

TableDataFormat: TypeAlias = TableFormat | H5Format | ParquetFormat
