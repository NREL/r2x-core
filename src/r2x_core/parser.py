"""Base parser framework for building infrasys System objects from model data.

This module provides the foundational parser infrastructure that applications should use
to create model-specific parsers (e.g., ReEDSParser, PlexosParser, SiennaParser). The parser
coordinates data loading, validation, transformation, and system construction workflows while
leveraging the DataStore and DataReader for file management.

Classes
-------
BaseParser
    Abstract base parser class for building infrasys.System objects.

See Also
--------
r2x_core.plugin_config.PluginConfig : Base configuration class for all plugins

Examples
--------
Create a model-specific parser:

>>> from pydantic import BaseModel
>>> from r2x_core.plugin_config import PluginConfig
>>> from r2x_core.parser import BaseParser
>>> from r2x_core.store import DataStore
>>>
>>> class MyModelConfig(PluginConfig):
...     model_year: int
...     scenario: str
>>>
>>> class MyModelParser(BaseParser):
...     def __init__(self, config: MyModelConfig, data_store: DataStore, **kwargs):
...         super().__init__(config, data_store, **kwargs)
...         self.model_year = config.model_year
...
...     def validate_inputs(self) -> None:
...         if self.model_year < 2020:
...             raise ValidationError("Year must be >= 2020")
...
...     def build_system_components(self) -> None:
...         bus_data = self.read_data_file("buses")
...         for row in bus_data.iter_rows(named=True):
...             bus = self.create_component(ACBus, name=row["name"])
...             self.add_component(bus)
...
...     def build_time_series(self) -> None:
...         load_data = self.read_data_file("load_profiles")
...         # Attach time series...
>>>
>>> config = MyModelConfig(model_year=2030, scenario="base")
>>> store = DataStore.from_json("mappings.json", folder="/data")
>>> parser = MyModelParser(config, store)
>>> system = parser.build_system()

See Also
--------
r2x_core.store.DataStore : Data file management and loading
r2x_core.reader.DataReader : Low-level file reading operations
r2x_core.datafile.DataFile : File configuration and transformations
r2x_core.exceptions : Custom exception classes

Notes
-----
The parser framework follows the Template Method design pattern, where the base
class (BaseParser) defines the overall workflow in build_system() and subclasses
implement specific steps through abstract methods.

The design separates concerns:
- File I/O and caching: Handled by DataStore/DataReader
- Data transformations: Configured in DataFile, applied during reading
- System construction: Coordinated by parser, using infrasys.System
- Domain logic: Implemented in model-specific parser subclasses

This separation enables:
- Independent testing of components
- Reusability across different models
- Clear separation of I/O from business logic
- Flexible configuration management
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from .exceptions import ComponentCreationError, ParserError
from .plugin_config import PluginConfig
from .store import DataStore


class BaseParser(ABC):
    """Abstract base class for building infrasys.System objects from model data.

    The BaseParser provides a standardized framework for creating model-specific parsers.
    It orchestrates data loading, validation, transformation, and system construction,
    while delegating model-specific logic to subclasses through abstract methods.

    Applications create parsers by:
    1. Inheriting from BaseParser
    2. Implementing required abstract methods
    3. Optionally overriding hook methods for custom behavior
    4. Defining a model-specific PluginConfig subclass

    The typical workflow is:
    1. Initialize parser with configuration and data store
    2. Call build_system() which orchestrates the full build process
    3. Receive populated infrasys.System object

    Parameters
    ----------
    config : PluginConfig
        Model-specific configuration instance containing model parameters,
        default values, and file mappings.
    data_store : DataStore
        Initialized DataStore instance with file mappings loaded. The parser
        uses this to read and cache data files.
    name : str, optional
        Name for the system being built. If None, a default name will be used.
    auto_add_composed_components : bool, default=True
        Whether to automatically add composed components to the system.
        Passed directly to infrasys.System constructor.
    skip_validation : bool, default=False
        Skip Pydantic validation when creating component instances. Useful for
        performance optimization or when handling incomplete/legacy data.
        Use with caution as it bypasses type and constraint checking.

    Attributes
    ----------
    config : PluginConfig
        The model configuration instance.
    data_store : DataStore
        Data store for file management and reading.
    system : System or None
        The infrasys.System instance being built. None until build_system() is called.
    name : str
        Name of the system being built.
    auto_add_composed_components : bool
        Whether to auto-add composed components.
    skip_validation : bool
        Whether to skip component validation.

    Methods
    -------
    build_system()
        Main entry point: Build and return the complete infrasys.System.
    get_data(key)
        Retrieve parsed data from the data store by key.
    read_data_file(name, **kwargs)
        Read a data file through the data store with optional parameters.
    create_component(component_class, **field_values)
        Factory method to create and validate component instances.
    add_component(component)
        Add a component to the system with logging.
    add_time_series(component, time_series, **kwargs)
        Attach time series data to a component.
    validate_inputs()
        Hook for pre-build validation (override in subclasses).
    post_process_system()
        Hook for post-build processing (override in subclasses).

    Abstract Methods (must implement in subclass)
    ----------------------------------------------
    build_system_components()
        Create all system components (buses, generators, etc.).
    build_time_series()
        Attach time series data to components.

    Raises
    ------
    ParserError
        If there are issues during parsing or system construction.
    ValidationError
        If configuration or data validation fails.
    ComponentCreationError
        If component instantiation fails.

    Examples
    --------
    Create a simple parser:

    >>> from r2x_core.parser import BaseParser
    >>> from r2x_core.plugin_config import PluginConfig
    >>> from r2x_core.store import DataStore
    >>>
    >>> class MyModelConfig(PluginConfig):
    ...     model_year: int
    >>>
    >>> class MyModelParser(BaseParser):
    ...     def __init__(self, config, data_store, **kwargs):
    ...         super().__init__(config, data_store, **kwargs)
    ...         self.model_year = config.model_year
    ...
    ...     def validate_inputs(self):
    ...         if self.model_year < 2020:
    ...             raise ValidationError("Invalid year")
    ...
    ...     def build_system_components(self):
    ...         bus_data = self.read_data_file("buses")
    ...         for row in bus_data.iter_rows(named=True):
    ...             bus = self.create_component(ACBus, name=row["name"])
    ...             self.add_component(bus)
    ...
    ...     def build_time_series(self):
    ...         load_data = self.read_data_file("load_profiles")
    ...         # Attach time series...
    >>>
    >>> config = MyModelConfig(model_year=2030)
    >>> store = DataStore.from_json("mappings.json")
    >>> parser = MyModelParser(config, store)
    >>> system = parser.build_system()

    With custom post-processing:

    >>> class AdvancedParser(BaseParser):
    ...     def post_process_system(self):
    ...         '''Add metadata and validate connectivity.'''
    ...         logger.info(f"Built {len(self.system.get_components(Bus))} buses")
    ...         self._validate_connectivity()
    ...         self.system.metadata = {"year": self.config.model_year}

    For plugin integration (calling methods individually):

    >>> parser = MyModelParser(config, store)
    >>> parser.validate_inputs()
    >>> parser.build_system_components()  # Public method
    >>> # Apply custom modifications...
    >>> parser.build_time_series()  # Public method
    >>> parser.post_process_system()
    >>> system = parser.system

    See Also
    --------
    r2x_core.plugin_config.PluginConfig : Base configuration class
    DataStore : Data file management
    DataReader : File reading operations
    infrasys.system.System : Target system class

    Notes
    -----
    The parser follows the Template Method pattern where build_system() defines
    the overall algorithm flow, and subclasses fill in the specific steps through
    abstract methods.

    The separation between parser and data store provides:
    - Independent testing of data loading vs. system building
    - Reuse of data stores across multiple parsers
    - Clear separation of I/O concerns from domain logic
    - Flexible caching strategies

    Key design patterns:
    - Template Method: build_system() defines the workflow skeleton
    - build_system_components() and build_time_series() are the abstract templates
    - Hook methods: validate_inputs(), post_process_system() (optional overrides)
    """

    PLUGIN_TYPE: ClassVar[str] = "parser"

    def __init__(
        self,
        config: PluginConfig,
        data_store: DataStore,
        *,
        name: str | None = None,
        auto_add_composed_components: bool = True,
        skip_validation: bool = False,
    ) -> None:
        """Initialize the parser with configuration and data store.

        Parameters
        ----------
        config : PluginConfig
            Model-specific configuration instance.
        data_store : DataStore
            Initialized DataStore instance with file mappings.
        name : str, optional
            Name for the system being built.
        auto_add_composed_components : bool, default=True
            Whether to automatically add composed components.
        skip_validation : bool, default=False
            Skip Pydantic validation when creating components.
        """
        self.config = config
        self.data_store = data_store
        self.system: Any = None  # Will be assigned System instance in build_system
        self.name = name or "system"
        self.auto_add_composed_components = auto_add_composed_components
        self.skip_validation = skip_validation

    def build_system(self) -> Any:
        """Build and return the complete infrasys.System.

        This is the main entry point for the parser. It orchestrates the complete
        system building workflow by calling validation, component creation, time
        series attachment, and post-processing in sequence.

        The workflow is:
        1. Validate inputs (validate_inputs)
        2. Create infrasys.System instance
        3. Build system components (build_system_components)
        4. Build time series (build_time_series)
        5. Post-process system (post_process_system)
        6. Return completed system

        Returns
        -------
        System
            Fully constructed infrasys.System instance with all components
            and time series attached.

        Raises
        ------
        ParserError
            If system construction fails.
        ValidationError
            If validation fails during any step.
        ComponentCreationError
            If component creation fails.

        Examples
        --------
        Basic usage:

        >>> parser = MyModelParser(config, data_store)
        >>> system = parser.build_system()
        >>> print(f"Built system with {len(system.get_components(Bus))} buses")

        With error handling:

        >>> try:
        ...     system = parser.build_system()
        ... except ValidationError as e:
        ...     logger.error(f"Validation failed: {e}")
        ... except ParserError as e:
        ...     logger.error(f"Parser error: {e}")

        See Also
        --------
        validate_inputs : Pre-build validation hook
        build_system_components : Component creation
        build_time_series : Time series attachment
        post_process_system : Post-build processing hook

        Notes
        -----
        This method creates the System instance during execution, not in __init__.
        This allows multiple systems to be built from the same parser configuration
        if needed, and keeps the parser lightweight until actually used.

        For plugin systems that need finer control, call the individual public
        methods (build_system_components, build_time_series) directly instead.
        """
        from .system import System

        logger.info("Starting system build: {}", self.name)

        # Step 1: Validate inputs before doing anything
        logger.debug("Validating parser inputs...")
        self.validate_inputs()

        # Step 2: Create the r2x_core.System instance
        logger.debug("Creating System instance: {}", self.name)
        self.system = System(
            name=self.name,
            auto_add_composed_components=self.auto_add_composed_components,
        )

        # Step 3: Build all system components
        logger.info("Building system components...")
        self.build_system_components()

        # Step 4: Attach time series to components
        logger.info("Building time series...")
        self.build_time_series()

        # Step 5: Post-process the system
        logger.debug("Post-processing system...")
        self.post_process_system()

        logger.info("System '{}' built successfully", self.name)
        return self.system

    def get_data(self, key: str) -> Any:
        """Retrieve parsed data from the data store by key.

        Provides convenient access to data that has been loaded into the data store.
        This is a thin wrapper around the data store's internal data access.

        Parameters
        ----------
        key : str
            The data file identifier/name as registered in the data store.

        Returns
        -------
        Any
            The loaded data (typically polars.LazyFrame, polars.DataFrame,
            dict, or other format depending on the file type).

        Raises
        ------
        KeyError
            If the specified key is not found in the data store.

        Examples
        --------
        >>> bus_data = parser.get_data("buses")
        >>> gen_data = parser.get_data("generators")

        With error handling:

        >>> try:
        ...     data = parser.get_data("optional_file")
        ... except KeyError:
        ...     logger.warning("Optional file not found, using defaults")
        ...     data = default_data

        See Also
        --------
        read_data_file : Read data file through the data store
        DataStore.get_data_file_by_name : Underlying data store method

        Notes
        -----
        This method assumes the data has already been loaded into the data store.
        For on-demand reading, use read_data_file() instead.
        """
        try:
            return self.data_store.get_data_file_by_name(key)
        except KeyError as e:
            raise KeyError(f"Data file '{key}' not found in data store") from e

    def read_data_file(self, name: str, **kwargs: Any) -> Any:
        """Read a data file through the data store.

        Loads a data file using the data store's reader, applying any configured
        transformations (filters, column mapping, etc.) and optionally using cache.

        Parameters
        ----------
        name : str
            The data file identifier as registered in the data store.
        **kwargs
            Additional keyword arguments passed to the data store's read_data_file
            method. Common arguments include:
            - use_cache : bool, whether to use cached data

        Returns
        -------
        Any
            The loaded and transformed data (format depends on file type).

        Raises
        ------
        KeyError
            If the data file name is not found in the data store.
        ParserError
            If file reading fails.

        Examples
        --------
        Basic usage:

        >>> bus_data = parser.read_data_file("buses")

        With caching disabled:

        >>> fresh_data = parser.read_data_file("generators", use_cache=False)

        See Also
        --------
        get_data : Access already-loaded data
        DataStore.read_data_file : Underlying data store method
        DataFile : File configuration including transformations

        Notes
        -----
        This method applies transformations configured in the DataFile definition.
        If the file has filter, rename, or cast operations defined, they are
        applied automatically during reading.

        For performance-critical code paths, consider using use_cache=True (default)
        to avoid repeated file I/O.
        """
        try:
            return self.data_store.read_data_file(name=name, **kwargs)
        except KeyError as e:
            raise ParserError(f"Data file '{name}' not found in data store") from e
        except Exception as e:
            raise ParserError(f"Failed to read data file '{name}': {e}") from e

    def create_component(self, component_class: type[Any], **field_values: Any) -> Any:
        """Create and validate a component instance.

        Factory method for creating infrasys Component instances with optional
        validation skipping. Handles field filtering to only pass valid fields
        for the component class, and provides consistent error handling.

        Parameters
        ----------
        component_class : type
            The Component class to instantiate (e.g., ACBus, Generator, etc.).
        **field_values
            Field names and values to pass to the component constructor.
            Invalid fields (not in component's model_fields) are filtered out.
            None values are also filtered out.

        Returns
        -------
        Component
            Validated (or constructed) instance of the specified component class.

        Raises
        ------
        ComponentCreationError
            If component creation fails due to invalid field values or other errors.

        Examples
        --------
        Basic usage:

        >>> bus = parser.create_component(
        ...     ACBus,
        ...     name="Bus1",
        ...     voltage=230.0,
        ...     bus_type=ACBusTypes.PV
        ... )
        >>> parser.add_component(bus)

        With extra fields (filtered out automatically):

        >>> gen = parser.create_component(
        ...     Generator,
        ...     name="Gen1",
        ...     capacity=100.0,
        ...     extra_field="ignored",  # Not in Generator.model_fields
        ...     bus=None,  # None values are filtered out
        ... )

        Skip validation for performance:

        >>> parser.skip_validation = True
        >>> gen = parser.create_component(ThermalGen, **row_data)

        See Also
        --------
        add_component : Add component to system
        infrasys.component.Component : Base component class

        Notes
        -----
        This method implements the create_model_instance pattern from the old
        r2x codebase, providing the skip_validation functionality for handling
        incomplete or legacy data.

        When skip_validation=True:
        - Uses model_construct() instead of model_validate()
        - Bypasses Pydantic validation (faster but less safe)
        - Falls back to validation if construction fails

        Field filtering removes:
        - Fields not in component_class.model_fields
        - Fields with None values

        Subclasses can override this method to add model-specific defaults
        or transformations before component creation.
        """
        # Filter to only valid fields for this component class
        valid_fields = {
            key: value
            for key, value in field_values.items()
            if key in component_class.model_fields and value is not None
        }

        try:
            if self.skip_validation:
                # Try to construct without validation first
                try:
                    return component_class.model_construct(**valid_fields)
                except Exception:
                    # Fall back to validation if construction fails
                    return component_class.model_validate(valid_fields)
            else:
                # Normal validation
                return component_class.model_validate(valid_fields)
        except PydanticValidationError as e:
            raise ComponentCreationError(f"Failed to create {component_class.__name__}: {e}") from e
        except Exception as e:
            raise ComponentCreationError(f"Failed to create {component_class.__name__}: {e}") from e

    def add_component(self, component: Any) -> None:
        """Add a component to the system with logging.

        Convenience method that adds a component to the system and logs the action.
        Provides consistent logging across all parsers.

        Parameters
        ----------
        component : Component
            The infrasys Component instance to add to the system.

        Raises
        ------
        ParserError
            If system has not been created yet (build_system not called).

        Examples
        --------
        >>> bus = parser.create_component(ACBus, name="Bus1")
        >>> parser.add_component(bus)

        In a loop:

        >>> for row in bus_data.iter_rows(named=True):
        ...     bus = parser.create_component(ACBus, **row)
        ...     parser.add_component(bus)

        See Also
        --------
        create_component : Create component instances
        infrasys.system.System.add_component : Underlying system method

        Notes
        -----
        This method requires that self.system is not None. Call this within
        build_system_components(), after build_system() completes, or in plugin
        workflows after manually creating a System instance.

        The logging uses DEBUG level to avoid cluttering output when adding
        many components, but provides traceability for debugging.
        """
        if self.system is None:
            raise ParserError(
                "System has not been created yet. Call build_system() or create a System instance before adding components."
            )

        self.system.add_component(component)
        logger.debug("Added {}: {}", component.__class__.__name__, component.name)

    def add_time_series(self, component: Any, time_series: Any, **kwargs: Any) -> None:
        """Attach time series data to a component.

        Convenience method for adding time series to components with consistent
        logging and error handling.

        Parameters
        ----------
        component : Component
            The component to attach the time series to.
        time_series : TimeSeriesData
            The time series data instance (e.g., SingleTimeSeries).
        **kwargs
            Additional keyword arguments passed to system.add_time_series.

        Raises
        ------
        ParserError
            If system has not been created yet.

        Examples
        --------
        >>> from infrasys.time_series_models import SingleTimeSeries
        >>>
        >>> bus = parser.system.get_component(ACBus, "Bus1")
        >>> ts = SingleTimeSeries(
        ...     data=load_profile.to_numpy(),
        ...     variable_name="max_active_power"
        ... )
        >>> parser.add_time_series(bus, ts)

        See Also
        --------
        build_time_series : Method that typically calls this
        infrasys.system.System.add_time_series : Underlying system method

        Notes
        -----
        This is typically called within build_time_series(), but can be used in any
        workflow where self.system has been initialized.
        """
        if self.system is None:
            raise ParserError(
                "System has not been created yet. Call build_system() or create a System instance before adding time series."
            )

        self.system.add_time_series(time_series, component, **kwargs)
        logger.debug("Added time series to {}: {}", component.__class__.__name__, component.name)

    def validate_inputs(self) -> None:
        """Validate configuration and data before building system.

        Hook method that subclasses can override to perform custom validation
        before system construction begins. Called at the start of build_system().

        Default implementation does nothing. Override in subclasses to add
        validation logic.

        Raises
        ------
        ValidationError
            If validation fails. Subclasses should raise this exception
            with a descriptive message.

        Examples
        --------
        Basic validation:

        >>> class MyParser(BaseParser):
        ...     def validate_inputs(self):
        ...         if self.config.model_year < 2020:
        ...             raise ValidationError("Year must be >= 2020")

        Checking data availability:

        >>> def validate_inputs(self):
        ...     required = ["buses", "generators", "branches"]
        ...     for name in required:
        ...         if name not in self.data_store._data_files:
        ...             raise ValidationError(f"Required file '{name}' missing")

        Validating against data:

        >>> def validate_inputs(self):
        ...     years_data = self.get_data("available_years")
        ...     available = years_data["year"].to_list()
        ...     if self.config.model_year not in available:
        ...         raise ValidationError(
        ...             f"Year {self.config.model_year} not in {available}"
        ...         )

        See Also
        --------
        build_system : Calls this method first
        ValidationError : Exception to raise on failure

        Notes
        -----
        This is a hook method in the Template Method pattern. The base class
        calls it at the appropriate time, but subclasses provide the implementation.

        Best practices:
        - Validate configuration parameters
        - Check required data files are present
        - Verify cross-field constraints
        - Fail fast with clear error messages
        """

    @abstractmethod
    def build_system_components(self) -> None:
        """Create all system components (abstract method for subclass implementation).

        Subclasses must implement this method to create and add all components
        needed for their specific model. This typically includes buses, generators,
        loads, branches, and other network elements.

        The implementation should:
        1. Read component data using read_data_file()
        2. Iterate over the data
        3. Create components using create_component()
        4. Add components using add_component()

        Raises
        ------
        ParserError
            If component creation fails.
        ComponentCreationError
            If specific component instantiation fails.

        Examples
        --------
        Normal usage (via build_system):

        >>> parser = MyModelParser(config, data_store)
        >>> system = parser.build_system()  # Calls build_system_components internally

        Direct usage (for plugin systems):

        >>> parser = MyModelParser(config, data_store)
        >>> parser.validate_inputs()
        >>> parser.build_system_components()  # Call directly
        >>> # Apply custom modifications...
        >>> parser.build_time_series()

        Typical implementation:

        >>> def build_system_components(self):
        ...     # Create buses
        ...     bus_data = self.read_data_file("buses")
        ...     for row in bus_data.iter_rows(named=True):
        ...         bus = self.create_component(
        ...             ACBus,
        ...             name=row["bus_name"],
        ...             voltage=row["voltage_kv"]
        ...         )
        ...         self.add_component(bus)
        ...
        ...     # Create generators
        ...     gen_data = self.read_data_file("generators")
        ...     for row in gen_data.iter_rows(named=True):
        ...         gen = self.create_component(
        ...             ThermalGen,
        ...             name=row["gen_name"],
        ...             bus=self.system.get_component(ACBus, row["bus_name"]),
        ...             active_power=row["capacity_mw"]
        ...         )
        ...         self.add_component(gen)

        With error handling:

        >>> def build_system_components(self):
        ...     try:
        ...         bus_data = self.read_data_file("buses")
        ...     except KeyError:
        ...         raise ParserError("Required file 'buses' not found")
        ...
        ...     for idx, row in enumerate(bus_data.iter_rows(named=True)):
        ...         try:
        ...             bus = self.create_component(ACBus, **row)
        ...             self.add_component(bus)
        ...         except Exception as e:
        ...             raise ComponentCreationError(
        ...                 f"Failed to create bus at row {idx}: {e}"
        ...             ) from e

        See Also
        --------
        build_system : Main workflow that calls this method
        create_component : Factory for creating components
        add_component : Add component to system
        read_data_file : Read data files
        build_time_series : Companion method for time series

        Notes
        -----
        This is an abstract method that must be implemented by subclasses.
        It is called by build_system() as part of the template method workflow.

        Common patterns:
        - Create topology first (buses, areas, zones)
        - Create devices (generators, loads, storage)
        - Create connections (branches, interfaces)
        - Establish relationships (generator.bus = bus_instance)
        """

    @abstractmethod
    def build_time_series(self) -> None:
        """Attach time series data to components (abstract method for subclass implementation).

        Subclasses must implement this method to read and attach time series
        data to the appropriate components. This typically includes load profiles,
        generation profiles, and other time-varying data.

        The implementation should:
        1. Read time series data using read_data_file()
        2. Process/transform the data as needed
        3. Create time series objects (e.g., SingleTimeSeries)
        4. Attach to components using add_time_series()

        Raises
        ------
        ParserError
            If time series processing fails.

        Examples
        --------
        Normal usage (via build_system):

        >>> parser = MyModelParser(config, data_store)
        >>> system = parser.build_system()  # Calls build_time_series internally

        Direct usage (for plugin systems):

        >>> parser = MyModelParser(config, data_store)
        >>> parser.build_system_components()
        >>> # Apply modifications...
        >>> parser.build_time_series()  # Call directly

        Typical implementation:

        >>> def build_time_series(self):
        ...     from infrasys.time_series_models import SingleTimeSeries
        ...
        ...     # Load profiles for buses
        ...     load_data = self.read_data_file("load_profiles")
        ...
        ...     for bus_name in load_data.columns:
        ...         bus = self.system.get_component(ACBus, bus_name)
        ...         ts = SingleTimeSeries(
        ...             data=load_data[bus_name].to_numpy(),
        ...             variable_name="max_active_power"
        ...         )
        ...         self.add_time_series(bus, ts)
        ...
        ...     # Capacity factors for renewables
        ...     cf_data = self.read_data_file("capacity_factors")
        ...     for gen_name in cf_data.columns:
        ...         gen = self.system.get_component(RenewableGen, gen_name)
        ...         ts = SingleTimeSeries(
        ...             data=cf_data[gen_name].to_numpy(),
        ...             variable_name="max_active_power"
        ...         )
        ...         self.add_time_series(gen, ts)

        See Also
        --------
        build_system : Main workflow that calls this method
        add_time_series : Attach time series to component
        read_data_file : Read time series data files
        build_system_components : Companion method for components

        Notes
        -----
        This is an abstract method that must be implemented by subclasses.
        It is called by build_system() after build_system_components(),
        ensuring all components exist before attaching time series.

        Common time series types:
        - Load profiles (demand over time)
        - Renewable capacity factors (generation availability)
        - Price curves (cost over time)
        - Reserve requirements (operating reserve levels)
        """

    def post_process_system(self) -> None:
        """Perform post-processing after system construction.

        Hook method that subclasses can override to perform custom processing
        after all components and time series have been added. Called at the
        end of build_system().

        Default implementation does nothing. Override in subclasses to add
        post-processing logic.

        Examples
        --------
        Add summary logging:

        >>> def post_process_system(self):
        ...     logger.info(f"System '{self.system.name}' built successfully")
        ...     logger.info(f"  Buses: {len(self.system.get_components(ACBus))}")
        ...     logger.info(f"  Generators: {len(self.system.get_components(Generator))}")

        Add metadata:

        >>> def post_process_system(self):
        ...     self.system.metadata = {
        ...         "model_year": self.config.model_year,
        ...         "scenario": self.config.scenario,
        ...         "created": datetime.now().isoformat(),
        ...         "parser_version": __version__
        ...     }

        Validate system integrity:

        >>> def post_process_system(self):
        ...     # Check all generators have valid buses
        ...     buses = set(self.system.get_components(ACBus))
        ...     for gen in self.system.get_components(Generator):
        ...         if gen.bus not in buses:
        ...             raise ValidationError(
        ...                 f"Generator {gen.name} has invalid bus"
        ...             )

        See Also
        --------
        build_system : Calls this method last
        validate_inputs : Pre-build validation hook

        Notes
        -----
        This is a hook method in the Template Method pattern. The base class
        calls it at the appropriate time, but subclasses provide the implementation.

        Common uses:
        - Logging summary statistics
        - Adding metadata
        - Validating system integrity
        - Computing derived quantities
        - Setting up cross-component relationships
        """
