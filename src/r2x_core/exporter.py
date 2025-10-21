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
            # perform preparation, return Ok(None) on success
            return Ok(None)

        def validate_export(self):
            # perform validation, return Err(...) on failure
            return Ok(None)

        def export_time_series(self):
            # write time series if present
            return Ok(None)

        def postprocess_export(self):
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

    Subclasses implement format-specific export behavior by overriding the
    hook methods. The base class coordinates the workflow and returns
    a :class:`r2x_core.result.Result` indicating success or failure.
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
            Export configuration parameters.
        system : System
            System object to export.
        data_store : DataStore | None
            Optional data store with output file paths.
        **kwargs
            Additional keyword arguments exposed to subclasses.
        """
        self.config = config
        self.system = system
        self.data_store = data_store

        for key, value in kwargs.items():
            setattr(self, key, value)

        logger.info("Initialized {} exporter", type(self).__name__)

    def export(self) -> Result[str, ExporterError]:
        """Execute the export workflow.

        The default workflow runs the following hooks in order::

            setup_configuration -> prepare_export -> validate_export -> export_time_series -> postprocess_export

        Returns
        -------
        Result[str, ExporterError]
            ``Ok(system_name)`` on success or ``Err(ExporterError(...))`` on failure.
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

    @abstractmethod
    def export_time_series(self) -> Result[None, ExporterError]:
        """Export time series data for the system.

        The base implementation is a no-op and returns ``Ok(None)``. Subclasses
        that write time series should override this method and return an
        appropriate :class:`r2x_core.result.Result`.
        """
        logger.debug("BaseExporter.export_time_series called - no-op; override in subclass if needed")
        return Ok(None)

    @abstractmethod
    def setup_configuration(self) -> Result[None, ExporterError]:
        """Set up exporter-specific configuration.

        The base implementation returns ``Ok(None)``. Override in subclasses
        when configuration mutation is required before export.
        """
        return Ok(None)

    @abstractmethod
    def prepare_export(self) -> Result[None, ExporterError]:
        """Prepare any inputs or derived data required for export.

        Return ``Err(ExporterError(...))`` to stop the workflow.
        """
        logger.debug("BaseExporter.prepare_export called - no-op; override in subclass if needed")
        return Ok(None)

    @abstractmethod
    def postprocess_export(self) -> Result[None, ExporterError]:
        """Perform any finalization or cleanup after export.

        The base implementation is a no-op and returns ``Ok(None)``.
        """
        logger.debug("BaseExporter.postprocess_export called - no-op; override in subclass if needed")
        return Ok(None)

    @abstractmethod
    def validate_export(self) -> Result[None, ExporterError]:
        """Validate configuration and system state prior to export.

        Implementations should return ``Ok(None)`` when validation succeeds,
        otherwise return ``Err(ExporterError(...))`` with details.
        """
        logger.debug("BaseExporter.validate_export called - no-op; override in subclass if needed")
        return Ok(None)
