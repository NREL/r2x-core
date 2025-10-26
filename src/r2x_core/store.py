"""Data Storage for managing R2X data files and their metadata.

Example usage of :class:`DataStore`:

Initialize a DataStore from a folder containing data files:

>>> from pathlib import Path
>>> from r2x_core.store import DataStore
>>> store = DataStore(folder_path="./data")
>>> store.list_data()
['file1', 'file2']

Add data files and read them:

>>> data = store.read_data("file1")
>>> "file1" in store
True

Export store configuration to JSON:

>>> store.to_json("config.json")
"""

import json
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError

from r2x_core.exceptions import UpgradeError
from r2x_core.upgrader_utils import run_datafile_upgrades

from .datafile import DataFile, create_data_files_from_records
from .plugin_config import PluginConfig
from .reader import DataReader
from .upgrader import PluginUpgrader
from .utils import backup_folder, filter_valid_kwargs


class DataStore:
    """Container for managing data file mappings and loading data.

    The :class:`DataStore` provides a high-level interface for managing
    a collection of :class:`DataFile` instances, including loading data,
    caching, and executing version upgrades. It can be initialized from
    a folder path, JSON configuration, or :class:`PluginConfig`.

    Parameters
    ----------
    folder_path : str | Path | None, optional
        Path to the folder containing data files. If None, uses current
        working directory. Default is None.
    reader : DataReader | None, optional
        Custom :class:`DataReader` instance. If None, a default reader
        is created. Default is None.
    upgrader : PluginUpgrader | None, optional
        Version upgrader strategy. If None, no upgrading is performed.
        Default is None.

    Attributes
    ----------
    folder : Path
        The resolved folder path containing the data files.
    reader : DataReader
        The data reader instance used to load data.
    upgrader : PluginUpgrader | None
        The version upgrader strategy, if provided.

    Methods
    -------
    from_data_files(data_files, folder_path, upgrader)
        Create a DataStore from a list of DataFile instances.
    from_json(json_fpath, folder_path, upgrader)
        Create a DataStore from a JSON configuration file.
    from_plugin_config(plugin_config, folder_path, upgrader)
        Create a DataStore from a PluginConfig instance.
    add_data(*data_files, overwrite)
        Add one or more DataFile instances to the store.
    read_data(name, use_cache, placeholders)
        Load data from a file by name.
    list_data()
        List all data file names in the store.
    remove_data(*names)
        Remove one or more data files from the store.
    clear_cache()
        Clear internal caches.
    to_json(fpath, **model_dump_kwargs)
        Export store configuration to JSON.
    upgrade_data(backup, upgrader_context)
        Run version upgrades on data files.

    See Also
    --------
    :class:`DataFile` : Individual data file configuration.
    :class:`DataReader` : Reader for loading data files.
    :class:`PluginUpgrader` : Version upgrade strategy.
    :class:`PluginConfig` : Plugin configuration source.

    Examples
    --------
    Create a DataStore from a folder:

    >>> store = DataStore(folder_path="./data")
    >>> files = store.list_data()

    Load data with caching:

    >>> data = store.read_data("file1", use_cache=True)

    Add data files and export configuration:

    >>> from r2x_core.datafile import DataFile
    >>> df = DataFile(name="new_file", path="data.csv")
    >>> store.add_data(df)
    >>> store.to_json("config.json")

    Notes
    -----
    All data file names must be unique within a store. The reader cache
    is managed separately from the file configuration cache.
    """

    def __init__(
        self,
        /,
        folder_path: str | Path | None = None,
        *,
        reader: DataReader | None = None,
        upgrader: PluginUpgrader | None = None,
    ) -> None:
        """Initialize the DataStore."""
        if folder_path is None:
            logger.debug("Starting store in current directory: {}", str(Path.cwd()))
            folder_path = Path.cwd()

        if isinstance(folder_path, str):
            folder_path = Path(folder_path)

        if not folder_path.exists():
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")

        self._reader = reader or DataReader()
        self._folder = folder_path.resolve()
        self._cache: dict[str, DataFile] = {}
        self._upgrader = upgrader
        logger.debug("Initialized DataStore with folder: {}", self.folder)

    @property
    def upgrader(self) -> PluginUpgrader | None:
        """Return the :class:`PluginUpgrader` instance, if provided."""
        return self._upgrader

    @property
    def folder(self) -> Path:
        """Return the resolved folder path containing data files."""
        return self._folder

    @property
    def reader(self) -> DataReader:
        """Return the :class:`DataReader` instance."""
        return self._reader

    def __getitem__(self, key: str) -> DataFile:
        """Access data file by name. Equivalent to :meth:`_get_data_file_by_name`."""
        return self._get_data_file_by_name(name=key)

    def __contains__(self, name: str) -> bool:
        """Check if a :class:`DataFile` exists in the store."""
        return name in self._cache

    @classmethod
    def from_data_files(
        cls,
        data_files: list[DataFile],
        folder_path: Path | str | None = None,
        upgrader: PluginUpgrader | None = None,
    ) -> "DataStore":
        """Create a :class:`DataStore` from a list of :class:`DataFile` instances.

        Parameters
        ----------
        data_files : list[DataFile]
            List of DataFile instances to add to the store.
        folder_path : Path | str | None, optional
            Path to the folder containing data files. Default is None.
        upgrader : PluginUpgrader | None, optional
            Version upgrader strategy. Default is None.

        Returns
        -------
        DataStore
            New DataStore instance with provided data files.
        """
        store = cls(folder_path, upgrader=upgrader)
        store.add_data(*data_files)
        return store

    @classmethod
    def from_json(
        cls,
        json_fpath: Path | str,
        folder_path: Path | str,
        upgrader: PluginUpgrader | None = None,
    ) -> "DataStore":
        """Create a :class:`DataStore` from a JSON configuration file.

        Parameters
        ----------
        json_fpath : Path | str
            Path to the JSON file containing data file configurations.
        folder_path : Path | str
            Path to the folder containing data files.
        upgrader : PluginUpgrader | None, optional
            Version upgrader strategy. Default is None.

        Returns
        -------
        DataStore
            New DataStore instance with data files from JSON.

        Raises
        ------
        FileNotFoundError
            If folder_path or json_fpath does not exist.
        TypeError
            If JSON file is not a JSON array.
        ValidationError
            If data files in JSON are invalid.
        """
        folder_path = Path(folder_path)
        json_fpath = Path(json_fpath)

        if not folder_path.exists():
            raise FileNotFoundError(f"Data folder not found: {folder_path}")

        if not json_fpath.exists():
            raise FileNotFoundError(f"Configuration file not found: {json_fpath}")

        with open(json_fpath, encoding="utf-8") as f:
            data_files_json = json.load(f)

        if not isinstance(data_files_json, list):
            msg = f"JSON file `{json_fpath}` is not a JSON array."
            raise TypeError(msg)

        if upgrader:
            upgrader.upgrade_data_files(folder_path=folder_path)

        result = create_data_files_from_records(data_files_json, folder_path=folder_path)
        if result.is_err():
            errors = result.err()
            line_errors: list[Any] = [e for err in errors for e in err.errors()]
            raise ValidationError.from_exception_data(
                title=f"Invalid data files in {json_fpath}",
                line_errors=line_errors,
            )
        data_files = result.unwrap()
        return cls.from_data_files(folder_path=folder_path, data_files=data_files, upgrader=upgrader)

    @classmethod
    def from_plugin_config(
        cls,
        plugin_config: PluginConfig,
        folder_path: Path | str,
        upgrader: PluginUpgrader | None = None,
    ) -> "DataStore":
        """Create a :class:`DataStore` from a :class:`PluginConfig` instance.

        Parameters
        ----------
        plugin_config : PluginConfig
            Plugin configuration containing file mappings.
        folder_path : Path | str
            Path to the folder containing data files.
        upgrader : PluginUpgrader | None, optional
            Version upgrader strategy. Default is None.

        Returns
        -------
        DataStore
            New DataStore instance with data files from plugin config.
        """
        json_fpath = plugin_config.file_mapping_path
        logger.info("Loading DataStore from plugin config: {}", type(plugin_config).__name__)
        logger.debug("File mapping path: %s", json_fpath)
        return cls.from_json(json_fpath=json_fpath, folder_path=folder_path, upgrader=upgrader)

    def add_data(self, *data_files: DataFile, overwrite: bool = False) -> None:
        """Add one or more :class:`DataFile` instances to the store.

        Parameters
        ----------
        *data_files : DataFile
            Variable number of DataFile instances to add.
        overwrite : bool, optional
            If True, overwrite existing data files with the same name.
            Default is False.

        Raises
        ------
        TypeError
            If any item is not a DataFile instance.
        KeyError
            If a data file with the same name exists and overwrite is False.
        """
        return self._add_data_file(*data_files, overwrite=overwrite)

    def clear_cache(self) -> None:
        """Clear both the :class:`DataReader` cache and store file configurations."""
        self.reader.clear_cache()
        self._cache.clear()
        logger.debug("Cleared data reader cache and data store configurations")

    def list_data(self) -> list[str]:
        """List all data file names in the store.

        Returns
        -------
        list[str]
            Sorted list of all data file names.
        """
        return sorted(self._cache.keys())

    def read_data(
        self, name: str, *, use_cache: bool = True, placeholders: dict[str, Any] | None = None
    ) -> Any:
        """Load data from a file using the configured :class:`DataReader`.

        Parameters
        ----------
        name : str
            Name of the data file to load.
        use_cache : bool, optional
            If True, use cached data if available. Default is True.
        placeholders : dict[str, Any] | None, optional
            Placeholder values for template substitution. Default is None.

        Returns
        -------
        Any
            Loaded data from the file.

        Raises
        ------
        KeyError
            If the data file name is not in the store.
        """
        return self._read_data_file_by_name(name=name, use_cache=use_cache, placeholders=placeholders)

    def remove_data(self, *names: str) -> None:
        """Remove one or more data files from the store.

        Parameters
        ----------
        *names : str
            Variable number of data file names to remove.
            Examples: remove_data("file1", "file2")

        Raises
        ------
        KeyError
            If any data file name is not in the store.
        """
        for name in names:
            if name not in self._cache:
                raise KeyError(f"Data file '{name}' not found in store.")

        for name in names:
            del self._cache[name]
            logger.debug("Removed data file '{}' from store", name)

    def to_json(self, fpath: str | Path, **model_dump_kwargs: dict[str, Any]) -> None:
        """Save the :class:`DataStore` configuration to a JSON file.

        Parameters
        ----------
        fpath : str | Path
            Path where JSON file will be written.
        **model_dump_kwargs : dict[str, Any]
            Additional keyword arguments passed to :meth:`DataFile.model_dump`.

        Notes
        -----
        Output JSON is formatted with 2-space indentation and includes Unicode.
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

    def upgrade_data(self, backup: bool = False, upgrader_context: dict[str, Any] | None = None) -> None:
        """Run version upgrades on data files.

        Parameters
        ----------
        backup : bool, optional
            If True, create a backup of the folder before upgrading. Default is False.
        upgrader_context : dict[str, Any] | None, optional
            Context dictionary passed to upgrade steps. Default is None.

        Raises
        ------
        UpgradeError
            If upgrader is not configured or upgrade fails.

        Notes
        -----
        Requires a :class:`PluginUpgrader` instance provided at initialization.
        """
        return self._upgrade_data(backup=backup, upgrader_context=upgrader_context)

    def _add_data_file(self, *data_files: DataFile, overwrite: bool = False) -> None:
        """Add :class:`DataFile` instances to the store (internal).

        Parameters
        ----------
        *data_files : DataFile
            Variable number of DataFile instances.
        overwrite : bool, optional
            If True, overwrite existing data files. Default is False.
        """
        if any(not isinstance(data_file, DataFile) for data_file in data_files):
            raise TypeError

        if any(data_file.name in self._cache for data_file in data_files) and not overwrite:
            msg = "Some data files already exists with the same name. "
            msg += "Pass overwrite=True to replace it."
            raise KeyError(msg)

        for data_file in data_files:
            self._cache[data_file.name] = data_file
            logger.debug("Added data file '{}' to store", data_file.name)
        return

    def _get_data_file_by_name(self, name: str) -> DataFile:
        """Retrieve a :class:`DataFile` configuration by name (internal).

        Parameters
        ----------
        name : str
            Name of the data file.

        Returns
        -------
        DataFile
            The requested data file.

        Raises
        ------
        KeyError
            If the data file name is not in the store.
        """
        if name not in self._cache:
            available_files = list(self._cache.keys())
            raise KeyError(f"'{name}' not present in store. Available files: {available_files}")

        return self._cache[name]

    def _read_data_file_by_name(
        self, /, *, name: str, use_cache: bool = True, placeholders: dict[str, Any] | None = None
    ) -> Any:
        """Load data from a file by name (internal).

        Parameters
        ----------
        name : str
            Name of the data file.
        use_cache : bool, optional
            If True, use cached data. Default is True.
        placeholders : dict[str, Any] | None, optional
            Placeholder values for substitution. Default is None.

        Returns
        -------
        Any
            Loaded data.

        Raises
        ------
        KeyError
            If the data file name is not in the store.
        """
        if name not in self:
            raise KeyError(f"'{name}' not present in store.")

        data_file = self._cache[name]
        return self.reader.read_data_file(
            data_file, self.folder, use_cache=use_cache, placeholders=placeholders
        )

    def _upgrade_data(self, backup: bool = False, upgrader_context: dict[str, Any] | None = None) -> None:
        """Run version upgrades (internal).

        Parameters
        ----------
        backup : bool, optional
            If True, create a folder backup. Default is False.
        upgrader_context : dict[str, Any] | None, optional
            Context for upgrade steps. Default is None.

        Raises
        ------
        UpgradeError
            If upgrader is not configured or upgrade fails.
        """
        if not self._upgrader:
            msg = "Instance of store does not have an upgrader class."
            raise UpgradeError(msg)

        from .upgrader_utils import UpgradeType

        version = self._upgrader.version  # Upgrader instance holds the current version of the plugin.
        logger.info(
            "Detected version '{}' for upgrader '{}' in folder: {}",
            version if version else "unknown",
            type(self._upgrader).__name__,
            self._folder,
        )
        registered_file_ops_steps = [s for s in self._upgrader.steps if s.upgrade_type == UpgradeType.FILE]
        if not registered_file_ops_steps:
            logger.debug("Not registered steps found. Skipping upgrader.")
            return None
        logger.warning(
            "Applying {} file upgrade steps for upgrader '{}'",
            len(registered_file_ops_steps),
            type(self._upgrader).__name__,
        )

        if backup:
            result_backup = backup_folder(self._folder)

            if result_backup.is_err():
                raise UpgradeError(result_backup.err())

        result = run_datafile_upgrades(
            steps=registered_file_ops_steps,
            folder_path=self._folder,
            current_version=version,
            upgrader_context=upgrader_context,
            strategy=self._upgrader.strategy,
        )
        if result.is_err():
            raise UpgradeError(result.err())
        return
