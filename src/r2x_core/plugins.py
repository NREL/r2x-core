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

    Container holding parser, exporter, config, and upgrader classes for a model
    plugin. Used by :class:`PluginManager` to store and retrieve complete plugin
    definitions. At least one of parser or exporter must be provided.

    Parameters
    ----------
    config : type[PluginConfig]
        Pydantic config class defining model-specific parameters
    parser : type | None
        Parser class implementing :class:`BaseParser`
    exporter : type | None
        Exporter class implementing :class:`BaseExporter`
    upgrader : type[DataUpgrader] | None
        Optional upgrader class implementing data folder migrations

    Attributes
    ----------
    config : type[PluginConfig]
        Configuration class for the model
    parser : type | None
        Parser class or None
    exporter : type | None
        Exporter class or None
    upgrader : type[DataUpgrader] | None
        Upgrader class or None

    See Also
    --------
    :class:`PluginManager` : Registry manager for plugin components
    :class:`BaseParser` : Base parser class
    :class:`BaseExporter` : Base exporter class

    Examples
    --------
    Create a plugin component for a model plugin:

    >>> from r2x_core.plugins import PluginComponent
    >>> from my_model import MyParser, MyExporter, MyConfig
    >>>
    >>> component = PluginComponent(
    ...     config=MyConfig,
    ...     parser=MyParser,
    ...     exporter=MyExporter,
    ...     upgrader=None
    ... )
    >>> component.parser
    <class 'my_model.MyParser'>

    Notes
    -----
    The dataclass is frozen (immutable) to prevent accidental modifications
    after registration.
    """

    config: type["PluginConfig"]
    parser: type | None = None
    exporter: type | None = None
    upgrader: type | None = None


class PluginManager:
    """Singleton registry for parsers, exporters, system modifiers, and filters.

    PluginManager is the central plugin registry maintaining class-level registries
    for all plugin types. It supports both programmatic registration via decorators
    and automatic discovery via entry points (group: r2x_plugin). Uses the singleton
    pattern to ensure a single source of truth for all registered plugins across
    the application lifecycle.

    Class Attributes
    ----------------
    _instance : PluginManager | None
        Singleton instance
    _initialized : bool
        Whether entry points have been loaded
    _registry : dict[str, PluginComponent]
        Model plugin registry mapping name to PluginComponent
    _modifier_registry : dict[str, SystemModifier]
        System modifier registry mapping name to modifier function
    _filter_registry : dict[str, FilterFunction]
        Filter function registry mapping name to filter function

    Properties
    ----------
    registered_parsers : dict[str, type]
        All registered parser classes by model name
    registered_exporters : dict[str, type]
        All registered exporter classes by model name
    registered_modifiers : dict[str, SystemModifier]
        All registered system modifier functions by name
    registered_filters : dict[str, FilterFunction]
        All registered filter functions by name

    Methods
    -------
    register_model_plugin(name, config, parser=None, exporter=None, upgrader=None)
        Register a complete model plugin
    register_system_modifier(name)
        Decorator to register a system modifier function
    register_filter(name)
        Decorator to register a filter function
    load_parser(name)
        Load a parser class by name
    load_exporter(name)
        Load an exporter class by name
    load_config_class(name)
        Load configuration class for a plugin by name
    get_upgrader(config_class)
        Get upgrader class for a configuration class
    get_file_mapping_path(plugin_name)
        Get file mapping path for a plugin

    See Also
    --------
    :class:`PluginComponent` : Data structure for model plugin registration
    :class:`SystemModifier` : Protocol for system modifier functions
    :class:`FilterFunction` : Protocol for filter functions
    :class:`PluginConfig` : Base configuration class for plugins

    Examples
    --------
    Register and use a complete model plugin:

    >>> from r2x_core.plugins import PluginManager, PluginComponent
    >>> from my_model import MyConfig, MyParser, MyExporter
    >>>
    >>> manager = PluginManager()
    >>> PluginManager.register_model_plugin(
    ...     name="my_model",
    ...     config=MyConfig,
    ...     parser=MyParser,
    ...     exporter=MyExporter
    ... )
    >>> parser_class = manager.load_parser("my_model")

    Register a system modifier with the decorator:

    >>> @PluginManager.register_system_modifier("add_storage")
    ... def add_storage(system: System, capacity_mw: float = 100.0, **kwargs) -> System:
    ...     # Add storage to system
    ...     return system

    Register a filter function with the decorator:

    >>> @PluginManager.register_filter("rename_cols")
    ... def rename_cols(data: pl.LazyFrame, mapping: dict[str, str]) -> pl.LazyFrame:
    ...     return data.rename(mapping)

    Notes
    -----
    Plugin Discovery Process:

    1. Programmatic registration: Plugins registered via :meth:`register_model_plugin`
    2. Entry point discovery: External packages can register via entry points in
       their setup.py/pyproject.toml (group: r2x_plugin)
    3. Lazy loading: Entry points are discovered on first PluginManager instantiation

    Design Patterns:

    - Singleton pattern: One instance shared globally
    - Class-level registries: Shared across all instances
    - Immutable components: PluginComponent uses frozen dataclass
    - Flexible signatures: System modifiers accept **kwargs for extensibility
    """

    _instance: ClassVar["PluginManager | None"] = None
    _initialized: ClassVar[bool] = False

    _registry: ClassVar[dict[str, PluginComponent]] = {}
    _modifier_registry: ClassVar[dict[str, SystemModifier]] = {}
    _filter_registry: ClassVar[dict[str, FilterFunction]] = {}

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
        upgrader: type | None = None,
    ) -> None:
        """Register a model plugin.

        Registers a model plugin with its configuration and optionally parser,
        exporter, and/or upgrader classes. At least one of parser or exporter
        should be provided, though both None is allowed (with a warning).

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
        upgrader : type | None, optional
            Upgrader class (DataUpgrader subclass)

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

        With upgrader:

        >>> PluginManager.register_model_plugin(
        ...     name="reeds",
        ...     config=ReEDSConfig,
        ...     parser=ReEDSParser,
        ...     upgrader=ReEDSDataUpgrader,
        ... )
        """
        if parser is None and exporter is None:
            logger.warning("Plugin '{}' registered with neither parser nor exporter", name)

        cls._registry[name] = PluginComponent(
            config=config,
            parser=parser,
            exporter=exporter,
            upgrader=upgrader,
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

    def get_upgrader(self, config_class: type["PluginConfig"]) -> type | None:
        """Get upgrader class for a config class.

        Returns the DataUpgrader subclass for the given config class.
        The upgrader class has registered upgrade steps and can be used
        to upgrade data folders.

        Parameters
        ----------
        config_class : type[PluginConfig]
            Configuration class to get upgrader for

        Returns
        -------
        type | None
            DataUpgrader subclass or None if no upgrader registered

        Raises
        ------
        KeyError
            If config class is not registered

        Examples
        --------
        >>> from r2x_core import PluginManager
        >>> from reeds_plugin import ReedsConfig
        >>>
        >>> manager = PluginManager()
        >>> upgrader_class = manager.get_upgrader(ReedsConfig)
        >>> if upgrader_class:
        ...     upgraded_folder = upgrader_class.upgrade(Path("/data"))
        """
        for component in self._registry.values():
            if component.config == config_class:
                return component.upgrader

        msg = f"Config class {config_class.__name__} not registered"
        raise KeyError(msg)

    def get_file_mapping_path(self, plugin_name: str) -> Path | None:
        """Get the file mapping path for a registered plugin.

        This is a convenience method that loads the plugin's config class
        and gets its file_mapping_path property. This allows getting the
        file mapping path without directly importing the config class.

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
        PluginConfig.file_mapping_path : Config property this delegates to
        load_config_class : Load the config class directly

        Notes
        -----
        The file may not exist even if a path is returned - the method only
        constructs the expected path based on the config module location.
        """
        config_class = self.load_config_class(plugin_name)
        if config_class is None:
            return None

        # Instantiate the config class to access the property
        try:
            config = config_class()
            return config.file_mapping_path
        except Exception:
            return None
