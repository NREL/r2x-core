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
>>>
>>> PluginManager.register_upgrade_step("my_plugin", step1)
>>> PluginManager.register_upgrade_step("my_plugin", step2)
"""

from __future__ import annotations

import shutil
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


def apply_upgrade(data: Any, step: UpgradeStep) -> tuple[Any, bool]:
    """Apply an upgrade step to data if needed.

    This function determines if an upgrade is necessary by comparing versions,
    executes the upgrade if needed, and updates the version in the data.

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
    >>> upgraded_data, applied = apply_upgrade(data, upgrade_step)
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

    type_str = upgrade_type.value if upgrade_type else "all types"
    logger.info("Applying upgrades - Type: {}, {} steps to consider", type_str, len(sorted_steps))

    for step in sorted_steps:
        try:
            current_data, was_applied = apply_upgrade(current_data, step)
            if was_applied:
                applied_steps.append(step.name)
        except Exception as e:
            logger.error("Upgrade step {} failed: {}", step.name, e)
            # Continue with other steps rather than failing completely
            continue

    logger.info("Completed upgrades. Applied: {}", applied_steps)
    return current_data, applied_steps


def upgrade_data(
    data_folder: Path | str,
    upgrader: str,
) -> Path:
    """Upgrade raw data files before parser initialization.

    This is the standard upgrade workflow for file operations on raw data
    before the parser and DataStore are initialized.

    Moves the original folder to a backup location with ".backup" suffix,
    then creates a copy at the original location where upgrades are applied.
    This approach is faster than copying for large datasets while maintaining
    a backup for safety.

    This function:
    1. Detects the current version from the data folder
    2. Moves the original folder to "{folder_name}.backup"
    3. Creates a copy from backup to original location
    4. Applies file operations to the original location (rename, move, restructure files)
    5. Returns the path to the upgraded folder (original location)

    Parameters
    ----------
    data_folder : Path or str
        Path to data folder to upgrade.
    upgrader : str
        Plugin name for upgrades.

    Returns
    -------
    Path
        Path to upgraded folder (same as input path).

    Raises
    ------
    FileNotFoundError
        If data folder doesn't exist.

    Examples
    --------
    Basic upgrade workflow:

    >>> upgraded_folder = upgrade_data(
    ...     data_folder="/data/old_format",
    ...     upgrader="my_plugin"
    ... )
    >>> # upgraded_folder will be "/data/old_format" (original location)
    >>> # backup created at "/data/old_format.backup"
    >>> # Use upgraded_folder for parser initialization
    >>> config = MyPluginConfig.from_json("config.json")
    >>> data_store = DataStore.from_json("config.json", upgraded_folder)

    See Also
    --------
    UpgradeType : Enum defining upgrade operation types
    apply_upgrades : Lower-level function for applying upgrades
    """
    from .plugins import PluginManager

    folder = Path(data_folder)

    if not folder.exists():
        raise FileNotFoundError(f"Data folder not found: {folder}")

    # Detect version from data folder
    version = PluginManager.detect_version(upgrader, folder)
    logger.info(
        "Detected version: {} for plugin '{}'",
        version if version else "unknown (will apply all upgrades)",
        upgrader,
    )

    # Get only file operation upgrade steps
    steps = PluginManager.get_upgrade_steps(upgrader)
    file_ops = [s for s in steps if s.upgrade_type == UpgradeType.FILE]

    if not file_ops:
        logger.info("No file operation upgrades found for plugin {}", upgrader)
        return folder

    logger.info("Found {} file operations for plugin {}", len(file_ops), upgrader)

    # Move original to backup
    backup_folder = folder.parent / f"{folder.name}_backup"
    if backup_folder.exists():
        logger.warning("Backup folder already exists, removing: {}", backup_folder)
        shutil.rmtree(backup_folder)
    shutil.move(str(folder), str(backup_folder))
    logger.info("Moved original folder to backup: {}", backup_folder)

    # Copy backup to original location for upgrades
    shutil.copytree(backup_folder, folder)

    _, applied = apply_upgrades(folder, file_ops, upgrade_type=UpgradeType.FILE)
    logger.info("Applied {} file operations: {}", len(applied), applied)
    return folder
