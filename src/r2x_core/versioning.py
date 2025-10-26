"""Versioning strategies for R2X Core.

Provides pluggable version comparison strategies for upgrade systems.

Classes
-------
VersioningModel
    Protocol defining version comparison interface
SemanticVersioningStrategy
    Compares semantic versions (e.g., "1.2.3")
GitVersioningStrategy
    Compares versions using git commit history order

Examples
--------
Semantic versioning:

>>> from r2x_core.versioning import SemanticVersioningStrategy
>>> strategy = SemanticVersioningStrategy()
>>> strategy.compare_versions("1.0.0", "2.0.0")  # -1 (1.0.0 < 2.0.0)

Git-based versioning:

>>> from r2x_core.versioning import GitVersioningStrategy
>>> commits = ["abc123", "def456", "ghi789"]
>>> strategy = GitVersioningStrategy(commits)
>>> strategy.compare_versions("abc123", "def456")  # -1 (older < newer)
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, Protocol


class VersioningModel(Protocol):
    """Protocol for version comparison strategies.

    Defines interface for comparing versions across different versioning schemes.
    Implementations include semantic versioning and git-based versioning.
    """

    @abstractmethod
    def compare_versions(self, current: Any, target: Any) -> int:
        """Compare two versions.

        Parameters
        ----------
        current : Any
            Current version string
        target : Any
            Target version string

        Returns
        -------
        int
            -1 if current < target, 0 if equal, 1 if current > target
        """
        raise NotImplementedError


class SemanticVersioningStrategy(VersioningModel):
    """Semantic versioning comparison using Python's string comparison.

    Compares versions following major.minor.patch format.
    Uses simple string comparison (assumes properly formatted versions).

    Examples
    --------
    >>> strategy = SemanticVersioningStrategy()
    >>> strategy.compare_versions("1.0.0", "2.0.0")
    -1
    >>> strategy.compare_versions("2.0.0", "2.0.0")
    0
    >>> strategy.compare_versions("3.0.0", "2.0.0")
    1

    Notes
    -----
    Does not handle pre-release suffixes (rc, alpha, beta).
    For complex semantic versioning, use packaging.version.Version instead.
    """

    def compare_versions(self, current: str, target: str) -> int:
        """Compare two semantic versions using numeric comparison.

        Splits versions into components and compares numerically.
        Handles different component lengths (1.0 vs 1.0.0).
        """
        current_parts = [int(x) for x in current.split(".")]
        target_parts = [int(x) for x in target.split(".")]

        max_len = max(len(current_parts), len(target_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        target_parts.extend([0] * (max_len - len(target_parts)))

        if current_parts < target_parts:
            return -1
        if current_parts > target_parts:
            return 1
        return 0


class GitVersioningStrategy(VersioningModel):
    """Git-based versioning using commit history order.

    Compares versions by their position in a git commit history.
    Earlier commits are considered older versions.

    Parameters
    ----------
    commit_history : list[str]
        List of commit hashes ordered from oldest to newest

    Examples
    --------
    >>> commits = ["abc123", "def456", "ghi789"]
    >>> strategy = GitVersioningStrategy(commits)
    >>> strategy.compare_versions("abc123", "def456")
    -1
    >>> strategy.compare_versions("def456", "def456")
    0
    >>> strategy.compare_versions("ghi789", "def456")
    1
    """

    def __init__(self, commit_history: list[str]) -> None:
        """Initialize Git versioning strategy.

        Parameters
        ----------
        commit_history : list[str]
            List of commit hashes ordered from oldest to newest
        """
        self.commit_history = commit_history

    def compare_versions(self, current: str | None, target: str) -> int:
        """Compare git versions using commit history position.

        Parameters
        ----------
        current : str | None
            Current git commit hash
        target : str
            Target git commit hash

        Returns
        -------
        int
            -1 if current older than target
            0 if current == target
            1 if current newer than target

        Raises
        ------
        ValueError
            If current or target not found in commit_history
        """
        if current is None:
            raise ValueError("Current version cannot be None")

        is_current_in_history = current not in self.commit_history
        is_target_in_history = target not in self.commit_history

        if is_current_in_history or is_target_in_history:
            msg = f"Failed to find commits in history. Is current in history? {is_current_in_history}"
            msg += f" Is target in history? {is_target_in_history}"
            raise ValueError(msg)
        current_idx = self.commit_history.index(current)
        target_idx = self.commit_history.index(target)
        if current_idx < target_idx:
            return -1
        if current_idx > target_idx:
            return 1
        return 0


class VersionDetector(Protocol):
    """Protocol for detecting version from data files.

    Plugins implement this to read version information from data files
    before DataStore initialization, enabling version detection for upgrades.

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
    def detect_version(self, folder_path: Path) -> str | None:
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
