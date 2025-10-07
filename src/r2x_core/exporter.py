"""Base exporter framework for exporting infrasys System objects to model formats.

This module provides the foundational exporter infrastructure that applications should use
to create model-specific exporters (e.g., ReEDSExporter, PlexosExporter, SiennaExporter).
The exporter coordinates component export, time series export, and file writing workflows
while leveraging the DataStore for file management.

Classes
-------
BaseExporter
    Abstract base exporter class for exporting infrasys.System objects.

Examples
--------
Create a model-specific exporter:

>>> from pydantic import BaseModel
>>> from r2x_core.exporter import BaseExporter
>>> from r2x_core.store import DataStore
>>> from r2x_core.system import System
>>>
>>> class MyModelConfig(BaseModel):
...     model_year: int
...     scenario: str
...     export_timeseries: bool = True
>>>
>>> class MyModelExporter(BaseExporter):
...     def __init__(self, config: MyModelConfig, system: System, data_store: DataStore, **kwargs):
...         super().__init__(config, system, data_store, **kwargs)
...         self.model_year = config.model_year
...
...     def export(self) -> None:
...         logger.info(f"Exporting to MyModel format for year {self.model_year}")
...         self._export_generators()
...         self._export_buses()
...         if self.config.export_timeseries:
...             self.export_time_series()
...         logger.info("Export complete")
...
...     def _export_generators(self) -> None:
...         gen_file = self.data_store.data_files["generators"]
...         self.system.export_components_to_csv(
...             file_path=gen_file.file_path,
...             filter_func=lambda c: isinstance(c, Generator)
...         )
...
...     def _export_buses(self) -> None:
...         pass  # Implementation
...
...     def export_time_series(self) -> None:
...         for datafile in self.data_store.data_files.values():
...             if datafile.is_timeseries:
...                 # Export time series data for this file
...                 pass  # Implementation
>>>
>>> config = MyModelConfig(model_year=2030, scenario="base", export_timeseries=True)
>>> system = System()  # Already populated with components
>>> store = DataStore(data_files={...}, folder="/path/to/output")
>>> exporter = MyModelExporter(config, system, store)
>>> exporter.export()

See Also
--------
r2x_core.store.DataStore : Data file management
r2x_core.system.System : System component management and export methods
r2x_core.datafile.DataFile : File configuration
r2x_core.exceptions : Custom exception classes

Notes
-----
The exporter framework follows the Template Method design pattern, where the base
class (BaseExporter) defines the overall structure and subclasses implement
specific export logic through the abstract export() method.

The design separates concerns:
- Component export: System.export_components_to_csv() and System.components_to_records()
- File management: DataStore provides file paths and configuration
- Time series export: Applications implement using infrasys get_time_series()
- Export orchestration: Coordinated by exporter subclass

This separation enables:
- Independent testing of components
- Reusability across different models
- Clear separation of export logic from I/O
- Flexible configuration management
"""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import BaseModel

from .store import DataStore
from .system import System


class BaseExporter(ABC):
    """Abstract base class for exporting infrasys.System objects to model formats.

    This class provides the foundational structure for model-specific exporters.
    Subclasses must implement two abstract methods:
    - export(): Define the overall export workflow
    - export_time_series(): Export time series data from system

    The BaseExporter provides access to:
    - System with components and time series (self.system)
    - DataStore with file paths and configuration (self.data_store)
    - Export configuration (self.config)

    Parameters
    ----------
    config : BaseModel
        Configuration object containing export parameters. Applications should
        define their own config class inheriting from pydantic.BaseModel.
    system : System
        R2X System object containing components and time series to export.
    data_store : DataStore
        DataStore containing output file paths and configuration.
    **kwargs : dict, optional
        Additional keyword arguments for subclass customization.

    Attributes
    ----------
    config : BaseModel
        Export configuration parameters.
    system : System
        System object with components and time series.
    data_store : DataStore
        DataStore with output file configuration.

    Examples
    --------
    Create a simple exporter:

    >>> from pydantic import BaseModel
    >>> from r2x_core import BaseExporter, DataStore, System, DataFile
    >>>
    >>> class MyConfig(BaseModel):
    ...     year: int
    >>>
    >>> class MyExporter(BaseExporter):
    ...     def export(self) -> None:
    ...         logger.info(f"Exporting for year {self.config.year}")
    ...         # Export all components to CSV
    ...         output_file = self.data_store.data_files["components"]
    ...         self.system.export_components_to_csv(output_file.file_path)
    ...         # Export time series
    ...         self.export_time_series()
    ...
    ...     def export_time_series(self) -> None:
    ...         # Export time series data
    ...         ts_file = self.data_store.data_files["timeseries"]
    ...         # ... implementation
    >>>
    >>> config = MyConfig(year=2030)
    >>> system = System(name="MySystem")
    >>> data_store = DataStore(
    ...     data_files={"components": DataFile(name="components", file_path="output.csv")},
    ...     folder="/output"
    ... )
    >>> exporter = MyExporter(config, system, data_store)
    >>> exporter.export()

    Export with filtering:

    >>> class FilteredExporter(BaseExporter):
    ...     def export(self) -> None:
    ...         # Export only specific component types
    ...         gen_file = self.data_store.data_files["generators"]
    ...         self.system.export_components_to_csv(
    ...             file_path=gen_file.file_path,
    ...             filter_func=lambda c: c.__class__.__name__ == "Generator"
    ...         )
    ...         self.export_time_series()
    ...
    ...     def export_time_series(self) -> None:
    ...         # Export time series for generators only
    ...         pass

    Export with field selection and renaming:

    >>> class MappedExporter(BaseExporter):
    ...     def export(self) -> None:
    ...         gen_file = self.data_store.data_files["generators"]
    ...         self.system.export_components_to_csv(
    ...             file_path=gen_file.file_path,
    ...             filter_func=lambda c: isinstance(c, Generator),
    ...             fields=["name", "max_active_power"],
    ...             key_mapping={"max_active_power": "capacity_mw"}
    ...         )
    ...         self.export_time_series()
    ...
    ...     def export_time_series(self) -> None:
    ...         # Export time series data
    ...         pass

    See Also
    --------
    r2x_core.system.System.export_components_to_csv : Export components to CSV
    r2x_core.system.System.components_to_records : Get components as dict records
    r2x_core.store.DataStore : File path management
    infrasys.system.System.get_time_series : Get time series from components

    Notes
    -----
    The BaseExporter provides a minimal interface with two abstract methods:
    - export(): Orchestrate the complete export workflow
    - export_time_series(): Handle time series data export

    This gives applications maximum flexibility to:
    - Define their own export workflow in export()
    - Use any combination of System export methods
    - Implement custom time series export logic
    - Handle transformations and formatting as needed

    Common export patterns:
    1. Component export: Use system.export_components_to_csv()
    2. Custom transformations: Use system.components_to_records() then transform
    3. Time series export: Implement in export_time_series() using system.get_time_series()
    4. Multi-file export: Iterate over data_store.data_files
    """

    def __init__(
        self,
        config: BaseModel,
        system: System,
        data_store: DataStore,
        **kwargs: Any,
    ) -> None:
        """Initialize the exporter.

        Parameters
        ----------
        config : BaseModel
            Export configuration parameters.
        system : System
            System object to export.
        data_store : DataStore
            DataStore with output file paths.
        **kwargs : dict
            Additional arguments for subclass customization.
        """
        self.config = config
        self.system = system
        self.data_store = data_store

        # Store additional kwargs for subclass use
        for key, value in kwargs.items():
            setattr(self, key, value)

        logger.debug("Initialized {} exporter", self.__class__.__name__)

    @abstractmethod
    def export(self) -> None:
        """Export the system to the target model format.

        This method must be implemented by subclasses to define the complete
        export workflow for their specific model format.

        The implementation should:

        1. Export component data using system.export_components_to_csv() or
           system.components_to_records()
        2. Export time series data using export_time_series()
        3. Apply any model-specific transformations
        4. Write files to paths configured in data_store

        Raises
        ------
        ExporterError
            If export fails for any reason.

        Examples
        --------
        Simple export implementation:

        >>> def export(self) -> None:
        ...     logger.info("Starting export")
        ...     # Export components
        ...     self._export_components()
        ...     # Export time series
        ...     self.export_time_series()
        ...     logger.info("Export complete")

        Export with error handling:

        >>> def export(self) -> None:
        ...     try:
        ...         self._export_components()
        ...         self.export_time_series()
        ...     except Exception as e:
        ...         raise ExporterError(f"Export failed: {e}") from e

        See Also
        --------
        export_time_series : Export time series data from system
        r2x_core.system.System.export_components_to_csv : Export components
        r2x_core.system.System.components_to_records : Get component records
        r2x_core.exceptions.ExporterError : Export error exception
        """
        # pragma: no cover

    @abstractmethod
    def export_time_series(self) -> None:
        """Export time series data from the system.

        This method must be implemented by subclasses to export time series
        data from components to files. The implementation should:
        1. Identify which components have time series data
        2. Retrieve time series using system.get_time_series()
        3. Convert to appropriate format (DataFrame, arrays, etc.)
        4. Write to files based on data_store configuration

        Subclasses can filter time series files using:
        >>> ts_files = [
        ...     df for df in self.data_store.data_files.values()
        ...     if df.is_timeseries
        ... ]

        Raises
        ------
        ExporterError
            If time series export fails.

        Examples
        --------
        Export time series to CSV:

        >>> def export_time_series(self) -> None:
        ...     import polars as pl
        ...     for datafile in self.data_store.data_files.values():
        ...         if datafile.is_timeseries:
        ...             # Collect time series data
        ...             ts_data = self._collect_time_series(datafile.name)
        ...             # Write to file
        ...             ts_data.write_csv(datafile.file_path)

        Export to HDF5:

        >>> def export_time_series(self) -> None:
        ...     import h5py
        ...     ts_file = self.data_store.data_files["timeseries"]
        ...     with h5py.File(ts_file.file_path, "w") as f:
        ...         for component in self.system.get_components():
        ...             ts_data = self.system.get_time_series(component)
        ...             if ts_data is not None:
        ...                 f.create_dataset(component.name, data=ts_data)

        Export with file type matching:

        >>> def export_time_series(self) -> None:
        ...     from r2x_core.file_types import TableFormat, H5Format, ParquetFormat
        ...     for datafile in self.data_store.data_files.values():
        ...         if not datafile.is_timeseries:
        ...             continue
        ...         ts_data = self._collect_time_series(datafile.name)
        ...         match datafile.file_type:
        ...             case TableFormat():
        ...                 ts_data.write_csv(datafile.file_path)
        ...             case H5Format():
        ...                 self._write_h5(datafile, ts_data)
        ...             case ParquetFormat():
        ...                 ts_data.write_parquet(datafile.file_path)

        See Also
        --------
        infrasys.system.System.get_time_series : Retrieve time series from components
        r2x_core.datafile.DataFile.is_timeseries : Check if file is for time series
        r2x_core.file_types : File type classes for format handling
        """
        # pragma: no cover
