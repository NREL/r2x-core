"""R2X Core Library"""

from importlib.metadata import version

__version__ = version("r2x_core")


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
from .file_types import FileFormat
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
    "ParserError",
    "PluginComponent",
    "PluginConfig",
    "PluginManager",
    "System",
    "SystemModifier",
    "ValidationError",
]
