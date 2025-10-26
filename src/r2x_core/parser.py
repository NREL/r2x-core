"""Base parser framework for building infrasys System objects from model data.

Example usage of :class:`BaseParser`:

Create a custom parser by subclassing BaseParser:

>>> from r2x_core.parser import BaseParser
>>> from r2x_core.store import DataStore
>>> class MyParser(BaseParser):
...     def build_system_components(self):
...         # Load and create components
...         return Ok(None)
...     def build_time_series(self):
...         # Attach time series data
...         return Ok(None)
>>> config = MyConfig()
>>> parser = MyParser(config)
>>> system = parser.build_system()

Use with a data store for file management:

>>> store = DataStore(folder_path="/data")
>>> parser = MyParser(config, data_store=store)
>>> gen_data = parser.read_data_file("generators")

Enable validation control for performance:

>>> parser = MyParser(config, skip_validation=True)

This module provides the foundational parser infrastructure that applications should use
to create model-specific parsers (e.g., ReEDSParser, PlexosParser, SiennaParser). The parser
coordinates data loading, validation, transformation, and system construction workflows while
leveraging the DataStore and DataReader for file management.
"""

# ruff: noqa: D401

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from infrasys import Component
from infrasys.exceptions import ISAlreadyAttached
from loguru import logger

from .exceptions import ComponentCreationError, ParserError
from .plugin_config import PluginConfig
from .result import Err, Ok, Result
from .store import DataStore
from .system import System
from .utils import create_component, filter_valid_kwargs

T = TypeVar("T", bound=Component)


class BaseParser(ABC):
    """Abstract base class for building infrasys.System objects from model data.

    The :class:`BaseParser` provides a standardized framework for creating
    model-specific parsers by orchestrating data loading, validation, transformation,
    and system construction through a template method pattern. Subclasses implement
    abstract methods to customize component and time series building logic.

    Parameters
    ----------
    config : PluginConfig
        Parser configuration parameters. This is a positional-only parameter.
    data_store : DataStore | None, optional
        Optional data store for file management. If None, creates a new :class:`DataStore`.
        This is a keyword-only parameter. Default is None.
    system_name : str | None, optional
        Name for the system being built. Defaults to "system".
        Default is None.
    auto_add_composed_components : bool, optional
        Whether to automatically add composed components to the system.
        Default is True.
    skip_validation : bool, optional
        Skip Pydantic validation when creating components (faster but less safe).
        Default is False.
    **kwargs : Any
        Additional keyword arguments passed to :class:`System` constructor.

    Attributes
    ----------
    config : PluginConfig
        The parser configuration instance.
    store : DataStore
        The data store for file management.
    system : System
        The infrasys System instance being built.
    auto_add_composed_components : bool
        Whether composed components are automatically added.
    skip_validation : bool
        Whether component validation is skipped.

    Methods
    -------
    build_system()
        Build and return the complete system using template method pattern.
    build_system_components()
        Create all system components (abstract).
    build_time_series()
        Attach time series data to components (abstract).
    validate_inputs()
        Hook to validate configuration and data.
    prepare_data()
        Hook to prepare and load data.
    postprocess_system()
        Hook for post-processing after system construction.
    validate_system()
        Hook to validate the complete system.
    add_component()
        Add a component to the system.
    add_time_series()
        Attach time series data to a component.
    create_component()
        Create a component instance with optional validation.
    get_data()
        Retrieve parsed data from the data store.
    read_data_file()
        Read a data file through the data store.

    See Also
    --------
    :class:`DataStore` : Data file storage and management.
    :class:`DataReader` : Reader for loading data files.
    :class:`PluginConfig` : Parser configuration base class.
    :class:`ComponentCreationError` : Error during component creation.
    :class:`ParserError` : Error during parsing.

    Examples
    --------
    Create a custom parser by implementing abstract methods:

    >>> from r2x_core.parser import BaseParser
    >>> from r2x_core.result import Ok
    >>> class MyModelParser(BaseParser):
    ...     def build_system_components(self):
    ...         # Create buses, generators, loads, etc.
    ...         gen_data = self.read_data_file("generators")
    ...         for row in gen_data.iter_rows(named=True):
    ...             self.create_component(Generator, name=row["name"])
    ...         return Ok(None)
    ...     def build_time_series(self):
    ...         # Attach time series
    ...         return Ok(None)
    >>> config = MyModelConfig()
    >>> parser = MyModelParser(config)
    >>> system = parser.build_system()

    Notes
    -----
    The signature uses PEP 570 positional-only (``/``) and keyword-only (``*``)
    parameter separators:

    - ``config`` must be passed positionally
    - All other parameters must be passed by keyword

    The build process follows this sequence:

    1. :meth:`validate_inputs` - validate configuration and data
    2. :meth:`prepare_data` - load and preprocess data
    3. :meth:`build_system_components` - create system components (abstract)
    4. :meth:`build_time_series` - attach time series (abstract)
    5. :meth:`postprocess_system` - post-processing
    6. :meth:`validate_system` - validate complete system
    """

    def __init__(
        self,
        /,
        config: PluginConfig,
        *,
        data_store: DataStore | None = None,
        system_name: str | None = None,
        auto_add_composed_components: bool = True,
        skip_validation: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the parser with configuration and data store.

        Parameters
        ----------
        config : PluginConfig
            Parser configuration parameters. This is a positional-only parameter.
        data_store : DataStore | None, optional
            Optional data store for file management. If None, creates a new DataStore.
            This is a keyword-only parameter.
        system_name : str | None, optional
            Name for the system being built. Defaults to "system".
        auto_add_composed_components : bool, default True
            Whether to automatically add composed components to the system.
        skip_validation : bool, default False
            Skip Pydantic validation when creating components (faster but less safe).
        **kwargs : Any
            Additional keyword arguments passed to System constructor.

        Raises
        ------
        TypeError
            If data_store is provided but is not a DataStore instance.

        Notes
        -----
        The signature uses PEP 570 positional-only (``/``) and keyword-only (``*``)
        parameter separators:

        - ``config`` must be passed positionally
        - All other parameters must be passed by keyword

        Examples
        --------
        >>> parser = MyParser(config)  # Minimal usage
        >>> parser = MyParser(config, data_store=store, system_name="MySystem")
        >>> parser = MyParser(config, skip_validation=True)  # Skip pydantic validation
        """
        self._config = config
        self._store = data_store or DataStore()

        if not isinstance(self._store, DataStore):
            raise TypeError(f"data_store must be a DataStore instance, got {type(self._store).__name__}")

        self.auto_add_composed_components = auto_add_composed_components
        self.skip_validation = skip_validation

        if "name" in kwargs and not system_name:
            system_name = kwargs.pop("name")
        self._system = System(name=system_name, **filter_valid_kwargs(System, kwargs))

    @property
    def config(self) -> PluginConfig:
        """Return the :class:`PluginConfig` instance."""
        return self._config

    @property
    def store(self) -> DataStore:
        """Return the parser's :class:`DataStore` instance."""
        return self._store

    @property
    def system(self) -> System:
        """Return the :class:`System` instance being built."""
        return self._system

    def __repr__(self) -> str:
        """Return a string representation of the parser for debugging."""
        return f"{type(self).__name__}(config={self.config!r})"

    def build_system(self) -> System:
        """Build and return the complete :class:`System` using template method pattern.

        This is a **template method** that orchestrates the build process by
        calling hook methods in a defined sequence. Subclasses should override
        the individual hook methods rather than overriding this method itself.

        The build sequence is:

        1. :meth:`validate_inputs` - Validate configuration and data
        2. :meth:`prepare_data` - Load and preprocess data
        3. :meth:`build_system_components` - Create system components
        4. :meth:`build_time_series` - Attach time series data
        5. :meth:`postprocess_system` - Post-processing
        6. :meth:`validate_system` - Validate complete system

        Returns
        -------
        System
            The built system instance.

        Raises
        ------
        ParserError
            If any step in the build process fails.

        Examples
        --------
        >>> parser = MyParser(config)
        >>> system = parser.build_system()  # May raise ParserError
        >>> print(system.name)
        """
        parser_name = type(self).__name__
        logger.info("Starting system build for {}", parser_name)

        logger.debug("Validating parser inputs for {}", parser_name)
        res = self.validate_inputs()
        if res.is_err():
            raise ParserError(f"Input validation failed: {res.error}")

        logger.debug("Initializing data for {}", parser_name)
        res = self.prepare_data()
        if res.is_err():
            error_msg = f"Data preparation failed: {res.error}"
            raise ParserError(error_msg)

        logger.info("Building system components for {}", parser_name)
        res = self.build_system_components()
        if res.is_err():
            error_msg = f"Component building failed: {res.error}"
            raise ParserError(error_msg)

        logger.info("Building time series for {}", parser_name)
        res = self.build_time_series()
        if res.is_err():
            error_msg = f"Time series building failed: {res.error}"
            raise ParserError(error_msg)

        logger.debug("Post-processing system for {}", parser_name)
        res = self.postprocess_system()
        if res.is_err():
            error_msg = f"Post-processing failed: {res.error}"
            raise ParserError(error_msg)

        logger.debug("Validating complete system for {}", parser_name)
        res = self.validate_system()
        if res.is_err():
            error_msg = f"System validation failed: {res.error}"
            raise ParserError(error_msg)

        logger.info("System '{}' built successfully by {}", self._system.name, parser_name)
        return self._system

    @abstractmethod
    def build_system_components(self) -> Result[None, ParserError]:
        """Create all system components (buses, generators, loads, branches, etc.).

        This abstract method must be implemented by subclasses. It is called during
        the :meth:`build_system` template method to instantiate and add all
        system components.

        Returns
        -------
        Result[None, ParserError]
            ``Ok(None)`` if component building succeeds, or ``Err(ParserError(...))``
            to stop the workflow and report failure.

        Examples
        --------
        >>> def build_system_components(self) -> Result[None, ParserError]:
        ...     gen_data = self.read_data_file("generators")
        ...     for row in gen_data.iter_rows(named=True):
        ...         gen = self.create_component(Generator, name=row["name"])
        ...         self.add_component(gen)
        ...     return Ok(None)
        """
        ...

    @abstractmethod
    def build_time_series(self) -> Result[None, ParserError]:
        """Attach time series data to components.

        This abstract method must be implemented by subclasses. It is called during
        the :meth:`build_system` template method to attach time series data to
        existing system components.

        Returns
        -------
        Result[None, ParserError]
            ``Ok(None)`` if time series building succeeds, or ``Err(ParserError(...))``
            to stop the workflow and report failure.

        Examples
        --------
        >>> def build_time_series(self) -> Result[None, ParserError]:
        ...     ts_data = self.read_data_file("timeseries")
        ...     for component in self.system.generators:
        ...         self.add_time_series(component, ts_data)
        ...     return Ok(None)
        """
        ...

    def validate_inputs(self) -> Result[None, ParserError]:
        """Hook to validate configuration and data before building the system.

        The base implementation is a no-op and returns ``Ok(None)``. Override
        in subclasses to implement validation logic.

        Returns
        -------
        Result[None, ParserError]
            ``Ok(None)`` when validation succeeds, otherwise
            ``Err(ParserError(...))`` with details.

        Examples
        --------
        >>> def validate_inputs(self) -> Result[None, ParserError]:
        ...     if not self.config.input_folder.exists():
        ...         return Err(ParserError("Input folder does not exist"))
        ...     return Ok(None)
        """
        return Ok(None)

    def prepare_data(self) -> Result[None, ParserError]:
        """Hook to prepare and load data class variables required for system creation.

        This hook is called after input validation but before component building.
        Use it to load data files, preprocess data, build lookup tables, or cache
        datasets that will be used during system construction.

        The base implementation is a no-op and returns ``Ok(None)``. Override
        in subclasses to implement data loading logic.

        Returns
        -------
        Result[None, ParserError]
            ``Ok(None)`` when data preparation succeeds, otherwise
            ``Err(ParserError(...))`` with details.

        Examples
        --------
        >>> def prepare_data(self) -> Result[None, ParserError]:
        ...     # Load and cache data files
        ...     self._generators = self.read_data_file("generators")
        ...     self._buses = self.read_data_file("buses")
        ...     # Preprocess or merge data
        ...     self._gen_bus_map = dict(zip(self._generators["id"], self._generators["bus"]))
        ...     return Ok(None)
        """
        return Ok(None)

    def postprocess_system(self) -> Result[None, ParserError]:
        """Hook for post-processing after system construction.

        The base implementation is a no-op and returns ``Ok(None)``. Override
        in subclasses to perform post-processing steps such as applying system
        modifiers, aggregating components, or cleaning up temporary data.

        Returns
        -------
        Result[None, ParserError]
            ``Ok(None)`` if post-processing succeeds, or ``Err(ParserError(...))``
            on failure.

        Examples
        --------
        >>> def postprocess_system(self) -> Result[None, ParserError]:
        ...     # Apply custom transformations
        ...     self.system.aggregate_buses(threshold=10)
        ...     return Ok(None)
        """
        return Ok(None)

    def validate_system(self) -> Result[None, ParserError]:
        """Hook to validate the complete system after all building steps.

        This hook is called after all components and time series have been built
        and post-processing is complete. Use it to validate component relationships,
        check for orphaned components, verify data integrity, or ensure system
        constraints are met.

        The base implementation is a no-op and returns ``Ok(None)``. Override
        in subclasses to implement system validation logic.

        Returns
        -------
        Result[None, ParserError]
            ``Ok(None)`` when system validation succeeds, otherwise
            ``Err(ParserError(...))`` with validation errors.

        Examples
        --------
        >>> def validate_system(self) -> Result[None, ParserError]:
        ...     # Check all generator buses exist
        ...     for gen in self.system.get_components(Generator):
        ...         if gen.bus not in self.system.get_components(Bus):
        ...             return Err(ParserError(f"Generator {gen.name} references missing bus {gen.bus}"))
        ...     return Ok(None)
        """
        return Ok(None)

    def add_component(self, component: T) -> Result[None, ParserError]:
        """Add a :class:`Component` to the system with consistent logging.

        This is a helper method for use during the build process. Raises an
        exception if called before the system is initialized, as this indicates
        a programming error (non-recoverable).

        Parameters
        ----------
        component : Component
            The component to add to the system.

        Returns
        -------
        Result[None, ParserError]
            ``Ok(None)`` if component is added, or ``Err(ParserError(...))``
            if the component is already attached.

        Raises
        ------
        ParserError
            If system has not been initialized (programming error).
        """
        if self._system is None:
            raise ParserError(
                "System has not been created yet. This is a programming error - "
                "ensure __init__ completes successfully before calling add_component()."
            )
        try:
            self._system.add_component(component)
        except ISAlreadyAttached as e:
            return Err(ParserError(f"{e}"))
        logger.trace("Added {}: {}", component.__class__.__name__, component.name)
        return Ok()

    def add_time_series(self, component: T, time_series: Any, **kwargs: Any) -> bool:
        """Attach time series data to a :class:`Component`.

        This is a helper method for use during the build process. Returns False if
        time series attachment fails, True on success. Logs failures as debug messages.

        Parameters
        ----------
        component : Component
            The component to attach time series to.
        time_series : Any
            The time series data to attach.
        **kwargs : Any
            Additional keyword arguments passed to :meth:`System.add_time_series`.

        Returns
        -------
        bool
            True if time series was attached successfully, False otherwise.

        Raises
        ------
        ParserError
            If system has not been initialized (programming error).

        Notes
        -----
        Errors during time series attachment are logged as debug messages.
        """
        if self._system is None:
            raise ParserError(
                "System has not been created yet. This is a programming error - "
                "ensure __init__ completes successfully before calling add_time_series()."
            )
        try:
            self._system.add_time_series(time_series, component, **kwargs)
            logger.debug("Added time series to {}: {}", type(component).__name__, component.name)
            return True
        except Exception as e:
            logger.debug("Failed to add time series to {}: {}", type(component).__name__, e)
            return False

    def create_component(self, component_class: type[T], /, **field_values: Any) -> T:
        """Create a :class:`Component` instance with optional validation.

        This helper method creates component instances while respecting the
        ``skip_validation`` flag set during parser initialization. It also
        filters out None values and invalid fields before construction.

        Parameters
        ----------
        component_class : type[T]
            The component class to instantiate. This is a positional-only parameter.
        **field_values : Any
            Field values to pass to the component constructor. All field values
            are keyword-only parameters.

        Returns
        -------
        T
            The created component instance.

        Raises
        ------
        ComponentCreationError
            If component creation fails due to validation errors or other issues.

        Notes
        -----
        When ``skip_validation=True``, this method uses ``model_construct``
        for faster creation without Pydantic validation.

        None values and fields not in the component's model fields are automatically
        filtered out before creation.

        Examples
        --------
        >>> # Create with validation (default)
        >>> bus = self.create_component(ACBus, name="Bus1", voltage=230.0)
        >>>
        >>> # Create without validation (if parser.skip_validation=True)
        >>> gen = self.create_component(Generator, name="Gen1", max_active_power=100.0)
        """
        util_result = create_component(
            component_class,
            skip_none=True,
            skip_validation=self.skip_validation,
            **field_values,
        )

        if util_result.is_err():
            class_name = type(component_class).__name__
            error = util_result.error
            raise ComponentCreationError(f"Failed to create {class_name}: {error}") from error

        return util_result.unwrap()

    def get_data(self, key: str) -> Any:
        """Retrieve parsed data from the :class:`DataStore` by key.

        Parameters
        ----------
        key : str
            The name/key of the data file.

        Returns
        -------
        Any
            The data from the store.

        Raises
        ------
        KeyError
            If the key is not in the data store.
        """
        return self._store[key]

    def read_data_file(self, name: str, **kwargs: Any) -> Any:
        """Read a data file through the data store using parser config placeholders.

        This is a convenience method that wraps :meth:`DataStore.read_data` and
        automatically passes the parser configuration as placeholders for template
        substitution.

        Parameters
        ----------
        name : str
            The name of the data file to read.
        **kwargs : Any
            Additional keyword arguments passed to :meth:`DataStore.read_data`.

        Returns
        -------
        Any
            The loaded data from the file.

        Examples
        --------
        >>> gen_data = self.read_data_file("generators")
        >>> bus_data = self.read_data_file("buses", use_cache=False)
        """
        return self._store.read_data(name=name, placeholders=self._config.model_dump(), **kwargs)
