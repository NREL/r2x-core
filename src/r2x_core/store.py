"""Data Storage for managing R2X data files and their metadata."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from loguru import logger

from .datafile import DataFile
from .reader import DataReader
from .utils import filter_valid_kwargs


class DataStore:
    """Container for managing data file mappings and loading data.

    The DataStore class provides a centralized interface for managing collections of
    data files, their metadata, and coordinating data loading operations. It maintains
    a registry of DataFile instances and delegates actual file reading operations to
    a DataReader instance.

    Parameters
    ----------
    folder : str or Path, optional
        Base directory containing the data files. If None, uses current working directory.
    reader : DataReader, optional
        Custom data reader instance for handling file I/O operations. If None,
        creates a default DataReader instance.

    Attributes
    ----------
    folder : Path
        Resolved absolute path to the base data directory.
    reader : DataReader
        Data reader instance used for file operations.

    Examples
    --------
    Create a basic data store:

    >>> store = DataStore(folder="/path/to/data")
    >>> data_file = DataFile(name="generators", fpath="gen_data.csv")
    >>> store.add_data_file(data_file)
    >>> data = store.read_data_file("generators")

    Load from JSON configuration:

    >>> store = DataStore.from_json("config.json", folder="/path/to/data")
    >>> files = store.list_data_files()
    >>> print(files)
    ['generators', 'transmission', 'load']

    Batch operations:

    >>> files = [DataFile(name="gen", fpath="gen.csv"), DataFile(name="load", fpath="load.csv")]
    >>> store.add_data_files(files)
    >>> store.remove_data_files(["gen", "load"])

    See Also
    --------
    DataFile : Data file metadata and configuration
    DataReader : File reading and processing operations

    Notes
    -----
    The DataStore maintains DataFile metadata in memory but delegates actual file
    reading to the DataReader, which may implement its own caching strategies.
    The store itself does not cache file contents, only the DataFile configurations.
    """

    def __init__(
        self, folder: str | Path | None = None, reader: DataReader | None = None
    ) -> None:
        """Initialize the DataStore.

        Parameters
        ----------
        folder : str | Path | None, optional
            Base directory containing the data files. If None, uses current
            working directory. Default is None.
        reader : DataReader | None, optional
            Custom data reader instance for handling file I/O operations.
            If None, creates a default DataReader instance. Default is None.

        Raises
        ------
        FileNotFoundError
            If the specified folder does not exist.
        """
        if folder is None:
            folder = Path.cwd()

        folder_path = Path(folder)
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")

        self._reader = reader or DataReader()
        self.folder = folder_path.resolve()
        self._cache: dict[str, DataFile] = {}

    def __contains__(self, name: str) -> bool:
        """Check if a data file exists in the store.

        Parameters
        ----------
        name : str
            Name of the data file to check for.

        Returns
        -------
        bool
            True if the data file exists in the store, False otherwise.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> data_file = DataFile(name="generators", fpath="gen.csv")
        >>> store.add_data_file(data_file)
        >>> "generators" in store
        True
        >>> "missing_file" in store
        False

        Notes
        -----
        This method enables the use of the 'in' operator with DataStore instances,
        providing a convenient way to check for data file existence without
        raising exceptions.
        """
        return name in self._cache

    @classmethod
    def from_json(cls, fpath: Path | str, folder: Path | str) -> "DataStore":
        """Create a DataStore instance from a JSON configuration file.

        Parameters
        ----------
        fpath : Path or str
            Path to the JSON configuration file containing DataFile specifications.
        folder : Path or str
            Base directory containing the data files referenced in the configuration.

        Returns
        -------
        DataStore
            A new DataStore instance populated with DataFile configurations
            from the JSON file.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        TypeError
            If the JSON file does not contain a valid array structure.
        ValidationError
            If any DataFile configuration in the JSON is invalid (raised by Pydantic
            during DataFile creation).
        KeyError
            If any data file names are duplicated (raised during add_data_files).

        Examples
        --------
        Create a JSON configuration file:

        >>> config = [
        ...     {"name": "generators", "fpath": "gen_data.csv", "description": "Generator capacity data"},
        ...     {"name": "load", "fpath": "load_data.csv", "description": "Load profiles"},
        ... ]
        >>> import json
        >>> with open("config.json", "w") as f:
        ...     json.dump(config, f)

        Load the DataStore:

        >>> store = DataStore.from_json("config.json", "/path/to/data")
        >>> store.list_data_files()
        ['generators', 'load']

        See Also
        --------
        to_json : Save DataStore configuration to JSON
        DataFile : Individual data file configuration structure

        Notes
        -----
        The JSON file must contain an array of objects, where each object
        represents a valid DataFile configuration with at minimum 'name'
        and 'fpath' fields.
        """
        fpath = Path(fpath)
        if not fpath.exists():
            raise FileNotFoundError(f"Configuration file not found: {fpath}")

        with open(fpath, encoding="utf-8") as f:
            data_files_json = json.load(f)

        if not isinstance(data_files_json, list):
            raise TypeError(f"JSON file `{fpath}` is not a JSON array.")

        store = cls(folder=folder)
        data_files = [DataFile(**file_data) for file_data in data_files_json]
        store.add_data_files(data_files)
        return store

    def add_data_file(self, data_file: DataFile, overwrite: bool = False) -> None:
        """Add a single data file to the store.

        Parameters
        ----------
        data_file : DataFile
            The data file configuration to add to the store.
        overwrite : bool, optional
            Whether to overwrite an existing file with the same name.
            Default is False.

        Raises
        ------
        KeyError
            If a file with the same name already exists and overwrite is False.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> data_file = DataFile(name="generators", fpath="gen_data.csv")
        >>> store.add_data_file(data_file)

        >>> # Overwrite existing file
        >>> new_data_file = DataFile(name="generators", fpath="new_gen_data.csv")
        >>> store.add_data_file(new_data_file, overwrite=True)

        See Also
        --------
        add_data_files : Add multiple data files at once
        remove_data_file : Remove a data file from the store
        """
        if data_file.name in self._cache and not overwrite:
            msg = f"Data file '{data_file.name}' already exists. "
            msg += "Use overwrite=True to replace it."
            raise KeyError(msg)

        self._cache[data_file.name] = data_file
        logger.debug("Added data file '{}' to store", data_file.name)

    def add_data_files(
        self, data_files: Iterable[DataFile], overwrite: bool = False
    ) -> None:
        """Add multiple data files to the store.

        Parameters
        ----------
        data_files : Iterable[DataFile]
            Collection of data file configurations to add to the store.
        overwrite : bool, optional
            Whether to overwrite existing files with the same names.
            Default is False.

        Raises
        ------
        KeyError
            If any file with the same name already exists and overwrite is False.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> files = [
        ...     DataFile(name="generators", fpath="gen.csv"),
        ...     DataFile(name="transmission", fpath="trans.csv"),
        ...     DataFile(name="load", fpath="load.csv")
        ... ]
        >>> store.add_data_files(files)

        See Also
        --------
        add_data_file : Add a single data file
        remove_data_files : Remove multiple data files
        """
        for data_file in data_files:
            self.add_data_file(data_file, overwrite=overwrite)

    def remove_data_file(self, name: str) -> None:
        """Remove a data file from the store.

        Parameters
        ----------
        name : str
            Name of the data file to remove.

        Raises
        ------
        KeyError
            If the specified file name is not present in the store.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> data_file = DataFile(name="generators", fpath="gen.csv")
        >>> store.add_data_file(data_file)
        >>> store.remove_data_file("generators")

        See Also
        --------
        remove_data_files : Remove multiple data files at once
        add_data_file : Add a data file to the store
        """
        if name not in self._cache:
            raise KeyError(f"Data file '{name}' not found in store.")

        del self._cache[name]
        logger.debug("Removed data file '{}' from store", name)

    def remove_data_files(self, names: Iterable[str]) -> None:
        """Remove multiple data files from the store.

        Parameters
        ----------
        names : Iterable[str]
            Collection of data file names to remove.

        Raises
        ------
        KeyError
            If any specified file name is not present in the store.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> files = [
        ...     DataFile(name="gen", fpath="gen.csv"),
        ...     DataFile(name="load", fpath="load.csv")
        ... ]
        >>> store.add_data_files(files)
        >>> store.remove_data_files(["gen", "load"])

        See Also
        --------
        remove_data_file : Remove a single data file
        add_data_files : Add multiple data files
        """
        for name in names:
            self.remove_data_file(name)

    def get_data_file_by_name(self, name: str) -> DataFile:
        """Retrieve a data file configuration by name.

        Parameters
        ----------
        name : str
            Name of the data file to retrieve.

        Returns
        -------
        DataFile
            The data file configuration object.

        Raises
        ------
        KeyError
            If the specified file name is not present in the store.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> data_file = store.get_data_file_by_name("generators")
        >>> print(data_file.fpath)
        generators.csv

        See Also
        --------
        list_data_files : Get all data file names
        read_data_file : Load the actual file contents
        """
        if name not in self._cache:
            available_files = list(self._cache.keys())
            raise KeyError(
                f"'{name}' not present in store. Available files: {available_files}"
            )

        return self._cache[name]

    def list_data_files(self) -> list[str]:
        """List all data file names in the store.

        Returns
        -------
        list[str]
            Sorted list of all data file names present in the store.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> files = [
        ...     DataFile(name="generators", fpath="gen.csv"),
        ...     DataFile(name="load", fpath="load.csv")
        ... ]
        >>> store.add_data_files(files)
        >>> store.list_data_files()
        ['generators', 'load']

        See Also
        --------
        get_data_file_by_name : Get a specific data file configuration
        __contains__ : Check if a specific file exists
        """
        return sorted(self._cache.keys())

    def read_data_file(self, name: str, use_cache: bool = True) -> Any:
        """Load data from a file using the configured reader.

        Parameters
        ----------
        name : str
            Name of the data file to load.
        use_cache : bool, optional
            Whether to use cached data if available. Default is True.

        Returns
        -------
        Any
            The loaded data, type depends on file type and reader configuration.

        Raises
        ------
        KeyError
            If the specified file name is not present in the store.
        FileNotFoundError
            If the file does not exist and is not marked as optional.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> data_file = DataFile(name="generators", fpath="gen.csv")
        >>> store.add_data_file(data_file)
        >>> data = store.read_data_file("generators")

        See Also
        --------
        get_data_file_by_name : Get the file configuration
        clear_cache : Clear the reader's cache
        """
        if name not in self:
            raise KeyError(f"'{name}' not present in store.")

        data_file = self._cache[name]
        return self.reader.read_data_file(self.folder, data_file, use_cache=use_cache)

    def clear_cache(self) -> None:
        """Clear both the data reader's cache and the data store's file configurations.

        This method clears the underlying DataReader's cache of loaded file contents
        and also removes all data file configurations from the DataStore.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> # Load some data files...
        >>> store.clear_cache()  # Clear cached file contents and configurations

        See Also
        --------
        reader : Access the underlying DataReader instance
        """
        self.reader.clear_cache()
        self._cache.clear()
        logger.debug("Cleared data reader cache and data store configurations")

    def to_json(self, fpath: str | Path, **model_dump_kwargs: dict[str, Any]) -> None:
        """Save the DataStore configuration to a JSON file.

        Parameters
        ----------
        fpath : str or Path
            Path where the JSON configuration file will be saved.
        **model_dump_kwargs : dict[str, Any]
            Additional keyword arguments passed to the DataFile.model_dump method
            for controlling serialization behavior.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> files = [DataFile(name="generators", fpath="gen.csv"), DataFile(name="load", fpath="load.csv")]
        >>> store.add_data_files(files)
        >>> store.to_json("config.json")

        >>> # Save with custom serialization options
        >>> store.to_json("config.json", exclude_none=True)

        See Also
        --------
        from_json : Load DataStore configuration from JSON
        DataFile.model_dump : Individual file serialization method

        Notes
        -----
        The resulting JSON file will contain an array of DataFile configurations
        that can be loaded back using the `from_json` class method.
        """
        json_data = [
            data_file.model_dump(
                mode="json",
                round_trip=True,
                **filter_valid_kwargs(data_file.model_dump, model_dump_kwargs),
            )
            for data_file in self._cache.values()
        ]

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info("Created JSON file at {}", fpath)

    @property
    def reader(self) -> DataReader:
        """Get the data reader instance.

        Returns
        -------
        DataReader
            The configured data reader instance.

        Examples
        --------
        >>> store = DataStore("/path/to/data")
        >>> reader = store.reader
        >>> reader.clear_cache()
        """
        return self._reader

    @reader.setter
    def reader(self, reader: DataReader) -> None:
        """Set a new data reader instance.

        Parameters
        ----------
        reader : DataReader
            New data reader instance to use.

        Raises
        ------
        TypeError
            If reader is not a valid DataReader instance.
        """
        if not isinstance(reader, DataReader):
            raise TypeError("reader must be a valid DataReader instance.")
        self._reader = reader
