"""Versioning strategies for R2X Core."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VersionStrategy(Protocol):
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


class SemanticVersioningStrategy(VersionStrategy):
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


class GitVersioningStrategy(VersionStrategy):
    """Git-based versioning using commit history order.

    Compares versions by their position in a git commit history.
    Earlier commits are considered older versions.

    Parameters
    ----------
    commit_history : list[str]
        List of commit hashes ordered from oldest to newest.

    Raises
    ------
    ValueError
        If commit_history is empty or contains non-string values.

    Examples
    --------
    Basic usage with commit history:

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
        """Initialize git versioning strategy with commit history.

        Parameters
        ----------
        commit_history : list[str]
            List of commit hashes ordered from oldest to newest.
            Can be obtained via: git log --oneline --reverse | awk '{print $1}'

        Raises
        ------
        ValueError
            If commit_history is empty or contains non-string values.
        """
        if not commit_history:
            raise ValueError("commit_history cannot be empty")
        if not all(isinstance(c, str) for c in commit_history):
            raise ValueError("All commits must be strings")

        self.commit_history = tuple(commit_history)

    def compare_versions(self, current: str | None, target: str) -> int:
        """Compare git versions by commit history position.

        Parameters
        ----------
        current : str | None
            Current commit hash.
        target : str
            Target commit hash.

        Returns
        -------
        int
            -1 if current is older than target (earlier in history).
            0 if current equals target.
            1 if current is newer than target (later in history).

        Raises
        ------
        ValueError
            If current is None, or if either commit is not found in history.
        """
        if current is None:
            raise ValueError("Current version cannot be None")

        if current not in self.commit_history:
            raise ValueError(
                f"Current commit '{current}' not found in history. "
                f"Available commits: {self.commit_history[0]} ... {self.commit_history[-1]}"
            )

        if target not in self.commit_history:
            raise ValueError(
                f"Target commit '{target}' not found in history. "
                f"Available commits: {self.commit_history[0]} ... {self.commit_history[-1]}"
            )

        current_idx = self.commit_history.index(current)
        target_idx = self.commit_history.index(target)

        if current_idx < target_idx:
            return -1
        if current_idx > target_idx:
            return 1
        return 0


@runtime_checkable
class VersionReader(Protocol):
    """Protocol for reading version from data files."""

    @abstractmethod
    def read_version(self, folder_path: Path) -> str | None:
        """Detect version from data folder."""
