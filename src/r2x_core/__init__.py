"""R2X Core Library."""

from importlib.metadata import version

from loguru import logger

from . import h5_readers
from .datafile import (
    DataFile,
)
from .exceptions import (
    ComponentCreationError,
    ExporterError,
    ParserError,
    ValidationError,
)
from .exporter import BaseExporter
from .file_types import FileFormat, H5Format
from .parser import BaseParser
from .plugin_config import PluginConfig
from .plugins import (
    FilterFunction,
    PluginComponent,
    PluginManager,
    SystemModifier,
)
from .reader import DataReader
from .store import DataStore
from .system import System
from .units import HasPerUnit, HasUnits, Unit, UnitSystem, get_unit_system, set_unit_system

__version__ = version("r2x_core")

# Disable default loguru handler for library usage
# Applications using this library should configure their own handlers
logger.disable("r2x_core")

__all__ = [
    "BaseExporter",
    "BaseParser",
    "ComponentCreationError",
    "DataFile",
    "DataReader",
    "DataStore",
    "ExporterError",
    "FileFormat",
    "FilterFunction",
    "H5Format",
    "HasPerUnit",
    "HasUnits",
    "ParserError",
    "PluginComponent",
    "PluginConfig",
    "PluginManager",
    "System",
    "SystemModifier",
    "Unit",
    "UnitSystem",
    "ValidationError",
    "get_unit_system",
    "h5_readers",
    "set_unit_system",
]
