"""R2X Core Library."""

from importlib.metadata import version

from loguru import logger

from . import h5_readers
from .datafile import (
    DataFile,
)
from .exceptions import ComponentCreationError, ExporterError, ParserError, UpgradeError, ValidationError
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
from .result import Err, Ok, Result, is_err, is_ok
from .store import DataStore
from .system import System
from .units import HasPerUnit, HasUnits, Unit, UnitSystem, get_unit_system, set_unit_system
from .upgrader import PluginUpgrader
from .upgrader_utils import (
    UpgradeStep,
    UpgradeType,
    run_datafile_upgrades,
    run_system_upgrades,
    run_upgrade_step,
)
from .versioning import (
    GitVersioningStrategy,
    SemanticVersioningStrategy,
    VersionDetector,
    VersioningModel,
)

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
    "Err",
    "ExporterError",
    "FileFormat",
    "FilterFunction",
    "GitVersioningStrategy",
    "H5Format",
    "HasPerUnit",
    "HasUnits",
    "Ok",
    "ParserError",
    "PluginComponent",
    "PluginConfig",
    "PluginManager",
    "PluginUpgrader",
    "Result",
    "SemanticVersioningStrategy",
    "System",
    "SystemModifier",
    "Unit",
    "UnitSystem",
    "UpgradeError",
    "UpgradeStep",
    "UpgradeType",
    "ValidationError",
    "VersionDetector",
    "VersioningModel",
    "get_unit_system",
    "h5_readers",
    "is_err",
    "is_ok",
    "run_datafile_upgrades",
    "run_system_upgrades",
    "run_upgrade_step",
    "set_unit_system",
]
