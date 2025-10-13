"""Upgrade system for R2X Core.

This module provides the upgrade mechanism for both data context (raw files,
dictionaries) and system context (model instances).

Classes
-------
UpgradeContext
    Enum defining valid upgrade execution contexts.
UpgradeStep
    Named tuple defining an upgrade step with versioning information.
UpgradeResult
    Result of an upgrade operation with rollback capability.

Functions
---------
apply_upgrade
    Apply a single upgrade step to data if needed.
apply_upgrades
    Apply multiple upgrade steps in priority order.
apply_upgrades_with_rollback
    Apply multiple upgrade steps with rollback capability.

Examples
--------
Register an upgrade step:

>>> from r2x_core.upgrader import UpgradeStep, UpgradeContext, apply_upgrades
>>> from r2x_core.versioning import SemanticVersioningStrategy
>>> from r2x_core.plugins import PluginManager
>>>
>>> def upgrade_to_v2(data):
...     data["version"] = "2.0.0"
...     data["new_field"] = "default"
...     return data
>>>
>>> step = UpgradeStep(
...     name="upgrade_to_v2",
...     func=upgrade_to_v2,
...     target_version="2.0.0",
...     versioning_strategy=SemanticVersioningStrategy(),
...     context=UpgradeContext.DATA
... )
>>> PluginManager.register_upgrade_step("my_model", step)

Apply data upgrades:

>>> data = {"version": "1.0.0"}
>>> upgraded_data, applied = apply_upgrades(
...     data, steps, context=UpgradeContext.DATA, upgrade_type="data"
... )

Apply system upgrades:

>>> system = System.from_json("system.json")
>>> upgraded_system, applied = apply_upgrades(
...     system, steps, context=UpgradeContext.SYSTEM, upgrade_type="system"
... )
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple

from loguru import logger

if TYPE_CHECKING:
    from r2x_core.versioning import VersioningStrategy


class UpgradeContext(str, Enum):
    """Valid upgrade execution contexts.

    Attributes
    ----------
    DATA : str
        For raw data and configuration upgrades (before System creation).
    SYSTEM : str
        For System instance upgrades (after System creation).
    BOTH : str
        For upgrades that can run in either context.
    """

    DATA = "data"
    SYSTEM = "system"
    BOTH = "both"


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
    priority : int, default=100
        Priority for upgrade execution (lower numbers run first).
    context : str | UpgradeContext, default=UpgradeContext.BOTH
        Context where upgrade applies: DATA, SYSTEM, or BOTH.
    upgrade_type : str, default="data"
        Type of upgrade: "data" for raw data/configurations, "system" for System instances.
    min_version : str | None, default=None
        Minimum version required for this upgrade.
    max_version : str | None, default=None
        Maximum version this upgrade is compatible with.

    Examples
    --------
    Data upgrade step for raw configuration data:

    >>> from r2x_core.versioning import SemanticVersioningStrategy
    >>> def upgrade_data(data):
    ...     data["version"] = "2.0.0"
    ...     data["new_field"] = "default"
    ...     return data
    >>>
    >>> step = UpgradeStep(
    ...     name="upgrade_config_to_v2",
    ...     func=upgrade_data,
    ...     target_version="2.0.0",
    ...     versioning_strategy=SemanticVersioningStrategy(),
    ...     upgrade_type="data",
    ...     context=UpgradeContext.DATA
    ... )

    System upgrade step for System instances:

    >>> def upgrade_system(system):
    ...     # Modify system components or metadata
    ...     for component in system.get_components():
    ...         component.upgraded = True
    ...     return system
    >>>
    >>> step = UpgradeStep(
    ...     name="upgrade_system_to_v2",
    ...     func=upgrade_system,
    ...     target_version="2.0.0",
    ...     versioning_strategy=SemanticVersioningStrategy(),
    ...     upgrade_type="system",
    ...     context=UpgradeContext.SYSTEM
    ... )
    """

    name: str
    func: Callable[[Any], Any]
    target_version: str
    versioning_strategy: VersioningStrategy
    priority: int = 100
    context: str | UpgradeContext = UpgradeContext.BOTH
    upgrade_type: str = "data"  # "data" or "system"
    min_version: str | None = None
    max_version: str | None = None


class UpgradeResult:
    """Result of an upgrade operation with rollback capability.

    This class tracks the original data state and applied upgrades,
    allowing all-or-nothing rollback if validation fails.

    Attributes
    ----------
    original_data : Any
        Deep copy of the original data before any upgrades.
    current_data : Any
        The current state of the data after upgrades.
    applied_steps : list[str]
        List of applied upgrade step names in order.

    Examples
    --------
    Apply upgrades with validation and rollback:

    >>> result = apply_upgrades_with_rollback(data, steps)
    >>> if validate(result.current_data):
    ...     final_data = result.current_data
    ... else:
    ...     logger.warning("Validation failed, rolling back")
    ...     final_data = result.rollback()
    """

    def __init__(self, original_data: Any):
        """Initialize with original data.

        Parameters
        ----------
        original_data : Any
            The original data before any upgrades.
        """
        self.original_data = copy.deepcopy(original_data)
        self.current_data = original_data
        self.applied_steps: list[str] = []

    def add_step(self, step_name: str, data: Any) -> None:
        """Record an applied upgrade step.

        Parameters
        ----------
        step_name : str
            Name of the applied upgrade step.
        data : Any
            Data state after applying this step.
        """
        self.current_data = data
        self.applied_steps.append(step_name)
        logger.debug("Applied upgrade step '{}' (total: {})", step_name, len(self.applied_steps))

    def rollback(self) -> Any:
        """Rollback all upgrades to original state.

        Returns
        -------
        Any
            The original data before any upgrades.

        Examples
        --------
        >>> result = apply_upgrades_with_rollback(data, steps)
        >>> if not validate(result.current_data):
        ...     data = result.rollback()  # Back to original
        """
        logger.info("Rolling back all upgrades to original state")
        self.current_data = copy.deepcopy(self.original_data)
        rolled_back_steps = self.applied_steps.copy()
        self.applied_steps.clear()
        logger.info("Rolled back {} upgrade step(s): {}", len(rolled_back_steps), rolled_back_steps)
        return self.current_data


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


def _get_context_str(context: str | UpgradeContext) -> str:
    """Convert context to string value.

    Helper function to normalize UpgradeContext enum values to strings.

    Parameters
    ----------
    context : str | UpgradeContext
        Context value to normalize (enum or string).

    Returns
    -------
    str
        String representation of the context.
    """
    return context.value if isinstance(context, UpgradeContext) else context


def apply_upgrades(
    data: Any,
    steps: list[UpgradeStep],
    context: str | UpgradeContext = UpgradeContext.BOTH,
    upgrade_type: str = "data",
) -> tuple[Any, list[str]]:
    """Apply multiple upgrade steps in priority order.

    Parameters
    ----------
    data : Any
        The data to upgrade.
    steps : list[UpgradeStep]
        List of upgrade steps to consider.
    context : str | UpgradeContext, default=UpgradeContext.BOTH
        Execution context: UpgradeContext.DATA, UpgradeContext.SYSTEM, or UpgradeContext.BOTH.
        String values ("data", "system", "both") also accepted for backward compatibility.
    upgrade_type : str, default="data"
        Type of upgrade to apply: "data" for raw data, "system" for System instances.

    Returns
    -------
    tuple[Any, list[str]]
        Tuple of (final_data, list_of_applied_step_names).

    Examples
    --------
    Apply data upgrades in data context:

    >>> data = {"version": "1.0.0"}
    >>> final_data, applied = apply_upgrades(
    ...     data, all_steps, context=UpgradeContext.DATA, upgrade_type="data"
    ... )
    >>> print(f"Applied {len(applied)} upgrades: {applied}")

    Apply system upgrades in system context:

    >>> system = System.from_json("system.json")
    >>> final_system, applied = apply_upgrades(
    ...     system, all_steps, context=UpgradeContext.SYSTEM, upgrade_type="system"
    ... )
    """
    # Normalize context to string for comparison
    context_str = _get_context_str(context)

    # Filter steps by context and upgrade type
    applicable_steps = [
        step
        for step in steps
        if (_get_context_str(step.context) in (context_str, UpgradeContext.BOTH.value))
        and step.upgrade_type == upgrade_type
    ]

    # Sort by priority (lower numbers first)
    sorted_steps = sorted(applicable_steps, key=lambda s: s.priority)

    current_data = data
    applied_steps: list[str] = []

    logger.info("Applying upgrades in {} context: {} steps to consider", context, len(sorted_steps))

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


def apply_upgrades_with_rollback(
    data: Any,
    steps: list[UpgradeStep],
    context: str | UpgradeContext = UpgradeContext.BOTH,
    upgrade_type: str = "data",
    stop_on_error: bool = False,
) -> UpgradeResult:
    """Apply multiple upgrade steps with rollback capability.

    This function is similar to `apply_upgrades` but returns an `UpgradeResult`
    object that allows all-or-nothing rollback if validation fails.

    Parameters
    ----------
    data : Any
        The data to upgrade.
    steps : list[UpgradeStep]
        List of upgrade steps to consider.
    context : str | UpgradeContext, default=UpgradeContext.BOTH
        Execution context: UpgradeContext.DATA, UpgradeContext.SYSTEM, or UpgradeContext.BOTH.
        String values ("data", "system", "both") also accepted for backward compatibility.
    upgrade_type : str, default="data"
        Type of upgrade to apply: "data" for raw data, "system" for System instances.
    stop_on_error : bool, default=False
        If True, stop and rollback on first error. If False, continue with remaining steps.

    Returns
    -------
    UpgradeResult
        Object containing current state, applied steps, and rollback capability.

    Examples
    --------
    Apply upgrades with automatic rollback on validation failure:

    >>> result = apply_upgrades_with_rollback(data, steps, context=UpgradeContext.DATA)
    >>> if not validate_data(result.current_data):
    ...     logger.warning("Validation failed, rolling back")
    ...     data = result.rollback()
    ... else:
    ...     data = result.current_data

    Apply upgrades and rollback if needed:

    >>> result = apply_upgrades_with_rollback(system, steps, context=UpgradeContext.SYSTEM)
    >>> if has_issues(result.current_data):
    ...     system = result.rollback()
    ... else:
    ...     system = result.current_data
    """
    # Normalize context to string for comparison
    context_str = _get_context_str(context)

    # Filter steps by context and upgrade type
    applicable_steps = [
        step
        for step in steps
        if (_get_context_str(step.context) in (context_str, UpgradeContext.BOTH.value))
        and step.upgrade_type == upgrade_type
    ]

    # Sort by priority (lower numbers first)
    sorted_steps = sorted(applicable_steps, key=lambda s: s.priority)

    result = UpgradeResult(data)
    logger.info(
        "Applying upgrades with rollback in {} context: {} steps to consider",
        context_str,
        len(sorted_steps),
    )

    for step in sorted_steps:
        try:
            upgraded_data, was_applied = apply_upgrade(result.current_data, step)
            if was_applied:
                result.add_step(step.name, upgraded_data)
                logger.info("Applied upgrade step '{}'", step.name)
        except Exception as e:
            logger.error("Upgrade step {} failed: {}", step.name, e)
            if stop_on_error:
                logger.warning("Stopping upgrade process and rolling back due to error in '{}'", step.name)
                result.rollback()
                break
            # Continue with other steps if not stopping on error
            continue

    logger.info("Completed upgrades. Applied: {}", result.applied_steps)
    return result
