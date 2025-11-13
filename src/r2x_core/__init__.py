"""R2X Core package public API with eager imports."""

from __future__ import annotations

from importlib.metadata import version

from loguru import logger

from . import h5_readers
from .datafile import DataFile, FileInfo, JSONProcessing, ReaderConfig, TabularProcessing
from .exceptions import (
    CLIError,
    ComponentCreationError,
    ExporterError,
    ParserError,
    UpgradeError,
    ValidationError,
)
from .exporter import BaseExporter
from .file_types import FileFormat, H5Format
from .parser import BaseParser
from .plugin import (
    ArgumentSource,
    ArgumentSpec,
    ConfigSpec,
    ImplementationType,
    InvocationSpec,
    IOContract,
    IOSlot,
    IOSlotKind,
    PluginKind,
    PluginManifest,
    PluginSpec,
    ResourceSpec,
    StoreMode,
    StoreSpec,
    UpgradeSpec,
    UpgradeStepSpec,
)
from .plugin_config import PluginConfig
from .reader import DataReader
from .result import Err, Ok, Result, is_err, is_ok
from .store import DataStore
from .system import System
from .units import HasPerUnit, HasUnits, Unit, UnitSystem, get_unit_system, set_unit_system
from .upgrader import PluginUpgrader
from .upgrader_utils import UpgradeStep, UpgradeType, run_upgrade_step
from .versioning import GitVersioningStrategy, SemanticVersioningStrategy, VersionReader, VersionStrategy

__version__ = version("r2x_core")

TIMESERIES_DIR = "R2X_TIMESERIES_DIR"

# Silence the library's logger by default; application code can configure it.
logger.disable("r2x_core")


# Public API
__all__ = [
    "ArgumentSource",
    "ArgumentSpec",
    "BaseExporter",
    "BaseParser",
    "CLIError",
    "ComponentCreationError",
    "ConfigSpec",
    "DataFile",
    "DataReader",
    "DataStore",
    "Err",
    "ExporterError",
    "FileFormat",
    "FileInfo",
    "GitVersioningStrategy",
    "H5Format",
    "HasPerUnit",
    "HasUnits",
    "IOContract",
    "IOSlot",
    "IOSlotKind",
    "ImplementationType",
    "InvocationSpec",
    "JSONProcessing",
    "Ok",
    "ParserError",
    "PluginConfig",
    "PluginKind",
    "PluginManifest",
    "PluginSpec",
    "PluginUpgrader",
    "ReaderConfig",
    "ResourceSpec",
    "Result",
    "SemanticVersioningStrategy",
    "StoreMode",
    "StoreSpec",
    "System",
    "TabularProcessing",
    "Unit",
    "UnitSystem",
    "UpgradeError",
    "UpgradeSpec",
    "UpgradeStep",
    "UpgradeStepSpec",
    "UpgradeType",
    "ValidationError",
    "VersionReader",
    "VersionStrategy",
    "get_unit_system",
    "h5_readers",
    "is_err",
    "is_ok",
    "run_upgrade_step",
    "set_unit_system",
]
