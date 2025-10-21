"""Exporter base class and workflow utilities.

This module defines :class:`BaseExporter`, the template that coordinates
export steps and returns a :class:`r2x_core.result.Result`.

Examples
--------
Minimal subclass and usage::

    from r2x_core.exporter import BaseExporter
    from r2x_core.result import Ok, Err
    from r2x_core.exceptions import ExporterError

    class MyExporter(BaseExporter):
        def prepare_export(self):
            # REQUIRED: perform the actual export work
            # Write files, transform data, etc.
            with open(self.config.output_path, 'w') as f:
                f.write(self.system.to_json())
            return Ok(None)

    exporter = MyExporter(config, system)
    result = exporter.export()
    if isinstance(result, Ok):
        print(f"Exported system: {result.unwrap()}")
    else:
        err = result.error
        raise ExporterError(err)

The examples above illustrate the preferred Result-based API for hooks and
how callers can inspect the returned Ok/Err to react to success or failure.
"""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import BaseModel

from .exceptions import ExporterError
from .result import Err, Ok, Result
from .store import DataStore
from .system import System


class BaseExporter(ABC):
    """Base class for exporters.

    Subclasses must implement the ``prepare_export`` method to perform the
    actual export work. Other hook methods are optional and can be overridden
    to customize the export workflow.

    The base class coordinates the workflow and returns a
    :class:`r2x_core.result.Result` indicating success or failure.
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
        """Execute the export workflow.

        This is a **template method** that orchestrates the export process by
        calling hook methods in a defined sequence. Subclasses should override
        the individual hook methods (``setup_configuration``, ``prepare_export``,
        ``validate_export``, ``export_time_series``, ``postprocess_export``)
        rather than overriding this method itself.

        The default workflow runs the following hooks in order::

            setup_configuration -> prepare_export -> validate_export -> export_time_series -> postprocess_export

        If any hook returns ``Err(...)``, the workflow stops and the error is
        returned to the caller.

        Returns
        -------
        Result[str, ExporterError]
            ``Ok(system_name)`` on success or ``Err(ExporterError(...))`` on failure.

        Notes
        -----
        This method should not be overridden by subclasses. Instead, customize
        behavior by implementing the hook methods.
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
        """Set up exporter-specific configuration.

        The base implementation returns ``Ok(None)``. Override in subclasses
        when configuration mutation is required before export.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` if configuration setup succeeds, or ``Err(ExporterError(...))``
            if configuration cannot be established.
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
        >>> def prepare_export(self):
        ...     output_path = self.config.output_dir / "output.json"
        ...     output_path.write_text(self.system.to_json())
        ...     return Ok(None)
        """
        ...

    def validate_export(self) -> Result[None, ExporterError]:
        """Validate configuration and system state prior to export.

        The base implementation is a no-op and returns ``Ok(None)``. Override
        in subclasses to implement validation logic.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` when validation succeeds, otherwise
            ``Err(ExporterError(...))`` with details.
        """
        logger.debug("BaseExporter.validate_export called - no-op; override in subclass if needed")
        return Ok(None)

    def export_time_series(self) -> Result[None, ExporterError]:
        """Export time series data for the system.

        The base implementation is a no-op and returns ``Ok(None)``. Subclasses
        that write time series should override this method and return an
        appropriate :class:`r2x_core.result.Result`.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` if export succeeds (or if no time series present),
            or ``Err(ExporterError(...))`` on failure.
        """
        logger.debug("BaseExporter.export_time_series called - no-op; override in subclass if needed")
        return Ok(None)

    def postprocess_export(self) -> Result[None, ExporterError]:
        """Perform any finalization or cleanup after export.

        The base implementation is a no-op and returns ``Ok(None)``. Override
        in subclasses to perform post-processing steps.

        Returns
        -------
        Result[None, ExporterError]
            ``Ok(None)`` if post-processing succeeds, or ``Err(ExporterError(...))``
            on failure.
        """
        logger.debug("BaseExporter.postprocess_export called - no-op; override in subclass if needed")
        return Ok(None)
