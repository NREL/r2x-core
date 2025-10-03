"""R2X Core Library"""

from importlib.metadata import version

__version__ = version("r2x_core")


from .datafile import (
    DataFile,
)
from .file_types import FileType
from .reader import DataReader
from .store import DataStore

__all__ = ["DataFile", "DataStore", "DataReader", "FileType"]
