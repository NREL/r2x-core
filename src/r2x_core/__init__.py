"""R2X Core package public API with eager imports."""

from __future__ import annotations

from importlib.metadata import version

from loguru import logger
from rust_ok import Err, Ok, Result, is_err, is_ok

from . import h5_readers
from .component_utils import components_to_records, export_components_to_csv
from .datafile import DataFile, FileInfo, JSONProcessing, ReaderConfig, TabularProcessing
from .enums import ArgumentSource, ImplementationType, IOSlotKind, PluginConfigAsset, PluginKind, StoreMode
from .exceptions import (
    CLIError,
    ComponentCreationError,
    PluginError,
    UpgradeError,
    ValidationError,
)
from .file_types import FileFormat, H5Format
from .getters import getter
from .plugin_base import Plugin
from .plugin_config import PluginConfig
from .plugin_context import PluginContext
from .reader import DataReader
from .result import RuleResult, TranslationResult
from .rules import Rule, RuleFilter
from .rules_executor import apply_rules_to_context, apply_single_rule
from .store import DataStore
from .system import System
from .time_series import transfer_time_series_metadata
from .units import HasPerUnit, HasUnits, Unit, UnitSystem, get_unit_system, set_unit_system
from .upgrader_utils import UpgradeStep, UpgradeType, run_upgrade_step
from .utils.parser import create_component
from .versioning import GitVersioningStrategy, SemanticVersioningStrategy, VersionReader, VersionStrategy

__version__ = version("r2x_core")

TIMESERIES_DIR = "R2X_TIMESERIES_DIR"

# Silence the library's logger by default; application code can configure it.
logger.disable("r2x_core")


# Public API
__all__ = [
    "ArgumentSource",
    "CLIError",
    "ComponentCreationError",
    "DataFile",
    "DataReader",
    "DataStore",
    "Err",
    "FileFormat",
    "FileInfo",
    "GitVersioningStrategy",
    "H5Format",
    "HasPerUnit",
    "HasUnits",
    "IOSlotKind",
    "ImplementationType",
    "JSONProcessing",
    "Ok",
    "Plugin",
    "PluginConfig",
    "PluginConfigAsset",
    "PluginContext",
    "PluginError",
    "PluginKind",
    "ReaderConfig",
    "Result",
    "Rule",
    "RuleFilter",
    "RuleResult",
    "SemanticVersioningStrategy",
    "StoreMode",
    "System",
    "TabularProcessing",
    "TranslationResult",
    "Unit",
    "UnitSystem",
    "UpgradeError",
    "UpgradeStep",
    "UpgradeType",
    "ValidationError",
    "VersionReader",
    "VersionStrategy",
    "apply_rules_to_context",
    "apply_single_rule",
    "components_to_records",
    "create_component",
    "export_components_to_csv",
    "get_unit_system",
    "getter",
    "h5_readers",
    "is_err",
    "is_ok",
    "run_upgrade_step",
    "set_unit_system",
    "transfer_time_series_metadata",
]
