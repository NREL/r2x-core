"""Upgrade utilities for R2X Core.

This module provides the upgrade execution infrastructure including:

- **UpgradeType**: Enum defining FILE vs SYSTEM upgrade operations
- **UpgradeStep**: Named tuple representing a single upgrade operation
- **shall_we_upgrade()**: Version-based upgrade decision logic
- **run_datafile_upgrades()**: Execute file-based upgrades in priority order
- **run_system_upgrades()**: Execute system data upgrades in priority order

The upgrade system uses a priority queue where lower numbers execute first.
Version comparison is delegated to configurable VersioningModel strategies.
"""

from collections.abc import Callable
from enum import Enum
from typing import Any, NamedTuple

from loguru import logger

from .exceptions import UpgradeError
from .result import Err, Ok, Result
from .versioning import VersioningModel


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
        May optionally accept upgrader_context keyword argument.
    target_version : str
        The version this upgrade targets.
    upgrade_type : UpgradeType
        Type of upgrade: FILE or SYSTEM.
    priority : int, default=100
        Priority for upgrade execution (lower numbers run first).
    min_version : str | None, default=None
        Minimum version required for this upgrade.
    max_version : str | None, default=None
        Maximum version this upgrade is compatible with.
    """

    name: str
    func: Callable[..., Any]
    target_version: str
    upgrade_type: UpgradeType
    priority: int = 100
    min_version: str | None = None
    max_version: str | None = None


def shall_we_upgrade(
    step: UpgradeStep, current_version: str, strategy: VersioningModel | None = None
) -> Result[bool, UpgradeError]:
    """Determine if upgrade step should execute based on version constraints.

    Parameters
    ----------
    step : UpgradeStep
        Upgrade step to evaluate
    current_version : str
        Current data version
    strategy : VersioningModel | None
        Version comparison strategy; if None, always upgrade

    Returns
    -------
    Result[bool, UpgradeError]
        Ok(True) if upgrade needed, Ok(False) if skip, Err on failure

    Notes
    -----
    Skips upgrade if:
    - Already at or past target version
    - Below minimum required version
    - Above maximum supported version
    """
    if strategy is None:
        return Ok(False)

    logger.debug("Evaluating {}: current={}, target={}", step.name, current_version, step.target_version)

    if strategy.compare_versions(current_version, step.target_version) >= 0:
        logger.debug("Skipping {}: already at target version", step.name)
        return Ok(False)

    if step.min_version and strategy.compare_versions(current_version, step.min_version) < 0:
        logger.warning(
            "Skipping {}: current version {} below minimum {}",
            step.name,
            current_version,
            step.min_version,
        )
        return Ok(False)

    if step.max_version and strategy.compare_versions(current_version, step.max_version) > 0:
        logger.warning(
            "Skipping {}: current version {} above maximum {}",
            step.name,
            current_version,
            step.max_version,
        )
        return Ok(False)

    return Ok(True)


def run_system_upgrades(
    steps: list[UpgradeStep],
    data: dict[str, Any],
    current_version: str | None,
    upgrader_context: Any | None = None,
    strategy: VersioningModel | None = None,
) -> Result[dict[str, Any], str]:
    """Apply upgrade steps in priority order to system data.

    Parameters
    ----------
    steps : list[UpgradeStep]
        Upgrade steps to execute (filtered to UpgradeType.SYSTEM)
    data : dict[str, Any]
        System data dictionary to upgrade in-place
    current_version : str | None
        Current system version
    upgrader_context : Any | None
        Optional context passed to upgrade functions
    strategy : VersioningModel | None
        Version comparison strategy; skips if None

    Returns
    -------
    Result[dict[str, Any], str]
        Ok(data) on success, Err(message) on failure

    Notes
    -----
    Executes steps in priority order (lower numbers first).
    Skips if no strategy provided (cannot determine upgrade necessity).
    """
    if not steps:
        logger.debug("No upgrade steps received. Skipping.")
        return Ok(data)

    if not strategy or not current_version:
        logger.debug("No strategy provided. Cannot determine upgrade necessity. Skipping.")
        return Ok(data)

    upgrade_steps_by_priority = sorted(steps, key=lambda s: s.priority)
    applied_steps: list[str] = []
    failed_steps: list[tuple[str, UpgradeError]] = []

    logger.info("Applying {} upgrade steps", len(upgrade_steps_by_priority))
    for step in upgrade_steps_by_priority:
        upgrade_decision = shall_we_upgrade(step=step, current_version=current_version, strategy=strategy)

        if upgrade_decision.is_err():
            error = upgrade_decision.err()
            logger.error("Error evaluating upgrade decision for {}: {}", step.name, error)
            failed_steps.append((step.name, error))
            continue

        if not upgrade_decision.unwrap():
            continue

        result = run_upgrade_step(step, data, upgrader_context=upgrader_context)
        if result.is_err():
            error_str = result.err()
            logger.error("{}", error_str)
            # Convert string error to UpgradeError
            failed_steps.append((step.name, UpgradeError(error_str)))
        else:
            logger.debug("Applied {} to data.", step.name)
            applied_steps.append(step.name)
    if failed_steps:
        return Err(f"Failed steps: {failed_steps}")
    return Ok(data)


def run_datafile_upgrades(
    steps: list[UpgradeStep],
    folder_path: Any,
    current_version: str | None,
    upgrader_context: Any | None = None,
    strategy: "VersioningModel | None" = None,
) -> Result[None, str]:
    """Apply upgrade steps in priority order to data files.

    Parameters
    ----------
    steps : list[UpgradeStep]
        Upgrade steps to execute (filtered to UpgradeType.FILE)
    folder_path : Any
        Path to data folder containing files to upgrade
    current_version : str | None
        Current data version
    upgrader_context : Any | None
        Optional context passed to upgrade functions
    strategy : VersioningModel | None
        Version comparison strategy; skips if None

    Returns
    -------
    Result[None, str]
        Ok() on success, Err(message) on failure

    Notes
    -----
    Executes steps in priority order (lower numbers first).
    Skips if no strategy provided (cannot determine upgrade necessity).
    """
    if not steps:
        logger.debug("No upgrade steps received. Skipping.")
        return Ok()

    if not strategy or not current_version:
        logger.debug("No strategy provided. Cannot determine upgrade necessity. Skipping.")
        return Ok()

    upgrade_steps_by_priority = sorted(steps, key=lambda s: s.priority)
    applied_steps: list[str] = []
    failed_steps: list[tuple[str, UpgradeError]] = []

    logger.info("Applying {} upgrade steps ", len(upgrade_steps_by_priority))
    for step in upgrade_steps_by_priority:
        upgrade_decision = shall_we_upgrade(step=step, current_version=current_version, strategy=strategy)

        if upgrade_decision.is_err():
            error = upgrade_decision.err()
            logger.error("Error evaluating upgrade decision for {}: {}", step.name, error)
            failed_steps.append((step.name, error))
            continue

        if not upgrade_decision.unwrap():
            continue

        result = run_upgrade_step(step, folder_path, upgrader_context=upgrader_context)
        if result.is_err():
            error_msg = result.err()
            logger.error("{}", error_msg)
            # Convert string error to UpgradeError
            failed_steps.append((step.name, UpgradeError(error_msg)))
        else:
            logger.debug("Applied {} to data.", step.name)
            applied_steps.append(step.name)
    if failed_steps:
        return Err(f"Failed steps = {failed_steps}")
    return Ok()


def run_upgrade_step(step: UpgradeStep, data: Any, upgrader_context: Any | None = None) -> Result[Any, str]:
    """Apply a single upgrade step to data if needed (internal function)."""
    logger.debug("Applying upgrade step: {}", step.name)
    try:
        # Try to pass upgrader_context if the function accepts it
        import inspect

        sig = inspect.signature(step.func)
        if "upgrader_context" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        ):
            data = step.func(data, upgrader_context=upgrader_context)
        else:
            data = step.func(data)
    except Exception as e:
        return Err(f"Failed {step.name}: {e}")
    logger.info("Successfully applied upgrade: {} -> {}", step.name, step.target_version)
    return Ok(data)
