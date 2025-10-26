"""Upgrade system for R2X Core.

Example usage of :class:`PluginUpgrader`:

Create an upgrader by subclassing PluginUpgrader:

>>> from r2x_core.upgrader import PluginUpgrader, UpgradeType
>>> from r2x_core.result import Ok
>>> class MyUpgrader(PluginUpgrader):
...     pass
>>> @MyUpgrader.register_upgrade_step("2.0.0", UpgradeType.FILE)
... def rename_columns(folder):
...     # Upgrade file operations
...     return folder

Register and use upgrade steps:

>>> upgrader = MyUpgrader(strategy=SemanticVersioningStrategy())
>>> result = upgrader.upgrade_data_files(Path("/data"))

This module provides a two-tier upgrade mechanism for R2X Core plugins:

**FILE**: File operations on raw data before parser initialization (default workflow)
**SYSTEM**: System object modifications for cached systems only
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from .exceptions import UpgradeError, ValidationError
from .result import Err, Ok, Result
from .upgrader_utils import UpgradeStep, UpgradeType, run_datafile_upgrades, run_system_upgrades
from .versioning import VersionDetector

if TYPE_CHECKING:
    from .versioning import VersioningModel


class PluginUpgrader:
    """Base class for plugin data upgraders.

    The :class:`PluginUpgrader` provides a decorator-based upgrade registration system
    for managing data migrations. It supports two upgrade types: FILE (raw data operations)
    and SYSTEM (cached system modifications).

    Parameters
    ----------
    strategy : VersioningModel | None, optional
        Version comparison strategy (semantic, git-based, etc.).
        Default is None.
    steps : list[UpgradeStep] | None, optional
        Pre-defined upgrade steps to register. Default is None.
    version : str | None, optional
        Current data version; auto-detected if version_detector provided.
        Default is None.
    version_detector : VersionDetector | None, optional
        Protocol for detecting version from data folder. Default is None.
    **kwargs : Any
        Additional arguments passed to version_detector.detect_version().

    Attributes
    ----------
    strategy : VersioningModel | None
        The versioning strategy instance.
    version : str | None
        The detected or provided version.
    steps : list[UpgradeStep]
        Registered upgrade steps.

    Methods
    -------
    upgrade_data_files(folder_path, upgrader_context)
        Upgrade data files folder to latest version.
    upgrade_system_data(system_data, upgrader_context)
        Upgrade serialized system data.
    registered_steps()
        Return all globally registered upgrade steps.
    register_upgrade_step(target_version, upgrade_type, priority)
        Decorator to register an upgrade step.

    See Also
    --------
    :class:`UpgradeStep` : Individual upgrade step definition.
    :class:`UpgradeType` : Type of upgrade (FILE or SYSTEM).
    :class:`VersioningModel` : Version comparison strategy.

    Examples
    --------
    Create a custom upgrader with FILE upgrade steps:

    >>> from r2x_core.upgrader import PluginUpgrader, UpgradeType
    >>> from r2x_core.versioning import SemanticVersioningStrategy
    >>> class MyUpgrader(PluginUpgrader):
    ...     pass
    >>> @MyUpgrader.register_upgrade_step("2.0.0", UpgradeType.FILE, priority=1)
    ... def rename_columns(folder, upgrader_context=None):
    ...     # Rename columns in data files
    ...     old = folder / "old_names.csv"
    ...     if old.exists():
    ...         old.rename(folder / "new_names.csv")
    ...     return folder
    >>> upgrader = MyUpgrader(strategy=SemanticVersioningStrategy())
    >>> result = upgrader.upgrade_data_files(Path("/data"))

    Notes
    -----
    Each subclass maintains its own isolated registry of upgrade steps through
    the ``__init_subclass__`` mechanism. This ensures that upgrade steps registered
    on one plugin class do not affect other plugins.

    The upgrade workflow can operate on two levels:

    - **FILE upgrades**: Run on raw data files before parser initialization
    - **SYSTEM upgrades**: Run on cached/serialized system objects
    """

    _registered_steps: ClassVar[list[UpgradeStep]] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Ensure each subclass has its own upgrade step registry."""
        super().__init_subclass__(**kwargs)
        cls._registered_steps = []  # isolate registry per plugin
        assert cls._registered_steps is not PluginUpgrader._registered_steps, (
            f"{cls.__name__} should have its own registry"
        )

    def __init__(
        self,
        folder_path: Path | str | None = None,
        strategy: VersioningModel | None = None,
        steps: list[UpgradeStep] | None = None,
        version: str | None = None,
        version_detector: VersionDetector | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the upgrader with versioning strategy and steps.

        Parameters
        ----------
        strategy : VersioningModel | None, optional
            Version comparison strategy. Default is None.
        steps : list[UpgradeStep] | None, optional
            Pre-defined upgrade steps to register. Default is None.
        version : str | None, optional
            Current data version. Default is None.
        version_detector : VersionDetector | None, optional
            Version detection protocol. Default is None.
        **kwargs : Any
            Additional keyword arguments for version_detector.
        """
        if not version and version_detector:
            if not folder_path:
                msg = "If not passing a version, you need to pass a folder_pass to detect the version."
                raise ValidationError(msg)
            folder_path = Path(folder_path)
            if not folder_path.exists():
                raise FileExistsError(f"{folder_path} does not exists.")
            # version_detector_kwargs = filter_valid_kwargs(version_detector.detect_version, kwargs)
            version = version_detector.detect_version(folder_path=folder_path)
        self._version = version
        self._strategy = strategy

        if steps:
            type(self)._registered_steps.extend(steps)

    @property
    def strategy(self) -> VersioningModel | None:
        """Return the :class:`VersioningModel` strategy instance."""
        return self._strategy

    @property
    def steps(self) -> list[UpgradeStep]:
        """Return all registered :class:`UpgradeStep` instances."""
        return type(self)._registered_steps

    @property
    def version(self) -> str | None:
        """Return the current detected or provided version."""
        return self._version

    def upgrade_data_files(
        self, folder_path: Path, upgrader_context: dict[str, Any] | None = None
    ) -> Result[None, UpgradeError]:
        """Upgrade data files folder to latest version.

        This is the main entry point for upgrading raw data files. It executes
        all registered FILE upgrade steps in priority order.

        Parameters
        ----------
        folder_path : Path | str
            Data folder to upgrade.
        upgrader_context : dict[str, Any] | None, optional
            Context dictionary passed to upgrade steps. Default is None.

        Returns
        -------
        Result[None, UpgradeError]
            ``Ok(None)`` if upgrade succeeds, ``Err(UpgradeError(...))`` on failure.

        Raises
        ------
        UpgradeError
            If any upgrade step fails.
        """
        if isinstance(folder_path, str):
            folder_path = Path(folder_path)

        file_steps = [step for step in self.steps if step.upgrade_type == UpgradeType.FILE]

        result = run_datafile_upgrades(
            file_steps,
            folder_path,
            self.version,
            upgrader_context=upgrader_context,
            strategy=self._strategy,
        )

        match result:
            case Ok():
                return Ok()
            case Err(error):
                raise UpgradeError(error)
            case _:
                return Ok()

    def upgrade_system_data(
        self, system_data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> Result[None, UpgradeError]:
        """Upgrade serialized system data.

        This is the main entry point for upgrading cached/serialized system objects.
        It executes all registered SYSTEM upgrade steps in priority order.

        Parameters
        ----------
        system_data : dict[str, Any]
            System data to upgrade (usually deserialized from JSON/cache).
        upgrader_context : dict[str, Any] | None, optional
            Context dictionary passed to upgrade steps. Default is None.

        Returns
        -------
        Result[None, UpgradeError]
            ``Ok(None)`` if upgrade succeeds, ``Err(UpgradeError(...))`` on failure.

        Raises
        ------
        UpgradeError
            If any upgrade step fails.
        """
        system_steps = [step for step in self.steps if step.upgrade_type == UpgradeType.SYSTEM]

        result = run_system_upgrades(
            system_steps,
            system_data,
            self.version,
            upgrader_context=upgrader_context,
            strategy=self.strategy,
        )

        match result:
            case Ok():
                return Ok()
            case Err(error):
                raise UpgradeError(error)
            case _:
                return Ok()

    @classmethod
    def registered_steps(cls) -> list[UpgradeStep]:
        """Return all globally registered upgrade steps for this upgrader class.

        Returns
        -------
        list[UpgradeStep]
            List of registered upgrade steps.
        """
        return cls._registered_steps

    @classmethod
    def register_upgrade_step(
        cls,
        target_version: str,
        upgrade_type: UpgradeType,
        priority: int = 100,
    ) -> Callable[[Callable[[Path], Path]], Callable[[Path], Path]]:
        """Register an upgrade step via decorator.

        Can be used from any module to register steps to this upgrader class.

        Parameters
        ----------
        target_version : str
            Target version for this upgrade.
        upgrade_type : UpgradeType
            Type of upgrade (FILE or SYSTEM).
        priority : int, optional
            Execution priority (lower runs first). Default is 100.

        Returns
        -------
        Callable
            Decorator function.

        Examples
        --------
        >>> @MyUpgrader.register_upgrade_step("2.0.0", UpgradeType.FILE, priority=1)
        ... def rename_columns(folder, upgrader_context=None):
        ...     # Perform upgrade operations
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
            if "_registered_steps" not in cls.__dict__:
                cls._registered_steps = []
            step = UpgradeStep(
                name=func.__name__,
                func=func,
                target_version=target_version,
                upgrade_type=upgrade_type,
                priority=priority,
            )
            cls._registered_steps.append(step)
            return func

        return decorator
