"""R2X Core package public API with lazy relative imports.

This module exposes the most commonly used package symbols but defers importing
heavy implementation modules until attributes are accessed. Deferring imports
avoids creating import cycles when submodules import the package root.

Design notes
- All runtime imports are performed with relative module names (starting with '.')
  and importlib.import_module(..., package=__name__). That keeps imports
  local to the package and prevents touching the top-level package during module
  import resolution.
- Type-only imports used by static checkers are performed inside a TYPE_CHECKING
  block using relative imports as well.
- Accessed attributes are cached on the package module to avoid repeated imports.
"""

from __future__ import annotations

import importlib
from importlib.metadata import version
from typing import Any

from loguru import logger

__version__ = version("r2x_core")

TIMESERIES_DIR = "R2X_TIMESERIES_DIR"

# Silence the library's logger by default; application code can configure it.
logger.disable("r2x_core")

# NOTE: module paths are package-relative. We will pass package=__name__ to
# importlib.import_module so the relative imports are resolved to this package.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    # Exceptions
    "CLIError": (".exceptions", "CLIError"),
    "ComponentCreationError": (".exceptions", "ComponentCreationError"),
    "ExporterError": (".exceptions", "ExporterError"),
    "ParserError": (".exceptions", "ParserError"),
    "UpgradeError": (".exceptions", "UpgradeError"),
    "ValidationError": (".exceptions", "ValidationError"),
    # Core data and services
    "DataFile": (".datafile", "DataFile"),
    "FileInfo": (".datafile", "FileInfo"),
    "ReaderConfig": (".datafile", "ReaderConfig"),
    "TabularProcessing": (".datafile", "TabularProcessing"),
    "JSONProcessing": (".datafile", "JSONProcessing"),
    "TabularTransformations": (".datafile", "TabularTransformations"),
    "JSONTransformations": (".datafile", "JSONTransformations"),
    "FileTransform": (".store", "FileTransform"),
    "DataReader": (".reader", "DataReader"),
    "DataStore": (".store", "DataStore"),
    "System": (".system", "System"),
    # Parser / exporter base classes
    "BaseExporter": (".exporter", "BaseExporter"),
    "BaseParser": (".parser", "BaseParser"),
    # Plugin configuration
    "PluginConfig": (".plugin_config", "PluginConfig"),
    "PluginUpgrader": (".plugin_config", "PluginUpgrader"),
    # Result types
    "Result": (".result", "Result"),
    "Ok": (".result", "Ok"),
    "Err": (".result", "Err"),
    "is_ok": (".result", "is_ok"),
    "is_err": (".result", "is_err"),
    # File formats and readers
    "FileFormat": (".file_types", "FileFormat"),
    "H5Format": (".file_types", "H5Format"),
    "h5_readers": (".h5_readers", None),
    # Utilities / CLI helpers
    "execute_parser": (".cli", "execute_parser"),
    "execute_exporter": (".cli", "execute_exporter"),
    "execute_sysmod": (".cli", "execute_sysmod"),
    "list_plugins": (".cli", "list_plugins"),
    "plugin_info": (".cli", "plugin_info"),
    "extract_plugin_schema": (".cli", "extract_plugin_schema"),
    # Versioning
    "VersionDetector": (".versioning", "VersionDetector"),
    "VersioningModel": (".versioning", "VersioningModel"),
    "GitVersioningStrategy": (".versioning", "GitVersioningStrategy"),
    "SemanticVersioningStrategy": (".versioning", "SemanticVersioningStrategy"),
    # Units
    "HasUnits": (".units", "HasUnits"),
    "HasPerUnit": (".units", "HasPerUnit"),
    "Unit": (".units", "Unit"),
    "UnitSystem": (".units", "UnitSystem"),
    "get_unit_system": (".units", "get_unit_system"),
    "set_unit_system": (".units", "set_unit_system"),
    # Upgrader helpers
    "UpgradeStep": (".upgrader_utils", "UpgradeStep"),
    "UpgradeType": (".upgrader_utils", "UpgradeType"),
    "run_datafile_upgrades": (".upgrader_utils", "run_datafile_upgrades"),
    "run_system_upgrades": (".upgrader_utils", "run_system_upgrades"),
    "run_upgrade_step": (".upgrader_utils", "run_upgrade_step"),
    # Serialization utilities
    "Package": (".package", "Package"),
    "ParserPlugin": (".plugin", "ParserPlugin"),
    "ExporterPlugin": (".plugin", "ExporterPlugin"),
    "UpgraderPlugin": (".plugin", "UpgraderPlugin"),
}


def __getattr__(name: str) -> Any:
    """Lazily import and cache attributes defined in _LAZY_IMPORTS.

    Uses package-relative module names so import resolution stays inside
    this package and avoids starting an import of the top-level package
    that could trigger import cycles.
    """
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _LAZY_IMPORTS[name]
    # importlib.import_module accepts relative names when package is provided
    module = importlib.import_module(module_name, package=__name__)
    value = module if attr_name is None else getattr(module, attr_name)
    # Cache the resolved attribute on the package module for subsequent access
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Extend dir() with the lazily-provided attributes."""
    names = set(globals().keys())
    names.update(_LAZY_IMPORTS.keys())
    return sorted(names)


# Public API
__all__ = [
    "BaseExporter",
    "BaseParser",
    "CLIError",
    "ComponentCreationError",
    "DataFile",
    "DataReader",
    "DataStore",
    "Err",
    "ExporterError",
    "ExporterPlugin",
    "FileFormat",
    "FileInfo",
    "FileTransform",
    "GitVersioningStrategy",
    "H5Format",
    "HasPerUnit",
    "HasUnits",
    "JSONProcessing",
    "JSONTransformations",
    "Ok",
    "Package",
    "ParserError",
    "ParserPlugin",
    "PluginConfig",
    "PluginUpgrader",
    "ReaderConfig",
    "Result",
    "SemanticVersioningStrategy",
    "System",
    "TabularProcessing",
    "TabularTransformations",
    "Unit",
    "UnitSystem",
    "UpgradeError",
    "UpgradeStep",
    "UpgradeType",
    "UpgraderPlugin",
    "ValidationError",
    "VersionDetector",
    "VersioningModel",
    "execute_exporter",
    "execute_parser",
    "execute_sysmod",
    "extract_plugin_schema",
    "get_unit_system",
    "h5_readers",
    "is_err",
    "is_ok",
    "list_plugins",
    "plugin_info",
    "run_datafile_upgrades",
    "run_system_upgrades",
    "run_upgrade_step",
    "set_unit_system",
]
