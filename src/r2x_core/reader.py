"""Data Reader for loading files based on their type."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from .datafile import DataFile
from .exceptions import ReaderError
from .file_readers import read_file_by_type
from .file_types import EXTENSION_MAPPING
from .processors import apply_transformation, register_transformation


class DataReader:
    """Reader class for loading data files.

    The DataReader handles the actual file I/O operations,
    while delegating file-type-specific reading logic to
    single dispatch methods.
    """

    def __init__(self) -> None:
        """Initialize the data reader."""

    def _resolve_glob_pattern(self, data_file: DataFile, folder: Path) -> Path | None:
        """Resolve a glob pattern to a single file path.

        Parameters
        ----------
        folder : Path
            Base directory to search in.
        data_file : DataFile
            Data file configuration with glob pattern.

        Returns
        -------
        Path | None
            Resolved file path, or None if optional and no matches found.

        Raises
        ------
        ValueError
            If glob pattern matches zero or multiple files (for required files).
        """
        pattern = data_file.glob
        assert pattern is not None, "DataFile must have a glob pattern"
        if data_file.is_optional:
            logger.debug("Optional glob pattern '{}' matched no files, returning None", pattern)
            return None

        matches = [p for p in folder.glob(pattern) if p.is_file()]
        if len(matches) == 0:
            msg = (
                f"No files found matching pattern '{pattern}' in {folder}\n"
                f"Suggestions:\n"
                f"  - Verify the pattern syntax (e.g., '*.xml' for any XML file)\n"
                f"  - Check that the directory contains files with the expected extension\n"
                f"  - Verify the base directory is correct"
            )
            raise ValueError(msg)

        if len(matches) > 1:
            file_list = "\n".join(f"  - {m.name}" for m in sorted(matches))
            msg = (
                f"Multiple files matched pattern '{pattern}' in {folder}:\n"
                f"{file_list}\n"
                f"Suggestions:\n"
                f"  - Use a more specific pattern (e.g., 'model_*.xml' instead of '*.xml')\n"
                f"  - Use the exact filename in 'fpath' instead of a glob pattern\n"
                f"  - Remove extra files from the directory"
            )
            raise ValueError(msg)

        logger.debug("Glob pattern '{}' resolved to: {}", pattern, matches[0].name)
        return matches[0]

    def _get_file_path(self, data_file: DataFile, folder: Path) -> Path | None:
        """Get the resolved file path from fpath, relative_fpath, or glob pattern.

        Parameters
        ----------
        data_file : DataFile
            Data file configuration.
        folder : Path
            Base directory containing the data files.

        Returns
        -------
        Path | None
            Resolved file path, or None if optional and not found.
        """
        assert (
            data_file.fpath is not None or data_file.relative_fpath is not None or data_file.glob is not None
        ), "DataFile must have fpath, relative_fpath, or glob"

        if data_file.glob is not None:
            return self._resolve_glob_pattern(data_file, folder)

        if data_file.relative_fpath is not None:
            # relative_fpath is relative to the folder
            rel_path = (
                Path(data_file.relative_fpath)
                if isinstance(data_file.relative_fpath, str)
                else data_file.relative_fpath
            )
            fpath = folder / rel_path
            logger.trace("Resolved relative_fpath={} for file={}", fpath, data_file.name)
            return fpath

        assert data_file.fpath is not None
        # fpath is absolute or absolute-like, use as-is
        logger.trace("Resolved absolute fpath={} for file={}", data_file.fpath, data_file.name)
        return data_file.fpath

    def read_data_file(
        self,
        data_file: DataFile,
        folder: Path,
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
        file_path = self._get_file_path(data_file, folder)

        if file_path is None:
            logger.debug("Optional file {} not found, returning None", data_file.name)
            return None

        if not file_path.exists() and data_file.is_optional:
            logger.debug("Optional file {} not found, returning None", file_path)
            return None

        if not file_path.exists() and not data_file.is_optional:
            msg = f"Missing required file: {file_path}"
            raise FileNotFoundError(msg)

        # Check for custom reader function first
        reader_kwargs = data_file.reader_kwargs or {}
        if data_file.reader_function is not None:
            logger.debug(
                "Attempting to read data_file{} with reader_function={}",
                data_file.name,
                data_file.reader_function,
            )
            raw_data = data_file.reader_function(file_path, **reader_kwargs)
        else:
            file_type_instance = data_file.file_type
            logger.trace(
                "Attempting to read data_file={} with {}", data_file.name, type(file_type_instance).__name__
            )
            raw_data = read_file_by_type(file_type_instance, file_path, **reader_kwargs)

        processed_data = apply_transformation(data_file, raw_data, placeholders)

        if processed_data.is_err():
            raise ReaderError(processed_data.error)

        processed_data = processed_data.unwrap()

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
