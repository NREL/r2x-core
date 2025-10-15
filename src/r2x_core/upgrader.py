"""Upgrade system for R2X Core.

This module provides a two-tier upgrade mechanism for R2X Core plugins:

**FILE**: File operations on raw data before parser initialization (default workflow)
**SYSTEM**: System object modifications for cached systems only

Classes
-------
UpgradeType
    Enum defining upgrade types (FILE or SYSTEM).
UpgradeStep
    Named tuple defining an upgrade step with versioning and type information.

Functions
---------
upgrade_data
    Main entry point for file upgrades (file operations on raw data).
apply_upgrade
    Apply a single upgrade step to data if needed.
apply_upgrades
    Apply multiple upgrade steps in priority order.

Examples
--------
Upgrade raw data files before parser (default workflow):

>>> from r2x_core import upgrade_data
>>> upgraded_folder = upgrade_data(
...     data_folder="/data/v1",
...     upgrader="my_plugin"
... )
>>> # Use upgraded folder for parser
>>> config = MyPluginConfig.from_json("config.json")
>>> data_store = DataStore.from_json("config.json", upgraded_folder)

Upgrade cached system (only when loading saved systems):

>>> from r2x_core import System
>>> system = System.from_json("system.json", upgrader="my_plugin")

Register upgrade steps:

>>> from r2x_core import UpgradeStep, UpgradeType
>>> from r2x_core.versioning import SemanticVersioningStrategy
>>> from r2x_core.plugins import PluginManager
>>>
>>> # File upgrade (rename data files)
>>> def rename_files(folder):
...     old_file = folder / "buses.csv"
...     if old_file.exists():
...         old_file.rename(folder / "nodes.csv")
...     return folder
>>>
>>> step1 = UpgradeStep(
...     name="rename_bus_files",
...     func=rename_files,
...     target_version="2.0.0",
...     versioning_strategy=SemanticVersioningStrategy(),
...     upgrade_type=UpgradeType.FILE
... )
>>>
>>> # System upgrade (update cached system)
>>> def upgrade_system(system):
...     system.metadata["upgraded_to"] = "2.0.0"
...     return system
>>>
>>> step2 = UpgradeStep(
...     name="upgrade_system_to_v2",
...     func=upgrade_system,
...     target_version="2.0.0",
...     versioning_strategy=SemanticVersioningStrategy(),
...     upgrade_type=UpgradeType.SYSTEM
... )
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from loguru import logger

if TYPE_CHECKING:
    from r2x_core.versioning import VersioningStrategy


class UpgradeType(str, Enum):
    """Type of upgrade operation.

    Attributes
    ----------
    FILE : str
        File system operations on raw data files (rename, move, modify).
        Applied before parser and DataStore initialization via upgrade_data().
        This is the default upgrade type used in the normal parser workflow.
    SYSTEM : str
        System object modifications for cached systems.
        Applied when loading saved systems via System.from_json(upgrader=...).
        Only used when loading cached systems, not in the default parser workflow.
    """

    FILE = "FILE"
    SYSTEM = "SYSTEM"


class UpgradeStep(NamedTuple):
    """Definition of a single upgrade step.

    Attributes
    ----------
    name : str
        Unique name for the upgrade step.
    func : callable
        Function to execute the upgrade. Should accept data and return upgraded data.
    target_version : str
        The version this upgrade targets.
    versioning_strategy : VersioningStrategy
        Strategy for version management.
    upgrade_type : UpgradeType
        Type of upgrade: FILE or SYSTEM.
    priority : int, default=100
        Priority for upgrade execution (lower numbers run first).
    min_version : str | None, default=None
        Minimum version required for this upgrade.
    max_version : str | None, default=None
        Maximum version this upgrade is compatible with.

    Examples
    --------
    File upgrade:

    >>> from r2x_core.versioning import SemanticVersioningStrategy
    >>> from pathlib import Path
    >>> def rename_files(folder: Path) -> Path:
    ...     old_file = folder / "buses.csv"
    ...     if old_file.exists():
    ...         old_file.rename(folder / "nodes.csv")
    ...     return folder
    >>>
    >>> step = UpgradeStep(
    ...     name="rename_bus_files",
    ...     func=rename_files,
    ...     target_version="2.0.0",
    ...     versioning_strategy=SemanticVersioningStrategy(),
    ...     upgrade_type=UpgradeType.FILE
    ... )

    System upgrade (for cached systems only):

    >>> def upgrade_system(system):
    ...     system.metadata["upgraded_to"] = "2.0.0"
    ...     return system
    >>>
    >>> step = UpgradeStep(
    ...     name="upgrade_system_to_v2",
    ...     func=upgrade_system,
    ...     target_version="2.0.0",
    ...     versioning_strategy=SemanticVersioningStrategy(),
    ...     upgrade_type=UpgradeType.SYSTEM
    ... )
    """

    name: str
    func: Callable[[Any], Any]
    target_version: str
    versioning_strategy: VersioningStrategy
    upgrade_type: UpgradeType
    priority: int = 100
    min_version: str | None = None
    max_version: str | None = None


class DataUpgrader(ABC):
    """Base class for plugin data upgraders.

    Plugins must inherit from this class and implement:
    1. strategy: VersioningStrategy class variable
    2. detect_version(): Static method to detect version from folder

    The base class provides:
    - steps: Class variable to hold registered upgrade steps
    - upgrade(): Method to run all upgrades
    - upgrade_step(): Decorator to register upgrade steps

    Examples
    --------
    Create a plugin upgrader:

    >>> from r2x_core.upgrader import DataUpgrader
    >>> from r2x_core.versioning import SemanticVersioningStrategy
    >>> from pathlib import Path
    >>>
    >>> class MyPluginUpgrader(DataUpgrader):
    ...     strategy = SemanticVersioningStrategy()
    ...
    ...     @staticmethod
    ...     def detect_version(folder: Path) -> str | None:
    ...         version_file = folder / "version.txt"
    ...         if version_file.exists():
    ...             return version_file.read_text().strip()
    ...         return None

    Register upgrade steps with decorator:

    >>> @MyPluginUpgrader.upgrade_step(
    ...     target_version="2.0.0",
    ...     upgrade_type=UpgradeType.FILE
    ... )
    ... def my_upgrade(folder: Path) -> Path:
    ...     # Upgrade logic
    ...     return folder

    Run upgrades:

    >>> folder = Path("/data")
    >>> upgraded = MyPluginUpgrader.upgrade(folder)
    """

    steps: list[UpgradeStep] = []  # noqa: RUF012

    @property
    @abstractmethod
    def strategy(self) -> VersioningStrategy:
        """Return versioning strategy for this upgrader (required)."""

    @staticmethod
    @abstractmethod
    def detect_version(folder: Path) -> str | None:
        """Detect version from data folder (required).

        Parameters
        ----------
        folder : Path
            Data folder to detect version from.

        Returns
        -------
        str | None
            Version string or None if not found.
        """

    @classmethod
    def upgrade(cls, folder: Path) -> Path:
        """Upgrade data folder to latest version.

        This is the main entry point for upgrading data.

        Parameters
        ----------
        folder : Path
            Data folder to upgrade.

        Returns
        -------
        Path
            Path to upgraded folder.

        Examples
        --------
        >>> from reeds_plugin import ReedsDataUpgrader
        >>> upgraded = ReedsDataUpgrader.upgrade(Path("/data"))
        """
        upgraded_folder, _ = apply_upgrades(folder, cls.steps, upgrade_type=UpgradeType.FILE)
        return Path(upgraded_folder)

    @classmethod
    def upgrade_step(
        cls,
        target_version: str,
        upgrade_type: UpgradeType,
        priority: int = 100,
    ) -> Callable[[Callable[[Path], Path]], Callable[[Path], Path]]:
        """Register an upgrade step via decorator.

        Can be used from any module to register steps to this upgrader.

        Parameters
        ----------
        target_version : str
            Target version for this upgrade.
        upgrade_type : UpgradeType
            Type of upgrade (FILE or SYSTEM).
        priority : int, default=100
            Execution priority (lower runs first).

        Examples
        --------
        >>> @MyPluginUpgrader.upgrade_step(
        ...     target_version="2.0.0",
        ...     upgrade_type=UpgradeType.FILE
        ... )
        ... def my_upgrade(folder: Path) -> Path:
        ...     # Upgrade logic
        ...     return folder
        """

        def decorator(func: Callable[[Path], Path]) -> Callable[[Path], Path]:
            """Inner decorator function that registers the upgrade step.

            Parameters
            ----------
            func : Callable
                The upgrade function to register.

            Returns
            -------
            Callable
                The original function unchanged.
            """
            # Get strategy - access via __dict__ to check if it's a class variable
            # If not in __dict__, it's a property and we need to instantiate to get it
            strategy_value = cls.__dict__["strategy"] if "strategy" in cls.__dict__ else cls().strategy

            step = UpgradeStep(
                name=func.__name__,
                func=func,
                target_version=target_version,
                versioning_strategy=strategy_value,
                upgrade_type=upgrade_type,
                priority=priority,
            )
            cls.steps.append(step)
            return func

        return decorator


def _apply_upgrade(data: Any, step: UpgradeStep) -> tuple[Any, bool]:
    """Apply a single upgrade step to data if needed (internal function).

    This is an internal function that determines if an upgrade is necessary
    by comparing versions, executes the upgrade if needed, and updates the
    version in the data.

    Users should typically use apply_upgrades() instead, which orchestrates
    multiple upgrade steps. This function is exposed for testing purposes.

    Parameters
    ----------
    data : Any
        The data to potentially upgrade.
    step : UpgradeStep
        The upgrade step to apply.

    Returns
    -------
    tuple[Any, bool]
        Tuple of (upgraded_data, was_applied).

    Examples
    --------
    >>> data = {"buses": [...], "version": "1.0.0"}
    >>> upgraded_data, applied = _apply_upgrade(data, upgrade_step)
    >>> if applied:
    ...     print(f"Upgraded to {step.target_version}")
    """
    logger.debug("Checking upgrade step: {}", step.name)

    try:
        # Get current version
        current_version = step.versioning_strategy.get_version(data)
        logger.debug("Current version: {}, Target: {}", current_version, step.target_version)

        # Compare versions
        comparison = step.versioning_strategy.compare(current_version, step.target_version)

        # Check if upgrade is needed
        if comparison >= 0:
            logger.debug("Skipping {}: current version >= target", step.name)
            return data, False

        # Check version constraints
        if step.min_version is not None:
            min_comparison = step.versioning_strategy.compare(current_version, step.min_version)
            if min_comparison < 0:
                logger.warning(
                    "Skipping {}: current version < minimum required ({})",
                    step.name,
                    step.min_version,
                )
                return data, False

        if step.max_version is not None:
            max_comparison = step.versioning_strategy.compare(current_version, step.max_version)
            if max_comparison > 0:
                logger.warning(
                    "Skipping {}: current version > maximum supported ({})",
                    step.name,
                    step.max_version,
                )
                return data, False

        # Apply upgrade
        logger.info("Applying upgrade step: {}", step.name)
        upgraded_data = step.func(data)

        # Update version
        final_data = step.versioning_strategy.set_version(upgraded_data, step.target_version)

        logger.info("Successfully applied upgrade: {} -> {}", step.name, step.target_version)
        return final_data, True

    except Exception as e:
        logger.error("Failed to apply upgrade step {}: {}", step.name, e)
        raise


def apply_upgrades(
    data: Any,
    steps: list[UpgradeStep],
    upgrade_type: UpgradeType | None = None,
) -> tuple[Any, list[str]]:
    """Apply multiple upgrade steps in priority order.

    Parameters
    ----------
    data : Any
        The data to upgrade.
    steps : list[UpgradeStep]
        List of upgrade steps to consider.
    upgrade_type : UpgradeType, optional
        Filter by upgrade type: FILE or SYSTEM.
        If None, all types are considered.

    Returns
    -------
    tuple[Any, list[str]]
        Tuple of (final_data, list_of_applied_step_names).

    Examples
    --------
    Apply file upgrades:

    >>> from pathlib import Path
    >>> folder = Path("/data")
    >>> folder, applied = apply_upgrades(
    ...     folder, all_steps, upgrade_type=UpgradeType.FILE
    ... )

    Apply system upgrades:

    >>> system = System.from_json("system.json")
    >>> system, applied = apply_upgrades(
    ...     system, all_steps, upgrade_type=UpgradeType.SYSTEM
    ... )
    """
    # Filter steps by upgrade type
    applicable_steps = steps
    if upgrade_type is not None:
        applicable_steps = [s for s in applicable_steps if s.upgrade_type == upgrade_type]

    # Sort by priority (lower numbers first)
    sorted_steps = sorted(applicable_steps, key=lambda s: s.priority)

    current_data = data
    applied_steps: list[str] = []

    if upgrade_type is not None:
        logger.info(
            "Applying {} upgrade steps (type: {})",
            len(sorted_steps),
            upgrade_type.value,
        )
    else:
        logger.info("Applying {} upgrade steps (all types)", len(sorted_steps))

    for step in sorted_steps:
        try:
            current_data, was_applied = _apply_upgrade(current_data, step)
            if was_applied:
                applied_steps.append(step.name)
        except Exception as e:
            logger.error("Upgrade step {} failed: {}", step.name, e)
            # Continue with other steps rather than failing completely
            continue

    if applied_steps:
        logger.info("Completed upgrades. Applied: {}", applied_steps)
    else:
        logger.debug("No upgrades were applied")

    return current_data, applied_steps
