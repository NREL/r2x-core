"""Data Reader for loading files based on their type."""

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loguru import logger

from .datafile import DataFile
from .file_readers import read_file_by_type
from .file_types import EXTENSION_MAPPING
from .processors import apply_transformation, register_transformation

MAX_CACHE_SIZE = 100


class DataReader:
    """Reader class for loading data files with caching support.

    The DataReader handles the actual file I/O operations and caching
    strategies, while delegating file-type-specific reading logic to
    single dispatch methods.

    Parameters
    ----------
    max_cache_size : int, optional
        Maximum number of files to keep in cache. Default is 100.

    Attributes
    ----------
    max_cache_size : int
        Maximum cache size limit.
    """

    def __init__(self, max_cache_size: int = MAX_CACHE_SIZE) -> None:
        self._cache: dict[str, Any] = {}
        self.max_cache_size = max_cache_size

    def _generate_cache_key(self, folder: Path, data_file: DataFile) -> str:
        """Generate a unique cache key for a file.

        Parameters
        ----------
        folder : Path
            Base directory containing the data files.
        data_file : DataFile
            Data file configuration.

        Returns
        -------
        str
            Unique cache key for the file.
        """
        file_path = folder / data_file.fpath
        # Include file path, modification time, and DataFile hash
        mtime = file_path.stat().st_mtime if file_path.exists() else 0
        key_data = f"{file_path}:{mtime}:{data_file.name}:{hash(data_file)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def read_data_file(
        self, folder: Path, data_file: DataFile, use_cache: bool = True
    ) -> Any:
        """Read a data file using cache if available.

        Parameters
        ----------
        folder : Path
            Base directory containing the data files.
        data_file : DataFile
            Data file configuration with metadata.
        use_cache : bool, optional
            Whether to use cached data if available. Default is True.

        Returns
        -------
        Any
            The loaded data, type depends on file type.

        Raises
        ------
        FileNotFoundError
            If the file does not exist and is not optional.
        """
        cache_key = self._generate_cache_key(folder, data_file)

        # Return cached data if available and requested
        if use_cache and cache_key in self._cache:
            logger.debug("Loading {} from cache", data_file.name)
            return self._cache[cache_key]

        file_path = folder / data_file.fpath
        if not file_path.exists():
            if data_file.is_optional:
                logger.debug("Optional file {} not found, returning None", file_path)
                return None
            else:
                msg = f"Missing required file: {file_path}"
                raise FileNotFoundError(msg)

        # Check for custom reader function first
        if data_file.reader_function is not None:
            logger.debug(
                "Using custom callable reader function for: {}", data_file.name
            )
            raw_data = data_file.reader_function(file_path)
        else:
            # Use single dispatch to read based on file type
            file_type_instance = data_file.file_type
            logger.debug(
                "Reading file {} as {}", file_path, type(file_type_instance).__name__
            )
            raw_data = read_file_by_type(file_type_instance, file_path)

        processed_data = apply_transformation(data_file, raw_data)

        if use_cache:
            self._add_to_cache(cache_key, processed_data)

        return processed_data

    def _add_to_cache(self, cache_key: str, data: Any) -> None:
        """Add data to cache, managing cache size limits.

        Parameters
        ----------
        cache_key : str
            Unique key for the cached data.
        data : Any
            Data to cache.
        """
        # Simple FIFO cache management
        if len(self._cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug("Cache full, removed oldest entry: {}", oldest_key)

        self._cache[cache_key] = data
        logger.debug("Added to cache: {}", cache_key)

    def clear_cache(self) -> None:
        """Clear cached files.

        Parameters
        ----------
        pattern : str, optional
            If provided, only clear cache entries matching this pattern.
            If None, clears all cached data.
        """
        self._cache.clear()
        logger.debug("Cleared all cache entries")
        return

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about the current cache state.

        Returns
        -------
        dict[str, Any]
            Cache statistics and information.
        """
        return {
            "file_count": len(self._cache),
            "max_size": self.max_cache_size,
            "cache_keys": list(self._cache.keys()),
        }

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
        transform_func: Callable[[Any, DataFile], Any],
    ) -> None:
        """Register a custom transformation function.

        Parameters
        ----------
        data_types : type or tuple of types
            Data type(s) the function can handle.
        transform_func : callable
            Function that transforms data given a DataFile configuration.

        Examples
        --------
        >>> def my_transform(data: MyClass, data_file: DataFile) -> MyClass:
        ...     # Custom logic here
        ...     return data
        >>> reader.register_custom_transformation(MyClass, my_transform)
        """
        register_transformation(data_types, transform_func)
