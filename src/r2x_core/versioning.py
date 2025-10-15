"""Versioning strategies for R2X Core.

This module provides versioning strategy implementations for version management
in data and system upgrades.

Classes
-------
VersioningStrategy
    Protocol defining the interface for version management.
SemanticVersioningStrategy
    Implementation using semantic versioning (e.g., "1.2.3").
GitVersioningStrategy
    Implementation using git commit hashes or timestamps.
FileModTimeStrategy
    Implementation using file modification timestamps.

Examples
--------
Use semantic versioning strategy:

>>> from r2x_core.versioning import SemanticVersioningStrategy
>>> strategy = SemanticVersioningStrategy(version_field="version")
>>> data = {"version": "1.0.0", "value": 10}
>>> current = strategy.get_version(data)  # "1.0.0"
>>> comparison = strategy.compare(current, "2.0.0")  # -1 (current < target)
>>> updated_data = strategy.set_version(data, "2.0.0")

Use git versioning strategy:

>>> from r2x_core.versioning import GitVersioningStrategy
>>> strategy = GitVersioningStrategy(use_timestamps=True)
>>> data = {"git_version": "2024-01-01T00:00:00Z"}
>>> current = strategy.get_version(data)
>>> comparison = strategy.compare(current, "2024-06-01T00:00:00Z")  # -1
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from loguru import logger
from packaging.version import Version


class VersioningStrategy(Protocol):
    """Protocol for version management strategies.

    This protocol defines the interface that all versioning strategies must implement.
    It allows plugins to define their own version comparison logic while maintaining
    a consistent interface for the upgrade system.

    Methods
    -------
    get_version(data) -> str | None
        Extract the current version from the data structure.
    set_version(data, version) -> Any
        Update the version in the data structure.
    compare(current, target) -> int
        Compare two versions (-1: current < target, 0: equal, 1: current > target).
    """

    @abstractmethod
    def get_version(self, data: Any) -> str | None:
        """Extract the current version from data.

        Parameters
        ----------
        data : Any
            The data structure (file, dict, model instance, etc.).

        Returns
        -------
        str | None
            Current version string, or None if no version found.
        """
        ...

    @abstractmethod
    def set_version(self, data: Any, version: str) -> Any:
        """Update the version in the data structure.

        Parameters
        ----------
        data : Any
            The data structure to update.
        version : str
            The new version to set.

        Returns
        -------
        Any
            The updated data structure.
        """
        ...

    @abstractmethod
    def compare(self, current: str | None, target: str) -> int:
        """Compare two versions.

        Parameters
        ----------
        current : str | None
            Current version string, None treated as "0.0.0" or earliest.
        target : str
            Target version string.

        Returns
        -------
        int
            -1 if current < target, 0 if equal, 1 if current > target.
        """
        ...


class SemanticVersioningStrategy(VersioningStrategy):
    """Semantic versioning strategy using packaging.version.

    Parameters
    ----------
    version_field : str, default="version"
        The field name where version is stored in data structures.
    default_version : str, default="0.0.0"
        Default version to use when no version is found.

    Examples
    --------
    >>> strategy = SemanticVersioningStrategy()
    >>> data = {"version": "1.0.0"}
    >>> strategy.get_version(data)
    '1.0.0'
    >>> strategy.compare("1.0.0", "2.0.0")
    -1
    >>> strategy.set_version(data, "2.0.0")
    {'version': '2.0.0'}
    """

    def __init__(self, version_field: str = "version", default_version: str = "0.0.0"):
        """Initialize semantic versioning strategy.

        Parameters
        ----------
        version_field : str, default="version"
            Name of the field containing version information in data structures.
        default_version : str, default="0.0.0"
            Default version to use when no version is found. Used as the current
            version when comparing against None.
        """
        self.version_field = version_field
        self.default_version = default_version

    def get_version(self, data: Any) -> str | None:
        """Extract version from data structure.

        Supports dictionaries, objects with attributes, and returns None for
        file paths or unsupported types.

        Parameters
        ----------
        data : Any
            Data structure to extract version from (dict, object, or Path).

        Returns
        -------
        str | None
            Version string if found, None otherwise.
        """
        if isinstance(data, dict):
            version = data.get(self.version_field)
            return str(version) if version is not None else None
        elif hasattr(data, self.version_field):
            version = getattr(data, self.version_field)
            return str(version) if version is not None else None
        elif isinstance(data, (str, Path)):
            return None
        return None

    def set_version(self, data: Any, version: str) -> Any:
        """Set version in data structure.

        Updates the version field in dictionaries or object attributes.
        Logs a warning for unsupported types.

        Parameters
        ----------
        data : Any
            Data structure to update (dict or object with attributes).
        version : str
            New version string to set.

        Returns
        -------
        Any
            The updated data structure.
        """
        if isinstance(data, dict):
            data[self.version_field] = version
            return data
        elif hasattr(data, self.version_field):
            setattr(data, self.version_field, version)
            return data
        else:
            logger.warning("Cannot set version on data type: {}", type(data))
            return data

    def compare(self, current: str | None, target: str) -> int:
        """Compare two semantic versions.

        Uses packaging.version.Version for proper semantic version comparison.
        None is treated as the default_version.

        Parameters
        ----------
        current : str | None
            Current version string. None is treated as default_version.
        target : str
            Target version string to compare against.

        Returns
        -------
        int
            -1 if current < target (upgrade needed)
            0 if current == target (versions equal)
            1 if current > target (current is newer)
        """
        current_version = Version(current or self.default_version)
        target_version = Version(target)

        if current_version < target_version:
            return -1
        elif current_version > target_version:
            return 1
        else:
            return 0


class GitVersioningStrategy(VersioningStrategy):
    """Git-based versioning strategy using commit hashes or timestamps.

    Parameters
    ----------
    version_field : str, default="git_version"
        The field name where git version is stored.
    use_timestamps : bool, default=False
        Whether to treat versions as ISO timestamps for comparison.
    """

    def __init__(self, version_field: str = "git_version", use_timestamps: bool = False):
        """Initialize git versioning strategy.

        Parameters
        ----------
        version_field : str, default="git_version"
            Name of the field containing git version information (commit hash or timestamp).
        use_timestamps : bool, default=False
            If True, treat versions as ISO timestamps and compare chronologically.
            If False, compare versions as strings lexicographically.
        """
        self.version_field = version_field
        self.use_timestamps = use_timestamps

    def get_version(self, data: Any) -> str | None:
        """Extract git version from data structure.

        Supports dictionaries and objects with attributes. Returns None for
        unsupported types.

        Parameters
        ----------
        data : Any
            Data structure to extract version from (dict or object).

        Returns
        -------
        str | None
            Git version string (commit hash or timestamp) if found, None otherwise.
        """
        if isinstance(data, dict):
            version = data.get(self.version_field)
            return str(version) if version is not None else None
        elif hasattr(data, self.version_field):
            version = getattr(data, self.version_field)
            return str(version) if version is not None else None
        return None

    def set_version(self, data: Any, version: str) -> Any:
        """Set git version in data structure.

        Updates the version field in dictionaries or object attributes.
        Logs a warning for unsupported types.

        Parameters
        ----------
        data : Any
            Data structure to update (dict or object with attributes).
        version : str
            New git version string to set (commit hash or timestamp).

        Returns
        -------
        Any
            The updated data structure.
        """
        if isinstance(data, dict):
            data[self.version_field] = version
            return data
        elif hasattr(data, self.version_field):
            setattr(data, self.version_field, version)
            return data
        else:
            logger.warning("Cannot set git version on data type: {}", type(data))
            return data

    def compare(self, current: str | None, target: str) -> int:
        """Compare git versions (commit hashes or timestamps).

        If use_timestamps=True, parses versions as ISO timestamps and compares
        chronologically. Otherwise, compares strings lexicographically.

        Parameters
        ----------
        current : str | None
            Current git version (commit hash or timestamp). None means upgrade needed.
        target : str
            Target git version to compare against.

        Returns
        -------
        int
            -1 if current < target or current is None (upgrade needed)
            0 if current == target (versions equal)
            1 if current > target (current is newer)

        Warnings
        --------
        Logs warning if timestamp parsing fails when use_timestamps=True.
        """
        if current is None:
            return -1

        if self.use_timestamps:
            try:
                current_dt = datetime.fromisoformat(current.replace("Z", "+00:00"))
                target_dt = datetime.fromisoformat(target.replace("Z", "+00:00"))

                if current_dt < target_dt:
                    return -1
                elif current_dt > target_dt:
                    return 1
                else:
                    return 0
            except ValueError:
                logger.warning("Invalid timestamp format: {} or {}", current, target)
                return -1
        else:
            if current < target:
                return -1
            elif current > target:
                return 1
            else:
                return 0


class FileModTimeStrategy(VersioningStrategy):
    """File modification time versioning strategy.

    Uses file modification timestamps as versions.

    Examples
    --------
    >>> strategy = FileModTimeStrategy()
    >>> version = strategy.get_version("/path/to/file.json")
    >>> # Returns file modification time as string
    """

    def get_version(self, data: Any) -> str | None:
        """Get file modification time as version.

        Extracts the modification time from a file path. Only works with
        file paths (str or Path), returns None for other data types.

        Parameters
        ----------
        data : Any
            File path (str or Path) to get modification time from.

        Returns
        -------
        str | None
            File modification time as string (Unix timestamp), or None if
            data is not a path or file doesn't exist.
        """
        if isinstance(data, (str, Path)):
            path = Path(data)
            if path.exists():
                return str(path.stat().st_mtime)
        return None

    def set_version(self, data: Any, version: str) -> Any:
        """Set version (not supported for file modification times).

        File modification times cannot be set directly through this strategy.
        This method logs a warning and returns the data unchanged.

        Parameters
        ----------
        data : Any
            Data structure (ignored).
        version : str
            Version string (ignored).

        Returns
        -------
        Any
            The unchanged data structure.

        Warnings
        --------
        Always logs a warning that modification times cannot be set directly.
        """
        logger.warning("Cannot set file modification time directly")
        return data

    def compare(self, current: str | None, target: str) -> int:
        """Compare file modification timestamps.

        Compares timestamps as floating point numbers (Unix timestamps).

        Parameters
        ----------
        current : str | None
            Current modification time as string. None means upgrade needed.
        target : str
            Target modification time to compare against.

        Returns
        -------
        int
            -1 if current < target or current is None (upgrade needed)
            0 if current == target (times equal)
            1 if current > target (current is newer)

        Warnings
        --------
        Logs warning if timestamp strings cannot be parsed as float.
        """
        if current is None:
            return -1

        try:
            current_time = float(current)
            target_time = float(target)

            if current_time < target_time:
                return -1
            elif current_time > target_time:
                return 1
            else:
                return 0
        except ValueError:
            logger.warning("Invalid timestamp: {} or {}", current, target)
            return -1


class VersionDetector(Protocol):
    """Protocol for detecting version from data folder without DataStore.

    Plugins implement this protocol to specify how to read version information
    from their data files before DataStore initialization. This enables version
    detection before file operations during upgrades.

    Methods
    -------
    detect_version(folder: Path) -> str | None
        Detect version from the data folder.

    Examples
    --------
    Implement a custom version detector:

    >>> class CustomDetector:
    ...     def detect_version(self, folder: Path) -> str | None:
    ...         version_file = folder / "VERSION"
    ...         if version_file.exists():
    ...             return version_file.read_text().strip()
    ...         return None
    >>> version = CustomDetector().detect_version(Path("/data/folder"))

    Implement a CSV-based detector:

    >>> class CSVDetector:
    ...     def detect_version(self, folder: Path) -> str | None:
    ...         import polars as pl
    ...         csv_path = folder / "metadata.csv"
    ...         if csv_path.exists():
    ...             df = pl.read_csv(csv_path)
    ...             return str(df.filter(pl.col("field") == "version")["value"][0])
    ...         return None

    See Also
    --------
    PluginManager.register_version_detector : Register detector for a plugin
    """

    @abstractmethod
    def detect_version(self, folder: Path) -> str | None:
        """Detect version from data folder.

        This method is called before DataStore initialization and should
        read version information using minimal file I/O operations.

        Parameters
        ----------
        folder : Path
            Path to the data folder.

        Returns
        -------
        str | None
            Version string if detected, None otherwise.

        Notes
        -----
        Implementations should handle missing files gracefully and
        return None rather than raising exceptions.
        """
        ...
