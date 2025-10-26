"""Exporter base class and workflow utilities.

Example usage of :class:`BaseExporter`:

Create a custom exporter by subclassing BaseExporter:

>>> from r2x_core.exporter import BaseExporter
>>> from r2x_core.result import Ok
>>> class MyExporter(BaseExporter):
...     def prepare_export(self):
...         # Write files, transform data, etc.
...         with open(self.config.output_path, 'w') as f:
...             f.write(self.system.to_json())
...         return Ok(None)
>>> exporter = MyExporter(config, system)
>>> result = exporter.export()
>>> if result.is_ok():
...     print(f"Export successful: {result.unwrap()}")

Use with a data store for output files:

>>> exporter = MyExporter(config, system, data_store=store)
>>> result = exporter.export()

This module defines :class:`BaseExporter`, the template that coordinates
export steps and returns a :class:`r2x_core.result.Result`.
"""

# ruff: noqa: D401

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import BaseModel

from .exceptions import ExporterError
from .result import Err, Ok, Result
from .store import DataStore
from .system import System


class BaseExporter(ABC):
    """Base class for system exporters.

    The :class:`BaseExporter` provides a template method pattern for exporting
    :class:`System` objects. Subclasses must implement :meth:`prepare_export`
    to perform the actual export work. Other hook methods are optional and can
    be overridden to customize the export workflow.

    Parameters
    ----------
    config : BaseModel
        Export configuration parameters. This is a positional-only parameter.
    system : System
        System object to export. This is a positional-only parameter.
    data_store : DataStore | None, optional
        Optional data store with output file paths. This is a keyword-only parameter.
        Default is None.
    **kwargs : Any
        Additional keyword arguments exposed to subclasses. All kwargs are keyword-only.

    Attributes
    ----------
    config : BaseModel
        The export configuration instance.
    system : System
        The system being exported.
    data_store : DataStore | None
        The data store for output management.

    Methods
    -------
    export()
        Execute the export workflow (template method).
    setup_configuration()
        Hook for exporter-specific configuration setup.
    prepare_export()
        Hook for actual export operation (abstract).
    validate_export()
        Hook for validation before export.
    export_time_series()
        Hook for exporting time series data.
    postprocess_export()
        Hook for post-processing after export.

    See Also
    --------
    :class:`BaseParser` : Parser base class (inverse operation).
    :class:`System` : System object being exported.
    :class:`DataStore` : Data store for file management.
    :class:`ExporterError` : Error during export.

    Examples
    --------
    Create a custom exporter and use it:

    >>> from r2x_core.exporter import BaseExporter
    >>> from r2x_core.result import Ok
    >>> from pathlib import Path
    >>> class CSVExporter(BaseExporter):
    ...     def prepare_export(self):
    ...         output_dir = Path(self.config.output_dir)
    ...         output_dir.mkdir(exist_ok=True)
    ...         # Write CSV files
    ...         for gen in self.system.generators:
    ...             # Export generator data
    ...             pass
    ...         return Ok(None)
    >>> exporter = CSVExporter(config, system)
    >>> result = exporter.export()

    Notes
    -----
    The signature uses PEP 570 positional-only (``/``) and keyword-only (``*``)
    parameter separators:

    - ``config`` and ``system`` must be passed positionally
    - ``data_store`` and any additional kwargs must be passed by keyword

    The export workflow follows this sequence:

    1. :meth:`setup_configuration` - Set up exporter configuration
    2. :meth:`prepare_export` - Perform actual export (abstract)
    3. :meth:`validate_export` - Validate export results
    4. :meth:`export_time_series` - Export time series data
    5. :meth:`postprocess_export` - Post-processing and cleanup
    """

    def __init__(
        self,
        config: BaseModel,
        system: System,
        /,
        *,
        data_store: DataStore | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the exporter.

        Parameters
        ----------
        config : BaseModel
            Export configuration parameters. This is a positional-only parameter.
        system : System
            System object to export. This is a positional-only parameter.
        data_store : DataStore | None, optional
            Optional data store with output file paths. This is a keyword-only parameter.
        **kwargs : Any
            Additional keyword arguments exposed to subclasses. All kwargs are keyword-only.

        Notes
        -----
        The signature uses PEP 570 positional-only (``/``) and keyword-only (``*``)
        parameter separators:

        - ``config`` and ``system`` must be passed positionally
        - ``data_store`` and any additional kwargs must be passed by keyword

        Examples
        --------
        >>> exporter = MyExporter(config, system)  # Minimal usage
        >>> exporter = MyExporter(config, system, data_store=store)  # With data_store
        >>> exporter = MyExporter(config, system, data_store=store, verbose=True)  # With kwargs
        """
        self.config = config
        self.system = system
        self.data_store = data_store

        for key, value in kwargs.items():
            setattr(self, key, value)

        logger.info("Initialized {} exporter", type(self).__name__)

    def export(self) -> Result[str, ExporterError]:
        """Execute the export workflow using template method pattern.

        This is a **template method** that orchestrates the export process by
        calling hook methods in a defined sequence. Subclasses should override
        the individual hook methods (``setup_configuration``, ``prepare_export``,
        ``validate_export``, ``export_time_series``, ``postprocess_export``)
        rather than overriding this method itself.

        The export sequence is:

        1. :meth:`setup_configuration` - Set up exporter configuration
        2. :meth:`prepare_export` - Perform actual export (abstract)
        3. :meth:`validate_export` - Validate export results
        4. :meth:`export_time_series` - Export time series data
        5. :meth:`postprocess_export` - Post-processing and cleanup

        Returns
        -------
        Result[str, ExporterError]
            ``Ok(system_name)`` on success or ``Err(ExporterError(...))`` on failure.

        Notes
        -----
        This method should not be overridden by subclasses. Instead, customize
        behavior by implementing the hook methods. If any hook returns ``Err(...)``,
        the workflow stops and the error is returned to the caller.

        Examples
        --------
        >>> exporter = MyExporter(config, system)
        >>> result = exporter.export()
        >>> if result.is_ok():
        ...     print(f"Exported: {result.unwrap()}")
        >>> else:
        ...     print(f"Export failed: {result.error}")
        """
        exporter_name = type(self).__name__
        system_name = getattr(self.system, "name", "<unnamed>")

        logger.info("Starting export for exporter: {} (system={})", exporter_name, system_name)

        logger.info("Setting up configuration for {}", exporter_name)
        res = self.setup_configuration()
        if isinstance(res, Err):
            logger.error("{}.setup_configuration failed: {}", exporter_name, res.error)
            return Err(ExporterError(str(res.error)))

        logger.info("Preparing export configuration for {}", exporter_name)
        res = self.prepare_export()
        if isinstance(res, Err):
            logger.error("{}.prepare_export failed: {}", exporter_name, res.error)
            return Err(ExporterError(str(res.error)))

        logger.info("Validating export configuration for {}", exporter_name)
        res = self.validate_export()
        if isinstance(res, Err):
            logger.error("{}.validate_export failed: {}", exporter_name, res.error)
            return Err(ExporterError(str(res.error)))

        logger.info("Exporting time series (if any) for {}", exporter_name)
        res = self.export_time_series()
        if isinstance(res, Err):
            logger.error("{}.export_time_series failed: {}", exporter_name, res.error)
            return Err(ExporterError(str(res.error)))

        logger.info("Post-processing export for {}", exporter_name)
        res = self.postprocess_export()
        if isinstance(res, Err):
            logger.error("{}.postprocess_export failed: {}", exporter_name, res.error)
            return Err(ExporterError(str(res.error)))

        logger.info("Export completed successfully by {} for system: {}", exporter_name, system_name)
        return Ok(system_name)

    def setup_configuration(self) -> Result[None, ExporterError]:
        """Hook to set up exporter-specific configuration.

        The base implementation returns ``Ok(None)``. Override in subclasses
        when configuration mutation is required before export.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` if configuration setup succeeds, or ``Err(ExporterError(...))``
            if configuration cannot be established.

        Examples
        --------
        >>> def setup_configuration(self) -> Result[None, ExporterError]:
        ...     self.config.output_dir.mkdir(parents=True, exist_ok=True)
        ...     return Ok(None)
        """
        return Ok(None)

    @abstractmethod
    def prepare_export(self) -> Result[None, ExporterError]:
        """Prepare and perform the export operation.

        **This method must be implemented by all subclasses.** This is where
        the actual export work happens: writing files, transforming data,
        generating output, etc.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` if export succeeds, or ``Err(ExporterError(...))``
            to stop the workflow and report failure.

        Examples
        --------
        >>> def prepare_export(self) -> Result[None, ExporterError]:
        ...     output_path = self.config.output_dir / "output.json"
        ...     output_path.write_text(self.system.to_json())
        ...     return Ok(None)
        """
        ...

    def validate_export(self) -> Result[None, ExporterError]:
        """Hook to validate configuration and system state prior to export.

        The base implementation is a no-op and returns ``Ok(None)``. Override
        in subclasses to implement validation logic.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` when validation succeeds, otherwise
            ``Err(ExporterError(...))`` with details.

        Examples
        --------
        >>> def validate_export(self) -> Result[None, ExporterError]:
        ...     if not self.system.generators:
        ...         return Err(ExporterError("No generators in system"))
        ...     return Ok(None)
        """
        logger.debug("BaseExporter.validate_export called - no-op; override in subclass if needed")
        return Ok(None)

    def export_time_series(self) -> Result[None, ExporterError]:
        """Hook to export time series data for the system.

        The base implementation is a no-op and returns ``Ok(None)``. Subclasses
        that write time series should override this method and return an
        appropriate :class:`Result`.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` if export succeeds (or if no time series present),
            or ``Err(ExporterError(...))`` on failure.

        Examples
        --------
        >>> def export_time_series(self) -> Result[None, ExporterError]:
        ...     for component in self.system.components:
        ...         if component.time_series:
        ...             # Export time series
        ...             pass
        ...     return Ok(None)
        """
        logger.debug("BaseExporter.export_time_series called - no-op; override in subclass if needed")
        return Ok(None)

    def postprocess_export(self) -> Result[None, ExporterError]:
        """Hook to perform finalization or cleanup after export.

        The base implementation is a no-op and returns ``Ok(None)``. Override
        in subclasses to perform post-processing steps such as compression,
        cleanup, or reporting.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` if post-processing succeeds, or ``Err(ExporterError(...))``
            on failure.

        Examples
        --------
        >>> def postprocess_export(self) -> Result[None, ExporterError]:
        ...     # Compress exported files
        ...     import shutil
        ...     shutil.make_archive("output", "zip", self.config.output_dir)
        ...     return Ok(None)
        """
        logger.debug("BaseExporter.postprocess_export called - no-op; override in subclass if needed")
        return Ok(None)
