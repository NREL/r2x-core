"""Plugin system for registering and discovering parsers, exporters, and modifiers.

This module provides the plugin infrastructure that enables r2x-core's extensibility.
Applications can register model-specific parsers and exporters, system modifiers for
transformations, and filter functions for data processing.

Classes
-------
PluginComponent
    Dataclass holding parser, exporter, and config for a model plugin.
SystemModifier
    Protocol defining the signature for system modifier functions.
FilterFunction
    Protocol defining the signature for filter functions.
PluginManager
    Singleton registry for all plugin types with discovery via entry points.

Examples
--------
Register a complete model plugin:

>>> from r2x_core import PluginManager, BaseParser, BaseExporter
>>> from pydantic import BaseModel
>>>
>>> class MyConfig(BaseModel):
...     folder: str
...     year: int
>>>
>>> class MyParser(BaseParser):
...     def build_system_components(self): pass
...     def build_time_series(self): pass
>>>
>>> class MyExporter(BaseExporter):
...     def export(self): pass
...     def export_time_series(self): pass
>>>
>>> PluginManager.register_model_plugin(
...     name="my_model",
...     config=MyConfig,
...     parser=MyParser,
...     exporter=MyExporter,
... )

Register a system modifier:

>>> from r2x_core import System
>>>
>>> @PluginManager.register_system_modifier("add_storage")
... def add_storage(system: System, capacity_mw: float = 100.0, **kwargs) -> System:
...     # Add storage components
...     return system

Register a filter function:

>>> import polars as pl
>>>
>>> @PluginManager.register_filter("rename_columns")
... def rename_columns(data: pl.LazyFrame, mapping: dict[str, str]) -> pl.LazyFrame:
...     return data.rename(mapping)

Discover and use plugins:

>>> manager = PluginManager()
>>> parser_class = manager.load_parser("my_model")
>>> exporter_class = manager.load_exporter("my_model")
>>> modifier = manager.registered_modifiers["add_storage"]

See Also
--------
r2x_core.parser.BaseParser : Base class for parsers
r2x_core.exporter.BaseExporter : Base class for exporters
r2x_core.system.System : System object for modifications

Notes
-----
The plugin system uses a singleton pattern with class-level registries to ensure
plugins are registered once and discoverable across the application. Entry points
are automatically discovered on first access to PluginManager.

Plugin Discovery:
- Plugins can be registered programmatically via decorators/methods
- External packages register via entry points (group: r2x_plugin)
- Entry points are loaded lazily on first PluginManager instantiation

Design Decisions:
- Singleton pattern: Ensures single source of truth for plugins
- Class-level registries: Shared across all instances
- Flexible signatures: System modifiers accept **kwargs for context
- Warning on incomplete plugins: Allows parser-only or exporter-only registration
"""

from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from loguru import logger

if TYPE_CHECKING:
    from r2x_core.parser import BaseParser
    from r2x_core.upgrader import UpgradeStep, UpgradeType
    from r2x_core.versioning import VersioningStrategy

    from .plugin_config import PluginConfig


class SystemModifier(Protocol):
    """Protocol for system modifier functions.

    System modifiers transform a System object, optionally using additional context
    like configuration or parser data. They must return a System object.

    Parameters
    ----------
    system : System
        The system to modify
    **kwargs : dict
        Optional context (config, parser, etc.)

    Returns
    -------
    System
        Modified system object

    Examples
    --------
    >>> def add_storage(system: System, capacity_mw: float = 100.0, **kwargs) -> System:
    ...     # Add storage components
    ...     return system
    """

    def __call__(self, system: Any, **kwargs: Any) -> Any:
        """Modify and return the system."""
        ...


class FilterFunction(Protocol):
    """Protocol for filter functions.

    Filter functions process data (typically polars DataFrames) and return
    processed data. They can accept additional parameters for configuration.

    Parameters
    ----------
    data : Any
        Data to filter/process (typically pl.LazyFrame)
    **kwargs : Any
        Filter-specific parameters

    Returns
    -------
    Any
        Processed data

    Examples
    --------
    >>> def rename_columns(data: pl.LazyFrame, mapping: dict[str, str]) -> pl.LazyFrame:
    ...     return data.rename(mapping)
    """

    def __call__(self, data: Any, **kwargs: Any) -> Any:
        """Process and return data."""
        ...


@dataclass
class PluginComponent:
    """Model plugin registration data.

    Holds the parser, exporter, and config classes for a model plugin.
    At least one of parser or exporter must be provided.

    Parameters
    ----------
    config : type[PluginConfig]
        Pydantic config class for the model
    parser : type | None
        Parser class (BaseParser subclass)
    exporter : type | None
        Exporter class (BaseExporter subclass)

    Attributes
    ----------
    config : type[PluginConfig]
        Configuration class
    parser : type | None
        Parser class or None
    exporter : type | None
        Exporter class or None
    """

    config: type["PluginConfig"]
    parser: type | None = None
    exporter: type | None = None


class PluginManager:
    """Singleton registry for parsers, exporters, modifiers, and filters.

    PluginManager maintains class-level registries for all plugin types and provides
    discovery via entry points. It uses the singleton pattern to ensure a single
    source of truth for all registered plugins.

    Class Attributes
    ----------------
    _instance : PluginManager | None
        Singleton instance
    _initialized : bool
        Whether entry points have been loaded
    _registry : dict[str, PluginComponent]
        Model plugin registry (name -> PluginComponent)
    _modifier_registry : dict[str, SystemModifier]
        System modifier registry (name -> function)
    _filter_registry : dict[str, FilterFunction]
        Filter function registry (name -> function)

    Properties
    ----------
    registered_parsers : dict[str, type]
        All registered parser classes
    registered_exporters : dict[str, type]
        All registered exporter classes
    registered_modifiers : dict[str, SystemModifier]
        All registered system modifiers
    registered_filters : dict[str, FilterFunction]
        All registered filter functions

    Methods
    -------
    register_model_plugin(name, config, parser=None, exporter=None)
        Register a model plugin with parser and/or exporter
    register_system_modifier(name)
        Decorator to register a system modifier function
    register_filter(name)
        Decorator to register a filter function
    load_parser(name)
        Load a parser class by name
    load_exporter(name)
        Load an exporter class by name
    load_config_class(name)
        Load config class for a plugin

    Examples
    --------
    Register and discover plugins:

    >>> manager = PluginManager()
    >>> PluginManager.register_model_plugin("switch", SwitchConfig, SwitchParser, SwitchExporter)
    >>> parser_class = manager.load_parser("switch")
    >>> print(list(manager.registered_parsers.keys()))
    ['switch']

    Use as decorator:

    >>> @PluginManager.register_system_modifier("add_storage")
    ... def add_storage(system, **kwargs):
    ...     return system

    See Also
    --------
    PluginComponent : Data structure for model plugins
    SystemModifier : Protocol for modifier functions
    FilterFunction : Protocol for filter functions
    """

    _instance: ClassVar["PluginManager | None"] = None
    _initialized: ClassVar[bool] = False

    _registry: ClassVar[dict[str, PluginComponent]] = {}
    _modifier_registry: ClassVar[dict[str, SystemModifier]] = {}
    _filter_registry: ClassVar[dict[str, FilterFunction]] = {}
    _upgrade_registry: ClassVar[dict[str, list["UpgradeStep"]]] = {}
    _version_detector_registry: ClassVar[dict[str, Any]] = {}

    def __new__(cls) -> "PluginManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if not cls._initialized:
                cls._load_entry_point_plugins()
                cls._initialized = True
        return cls._instance

    @classmethod
    def _load_entry_point_plugins(cls) -> None:
        """Discover and load plugins from entry points.

        Looks for entry points in the 'r2x_plugin' group and calls their
        registration functions.
        """
        try:
            discovered = entry_points(group="r2x_plugin")
            for ep in discovered:
                try:
                    register_func = ep.load()
                    register_func()
                    logger.debug("Loaded plugin from entry point: {}", ep.name)
                except Exception as e:
                    logger.warning("Failed to load plugin '{}': {}", ep.name, e)
        except Exception as e:
            logger.debug("Entry point discovery not available: {}", e)

    @classmethod
    def register_model_plugin(
        cls,
        name: str,
        config: type["PluginConfig"],
        parser: type | None = None,
        exporter: type | None = None,
    ) -> None:
        """Register a model plugin.

        Registers a model plugin with its configuration and optionally parser
        and/or exporter classes. At least one of parser or exporter should be
        provided, though both None is allowed (with a warning).

        Parameters
        ----------
        name : str
            Plugin name (e.g., "switch", "plexos")
        config : type[PluginConfig]
            Pydantic configuration class
        parser : type | None, optional
            Parser class (BaseParser subclass)
        exporter : type | None, optional
            Exporter class (BaseExporter subclass)

        Warnings
        --------
        Logs a warning if both parser and exporter are None.

        Examples
        --------
        >>> PluginManager.register_model_plugin(
        ...     name="switch",
        ...     config=SwitchConfig,
        ...     parser=SwitchParser,
        ...     exporter=SwitchExporter,
        ... )

        Parser-only plugin:

        >>> PluginManager.register_model_plugin(
        ...     name="reeds",
        ...     config=ReEDSConfig,
        ...     parser=ReEDSParser,
        ... )
        """
        if parser is None and exporter is None:
            logger.warning("Plugin '{}' registered with neither parser nor exporter", name)

        cls._registry[name] = PluginComponent(
            config=config,
            parser=parser,
            exporter=exporter,
        )
        logger.debug("Registered model plugin: {}", name)

    @classmethod
    def register_system_modifier(
        cls, name: str | SystemModifier | None = None
    ) -> Callable[[SystemModifier], SystemModifier] | SystemModifier:
        """Register a system modifier function.

        System modifiers transform a System object and return the modified system.
        They can accept additional context via ``**kwargs``.

        Can be used with or without a name argument:
        - @register_system_modifier - uses function name
        - @register_system_modifier("custom_name") - uses explicit name

        Parameters
        ----------
        name : str | SystemModifier | None
            Modifier name, or the function itself if used without parentheses

        Returns
        -------
        Callable | SystemModifier
            Decorator function or decorated function

        Examples
        --------
        >>> @PluginManager.register_system_modifier
        ... def add_storage(system: System, capacity_mw: float = 100.0, **kwargs) -> System:
        ...     # Add storage components
        ...     return system

        >>> @PluginManager.register_system_modifier("custom_name")
        ... def add_storage(system: System, **kwargs) -> System:
        ...     return system
        """

        def decorator(func: SystemModifier) -> SystemModifier:
            """Register system modifiers."""
            modifier_name = name if isinstance(name, str) else func.__name__  # type: ignore[attr-defined]
            cls._modifier_registry[modifier_name] = func
            logger.debug("Registered system modifier: {}", modifier_name)
            return func

        # If used as @register_system_modifier (without parentheses)
        if callable(name):
            return decorator(name)

        # If used as @register_system_modifier("name") (with parentheses)
        return decorator

    @classmethod
    def register_filter(
        cls, name: str | FilterFunction | None = None
    ) -> Callable[[FilterFunction], FilterFunction] | FilterFunction:
        """Register a filter function.

        Filter functions process data (typically polars DataFrames) and return
        processed data.

        Can be used with or without a name argument:
        - @register_filter - uses function name
        - @register_filter("custom_name") - uses explicit name

        Parameters
        ----------
        name : str | FilterFunction | None
            Filter name, or the function itself if used without parentheses

        Returns
        -------
        Callable | FilterFunction
            Decorator function or decorated function

        Examples
        --------
        >>> @PluginManager.register_filter
        ... def rename_columns(data: pl.LazyFrame, mapping: dict[str, str]) -> pl.LazyFrame:
        ...     return data.rename(mapping)

        >>> @PluginManager.register_filter("custom_name")
        ... def process_data(data: pl.LazyFrame) -> pl.LazyFrame:
        ...     return data
        """

        def decorator(func: FilterFunction) -> FilterFunction:
            """Register a filter function."""
            filter_name = name if isinstance(name, str) else func.__name__  # type: ignore[attr-defined]
            cls._filter_registry[filter_name] = func
            logger.debug("Registered filter: {}", filter_name)
            return func

        # If used as @register_filter (without parentheses)
        if callable(name):
            return decorator(name)

        # If used as @register_filter("name") (with parentheses)
        return decorator

    @property
    def registered_parsers(self) -> dict[str, type]:
        """Get all registered parser classes.

        Returns
        -------
        dict[str, type]
            Mapping of plugin name to parser class
        """
        return {name: plugin.parser for name, plugin in self._registry.items() if plugin.parser is not None}

    @property
    def registered_exporters(self) -> dict[str, type]:
        """Get all registered exporter classes.

        Returns
        -------
        dict[str, type]
            Mapping of plugin name to exporter class
        """
        return {
            name: plugin.exporter for name, plugin in self._registry.items() if plugin.exporter is not None
        }

    @property
    def registered_modifiers(self) -> dict[str, SystemModifier]:
        """Get all registered system modifiers.

        Returns
        -------
        dict[str, SystemModifier]
            Mapping of modifier name to function
        """
        return self._modifier_registry.copy()

    @property
    def registered_filters(self) -> dict[str, FilterFunction]:
        """Get all registered filter functions.

        Returns
        -------
        dict[str, FilterFunction]
            Mapping of filter name to function
        """
        return self._filter_registry.copy()

    def load_parser(self, name: str) -> "type[BaseParser] | None":
        """Load a parser class by name.

        Parameters
        ----------
        name : str
            Plugin name

        Returns
        -------
        type[BaseParser] | None
            Parser class or None if not found

        Examples
        --------
        >>> manager = PluginManager()
        >>> parser_class = manager.load_parser("switch")
        >>> if parser_class:
        ...     parser = parser_class(config=config, data_store=store)
        """
        plugin = self._registry.get(name)
        return plugin.parser if plugin else None

    def load_exporter(self, name: str) -> type | None:
        """Load an exporter class by name.

        Parameters
        ----------
        name : str
            Plugin name

        Returns
        -------
        type | None
            Exporter class or None if not found

        Examples
        --------
        >>> manager = PluginManager()
        >>> exporter_class = manager.load_exporter("plexos")
        >>> if exporter_class:
        ...     exporter = exporter_class(config=config, system=system, data_store=store)
        """
        plugin = self._registry.get(name)
        return plugin.exporter if plugin else None

    def load_config_class(self, name: str) -> type["PluginConfig"] | None:
        """Load configuration class for a plugin.

        Parameters
        ----------
        name : str
            Plugin name

        Returns
        -------
        type[PluginConfig] | None
            Configuration class or None if not found

        Examples
        --------
        >>> manager = PluginManager()
        >>> config_class = manager.load_config_class("switch")
        >>> if config_class:
        ...     config = config_class(folder="./data", year=2030)
        """
        plugin = self._registry.get(name)
        return plugin.config if plugin else None

    def load_upgrader(self, name: str) -> list["UpgradeStep"]:
        """Load upgrade steps for a plugin.

        This is an instance method wrapper around get_upgrade_steps() for
        consistency with other load_* methods. Use this in CLI workflows
        to check if upgrades exist and get the steps.

        Parameters
        ----------
        name : str
            Plugin name

        Returns
        -------
        list[UpgradeStep]
            List of upgrade steps sorted by priority, or empty list if none

        Examples
        --------
        In Rust CLI (via PyO3):

        >>> # Python equivalent of Rust call:
        >>> manager = PluginManager()
        >>> steps = manager.load_upgrader("reeds")
        >>> if steps:
        ...     # Has upgrades - call upgrade_data before loading data_store
        ...     from r2x_core import upgrade_data
        ...     upgraded_path = upgrade_data(input_path, "reeds")
        ...     data_store = DataStore.from_json(file_mapping, upgraded_path)
        ... else:
        ...     # No upgrades - use original input path
        ...     data_store = DataStore.from_json(file_mapping, input_path)

        See Also
        --------
        get_upgrade_steps : Class method version of this function
        """
        return self.get_upgrade_steps(name)

    def get_file_mapping_path(self, plugin_name: str) -> Path | None:
        """Get the file mapping path for a registered plugin.

        This is a convenience method that loads the plugin's config class
        and delegates to its get_file_mapping_path() classmethod. This allows
        getting the file mapping path without directly importing the config class.

        Parameters
        ----------
        plugin_name : str
            Name of the registered plugin

        Returns
        -------
        Path | None
            Absolute path to the plugin's file_mapping.json, or None if the
            plugin is not registered.

        Examples
        --------
        Get file mapping path for a registered plugin:

        >>> from r2x_core import PluginManager
        >>> manager = PluginManager()
        >>> mapping_path = manager.get_file_mapping_path("reeds")
        >>> if mapping_path:
        ...     print(f"ReEDS mapping: {mapping_path}")
        ...     if mapping_path.exists():
        ...         import json
        ...         with open(mapping_path) as f:
        ...             mappings = json.load(f)

        Use in CLI tools:

        >>> import sys
        >>> plugin = sys.argv[1]  # e.g., "switch"
        >>> manager = PluginManager()
        >>> path = manager.get_file_mapping_path(plugin)
        >>> if path and path.exists():
        ...     # Load and process mappings
        ...     pass
        ... else:
        ...     print(f"No file mapping found for {plugin}")

        See Also
        --------
        PluginConfig.get_file_mapping_path : Config classmethod this delegates to
        load_config_class : Load the config class directly

        Notes
        -----
        The file may not exist even if a path is returned - the method only
        constructs the expected path based on the config module location.
        """
        config_class = self.load_config_class(plugin_name)
        if config_class is None:
            return None

        return config_class.get_file_mapping_path()

    @classmethod
    def register_upgrade_step(cls, plugin_name: str, step: "UpgradeStep") -> None:
        """Register an upgrade step for a plugin.

        Parameters
        ----------
        plugin_name : str
            Name of the plugin this upgrade step belongs to
        step : UpgradeStep
            The upgrade step to register

        Examples
        --------
        >>> from r2x_core.versioning import UpgradeStep, SemanticVersioningStrategy
        >>> def upgrade_func(data):
        ...     data["version"] = "2.0.0"
        ...     return data
        >>> step = UpgradeStep(
        ...     name="upgrade_to_v2",
        ...     func=upgrade_func,
        ...     target_version="2.0.0",
        ...     versioning_strategy=SemanticVersioningStrategy()
        ... )
        >>> PluginManager.register_upgrade_step("my_plugin", step)
        """
        if plugin_name not in cls._upgrade_registry:
            cls._upgrade_registry[plugin_name] = []

        cls._upgrade_registry[plugin_name].append(step)
        logger.debug("Registered upgrade step '{}' for plugin '{}'", step.name, plugin_name)

    @classmethod
    def get_upgrade_steps(cls, plugin_name: str) -> list["UpgradeStep"]:
        """Get all upgrade steps for a plugin, sorted by priority.

        Parameters
        ----------
        plugin_name : str
            Name of the plugin

        Returns
        -------
        list[UpgradeStep]
            List of upgrade steps sorted by priority (lower numbers first)

        Examples
        --------
        >>> steps = PluginManager.get_upgrade_steps("my_plugin")
        >>> for step in steps:
        ...     print(f"Step: {step.name}, Priority: {step.priority}")
        """
        steps = cls._upgrade_registry.get(plugin_name, [])
        return sorted(steps, key=lambda s: s.priority)

    @property
    def registered_upgrade_steps(self) -> dict[str, list["UpgradeStep"]]:
        """All registered upgrade steps by plugin name.

        Returns
        -------
        dict[str, list[UpgradeStep]]
            Dictionary mapping plugin names to their upgrade steps
        """
        return self._upgrade_registry.copy()

    @classmethod
    def register_version_detector(cls, plugin_name: str, detector: Any) -> None:
        """Register a version detector for a plugin.

        Version detectors allow plugins to specify how to read version information
        from data files before DataStore initialization. This enables version
        detection before file operations during upgrades.

        Parameters
        ----------
        plugin_name : str
            Name of the plugin this detector belongs to.
        detector : VersionDetector
            Version detector instance implementing the detect_version method.

        Examples
        --------
        Register a custom version detector:

        >>> class CustomDetector:
        ...     def detect_version(self, folder):
        ...         version_file = folder / "VERSION"
        ...         return version_file.read_text().strip() if version_file.exists() else None
        >>> PluginManager.register_version_detector("my_plugin", CustomDetector())

        Register a detector that reads from a specific CSV file:

        >>> class CSVDetector:
        ...     def detect_version(self, folder):
        ...         import polars as pl
        ...         csv_path = folder / "metadata.csv"
        ...         if csv_path.exists():
        ...             df = pl.read_csv(csv_path)
        ...             return str(df.filter(pl.col("field") == "version")["value"][0])
        ...         return None
        >>> PluginManager.register_version_detector("my_plugin", CSVDetector())

        See Also
        --------
        r2x_core.versioning.VersionDetector : Protocol for version detectors
        detect_version : Detect version for a plugin
        """
        cls._version_detector_registry[plugin_name] = detector
        logger.info("Registered version detector for plugin: {}", plugin_name)

    @classmethod
    def version_detector(
        cls, plugin_name: str
    ) -> "Callable[[Callable[[Path], str | None]], Callable[[Path], str | None]]":
        """Register a version detector function for a plugin.

        This provides a convenient decorator-based API for registering version
        detection functions. The decorated function should accept a Path and
        return an optional version string.

        Parameters
        ----------
        plugin_name : str
            Name of the plugin this detector belongs to.

        Returns
        -------
        Callable
            Decorator function that registers the version detector.

        Examples
        --------
        Register a version detector with decorator:

        >>> from pathlib import Path
        >>> @PluginManager.version_detector("my_plugin")
        ... def detect_my_version(folder: Path) -> str | None:
        ...     version_file = folder / "VERSION.txt"
        ...     if version_file.exists():
        ...         return version_file.read_text().strip()
        ...     return None

        Register a detector that reads from CSV:

        >>> import polars as pl
        >>> @PluginManager.version_detector("my_plugin")
        ... def detect_from_csv(folder: Path) -> str | None:
        ...     csv_path = folder / "metadata.csv"
        ...     if csv_path.exists():
        ...         df = pl.read_csv(csv_path)
        ...         version_row = df.filter(pl.col("field") == "version")
        ...         if len(version_row) > 0:
        ...             return str(version_row["value"][0])
        ...     return None

        See Also
        --------
        register_version_detector : Register a detector instance
        detect_version : Detect version for a plugin
        r2x_core.versioning.VersionDetector : Protocol for version detectors
        """

        def decorator(func: Callable[[Path], str | None]) -> Callable[[Path], str | None]:
            # Create a simple detector wrapper that implements the protocol
            class FunctionDetector:
                def __init__(self, func: Callable[[Path], str | None]):
                    self.func = func

                def detect_version(self, folder: Path) -> str | None:
                    return self.func(folder)

            cls.register_version_detector(plugin_name, FunctionDetector(func))
            return func

        return decorator

    @classmethod
    def upgrade_step(
        cls,
        plugin_name: str,
        target_version: str,
        versioning_strategy: "VersioningStrategy",
        upgrade_type: "UpgradeType",
        priority: int = 100,
        min_version: str | None = None,
        max_version: str | None = None,
    ) -> "Callable[[Callable], Callable]":  # type: ignore[type-arg]
        """Register an upgrade step using a decorator.

        This provides a convenient decorator-based API for registering upgrade
        functions. The decorated function should accept data and return upgraded data.

        Parameters
        ----------
        plugin_name : str
            Name of the plugin this upgrade belongs to.
        target_version : str
            The version this upgrade targets.
        versioning_strategy : VersioningStrategy
            Strategy for version management.
        upgrade_type : UpgradeType
            Type of upgrade (FILE or SYSTEM).
        priority : int, default=100
            Priority for upgrade execution (lower numbers run first).
        min_version : str | None, default=None
            Minimum version required for this upgrade.
        max_version : str | None, default=None
            Maximum version this upgrade is compatible with.

        Returns
        -------
        Callable
            Decorator function that registers the upgrade step.

        Examples
        --------
        Register a file upgrade with decorator:

        >>> from pathlib import Path
        >>> from r2x_core import UpgradeType
        >>> from r2x_core.versioning import SemanticVersioningStrategy
        >>> strategy = SemanticVersioningStrategy()
        >>>
        >>> @PluginManager.upgrade_step(
        ...     plugin_name="reeds",
        ...     target_version="2.0.0",
        ...     versioning_strategy=strategy,
        ...     upgrade_type=UpgradeType.FILE
        ... )
        ... def rename_buses_to_nodes(folder: Path) -> Path:
        ...     '''Rename buses.csv to nodes.csv.'''
        ...     old_file = folder / "buses.csv"
        ...     if old_file.exists():
        ...         old_file.rename(folder / "nodes.csv")
        ...     return folder

        Register with version constraints:

        >>> @PluginManager.upgrade_step(
        ...     plugin_name="reeds",
        ...     target_version="3.0.0",
        ...     versioning_strategy=strategy,
        ...     upgrade_type=UpgradeType.FILE,
        ...     min_version="2.0.0",
        ...     max_version="2.9.9",
        ...     priority=50
        ... )
        ... def restructure_files(folder: Path) -> Path:
        ...     '''Reorganize file structure for v3.'''
        ...     # Your upgrade logic here
        ...     return folder

        Register a system upgrade:

        >>> @PluginManager.upgrade_step(
        ...     plugin_name="reeds",
        ...     target_version="2.0.0",
        ...     versioning_strategy=strategy,
        ...     upgrade_type=UpgradeType.SYSTEM
        ... )
        ... def update_system_metadata(system):
        ...     '''Update system metadata after loading.'''
        ...     system.metadata["upgraded_to"] = "2.0.0"
        ...     return system

        See Also
        --------
        register_upgrade_step : Register an UpgradeStep instance
        UpgradeStep : Upgrade step definition
        UpgradeType : Upgrade type enumeration
        """
        from r2x_core.upgrader import UpgradeStep

        def decorator(func: Callable) -> Callable:  # type: ignore[type-arg]
            step = UpgradeStep(
                name=func.__name__,
                func=func,
                target_version=target_version,
                versioning_strategy=versioning_strategy,
                upgrade_type=upgrade_type,
                priority=priority,
                min_version=min_version,
                max_version=max_version,
            )
            cls.register_upgrade_step(plugin_name, step)
            return func

        return decorator

    @classmethod
    def detect_version(cls, plugin_name: str, folder: Path) -> str | None:
        """Detect version for a plugin without DataStore.

        This method uses the registered version detector for the specified plugin
        to read version information from data files before DataStore initialization.
        This enables upgrades that need to rename or move files before loading.

        Parameters
        ----------
        plugin_name : str
            Name of the plugin.
        folder : Path
            Path to the data folder.

        Returns
        -------
        str | None
            Detected version string, or None if no detector is registered
            or version cannot be detected.

        Examples
        --------
        Detect version before creating DataStore:

        >>> from pathlib import Path
        >>> version = PluginManager.detect_version("my_plugin", Path("/data"))
        >>> print(f"Detected version: {version}")

        Use in DataStore initialization:

        >>> version = PluginManager.detect_version("my_plugin", folder)
        >>> if version:
        ...     # Apply version-specific logic before loading files
        ...     pass

        See Also
        --------
        register_version_detector : Register a detector for a plugin
        r2x_core.versioning.VersionDetector : Protocol for version detectors

        Notes
        -----
        This method is called automatically by DataStore.from_json when an
        upgrader is specified. Plugins do not need to call this directly
        unless they need version information before DataStore creation.
        """
        detector = cls._version_detector_registry.get(plugin_name)
        if detector is None:
            logger.debug("No version detector registered for plugin: {}", plugin_name)
            return None

        try:
            version = detector.detect_version(folder)
            if version:
                logger.info("Detected version for plugin {}: {}", plugin_name, version)
            return version  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning("Version detection failed for plugin {}: {}", plugin_name, e)
            return None

    @property
    def registered_version_detectors(self) -> dict[str, Any]:
        """All registered version detectors by plugin name.

        Returns
        -------
        dict[str, VersionDetector]
            Dictionary mapping plugin names to their version detectors.
        """
        return self._version_detector_registry.copy()
