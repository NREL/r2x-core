"""Data Reader for loading files based on their type."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from r2x_core.datafile_utils import get_file_path

from .datafile import DataFile
from .exceptions import ReaderError
from .file_readers import read_file_by_type
from .file_types import EXTENSION_MAPPING
from .processors import apply_processing, register_transformation


class DataReader:
    """Reader class for loading data files.

    The DataReader handles the actual file I/O operations,
    while delegating file-type-specific reading logic to
    single dispatch methods.
    """

    def __init__(self) -> None:
        """Initialize the data reader."""

    def read_data_file(
        self,
        data_file: DataFile,
        folder_path: Path,
        placeholders: dict[str, Any] | None = None,
    ) -> Any:
        """Read a data file.

        Parameters
        ----------
        data_file : DataFile
            Data file configuration with metadata.
        folder : Path
            Base directory containing the data files.
        placeholders : dict[str, Any] | None, optional
            Dictionary mapping placeholder variable names to their values.
            Used to substitute placeholders like {solve_year} in filter_by.
            Default is None.

        Returns
        -------
        Any
            The loaded data, type depends on file type.

        Raises
        ------
        FileNotFoundError
            If the file does not exist and is not optional.
        ValueError
            If glob pattern matches zero or multiple files (for required files),
            or if placeholders are found in filter_by but no placeholders dict provided.
        """
        logger.debug("Starting reading for data_file={}", data_file.name)
        fpath_result = get_file_path(data_file, folder_path, info=data_file.info)
        if fpath_result.is_err():
            error = fpath_result.err()
            if isinstance(error, ValueError):
                raise error
            raise FileNotFoundError(str(error)) from error
        fpath = fpath_result.unwrap()

        if fpath is None:
            logger.info("Skipping optional file: {}", data_file.name)
            return None

        reader = data_file.reader
        reader_kwargs = reader.kwargs if reader else {}
        if reader and reader.function:
            logger.debug(
                "Attempting to read data_file{} with reader_function={}",
                data_file.name,
                data_file.reader,
            )
            raw_data = reader.function(fpath, **reader_kwargs)
            if data_file.proc_spec is not None:
                processed_data = apply_processing(
                    data_file=data_file,
                    data=raw_data,
                    proc_spec=data_file.proc_spec,
                    placeholders=placeholders,
                )

                if processed_data.is_err():
                    raise ReaderError(processed_data.error)

                processed_data = processed_data.unwrap()
            else:
                processed_data = raw_data

            return processed_data

        file_type_instance = data_file.file_type
        logger.trace(
            "Attempting to read data_file={} with {}", data_file.name, type(file_type_instance).__name__
        )
        raw_data = read_file_by_type(file_type_instance, fpath, **reader_kwargs)
        if data_file.proc_spec is not None:
            processed_data = apply_processing(
                data_file=data_file, data=raw_data, proc_spec=data_file.proc_spec, placeholders=placeholders
            )
            if processed_data.is_err():
                raise ReaderError(processed_data.error)

            processed_data = processed_data.unwrap()
        else:
            processed_data = raw_data
        return processed_data

    def get_supported_file_types(self) -> list[str]:
        """Get list of supported file extensions.

        Returns
        -------
        list[str]
            List of supported file extensions.
        """
        return list(EXTENSION_MAPPING.keys())

    def register_custom_transformation(
        self,
        data_types: type | tuple[type, ...],
        transform_func: Callable[[DataFile, Any], Any],
    ) -> None:
        """Register a custom transformation function.

        Parameters
        ----------
        data_types : type or tuple of types
            Data type(s) the function can handle.
        transform_func : callable
            Function that transforms data given a DataFile configuration.
            Signature: (data_file: DataFile, data: Any) -> Any

        Examples
        --------
        >>> def my_transform(data_file: DataFile, data: MyClass) -> MyClass:
        ...     # Custom logic here
        ...     return data
        >>> reader.register_custom_transformation(MyClass, my_transform)
        """
        register_transformation(data_types, transform_func)
