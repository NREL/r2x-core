"""R2X Core Library"""

from importlib.metadata import version

__version__ = version("r2x_core")


from .datafile import (
    DataFile,
)
from .exceptions import ComponentCreationError, ParserError, ValidationError
from .file_types import FileType
from .parser import BaseParser, ParserConfig
from .reader import DataReader
from .store import DataStore
from .system import System

__all__ = [
    "DataFile",
    "DataStore",
    "DataReader",
    "FileType",
    "BaseParser",
    "ParserConfig",
    "System",
    "ParserError",
    "ValidationError",
    "ComponentCreationError",
]
