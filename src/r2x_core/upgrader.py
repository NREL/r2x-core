"""Base class for data structure upgrade plugins.

Provides a registry system for upgrade steps using a decorator pattern.
Each upgrader subclass maintains its own list of ordered UpgradeStep objects
that transform data from one version to the next.

Usage:

    class MyUpgrader(BaseUpgrader):
        @register_step(name="v1_to_v2")
        def upgrade_to_v2(data):
            # Transform data from v1 to v2
            return transformed_data

    # Or direct registration:
    def upgrade_to_v3(data):
        return data

    MyUpgrader.register_step(upgrade_to_v3, name="v2_to_v3")
    steps = MyUpgrader.list_steps()  # Returns all registered steps

Each step receives data and optional parameters specified during registration,
allowing flexible upgrade workflows.

See Also
--------
:class:`~r2x_core.upgrader_utils.UpgradeStep` : Individual upgrade transformation.
:func:`~r2x_core.upgrader_utils.run_upgrade_step` : Execute individual steps.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from .upgrader_utils import UpgradeStep


class BaseUpgrader:
    """Registry for versioning and upgrade transformations.

    Each subclass maintains its own list of ordered upgrade steps. Use the
    @register_step decorator or register_step() method to add transformations
    that convert data from one version to the next.

    Attributes
    ----------
    steps : ClassVar[list[UpgradeStep]]
        Class-level list of registered upgrade steps for this upgrader.
        Each subclass has its own isolated list via __init_subclass__.

    See Also
    --------
    :meth:`register_step` : Register an upgrade transformation step.
    :meth:`list_steps` : Get all registered steps.
    """

    steps: ClassVar[list[UpgradeStep]] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize a new upgrader subclass with isolated step registry.

        Automatically called when a subclass is created. Ensures each
        subclass has its own steps list, preventing step inheritance.

        Parameters
        ----------
        **kwargs : Any
            Additional keyword arguments passed to super().__init_subclass__().
        """
        cls.steps = []

    @classmethod
    def register_step(cls, func: Callable[..., Any] | None = None, **kwargs: Any) -> Callable[..., Any]:
        """Register an upgrade transformation step.

        Supports both decorator and direct call patterns. Steps are executed
        sequentially in the order registered, each transforming data to the
        next version.

        Parameters
        ----------
        func : Callable | None
            Function to register as a step. If None, acts as a decorator
            factory. If provided, directly registers the function and returns it.
        **kwargs : Any
            Additional parameters:
            - name (str): Override the step name. Defaults to func.__name__.
            - Other kwargs are passed to UpgradeStep for future extensibility.

        Returns
        -------
        Callable
            The input function (or decorator if func is None).

        Examples
        --------
        Using as a decorator (recommended):

        >>> class MyUpgrader(BaseUpgrader):
        ...     @register_step(name="v1_to_v2")
        ...     def upgrade_v1_to_v2(data):
        ...         data['version'] = 2
        ...         return data

        Direct registration:

        >>> def upgrade_v2_to_v3(data):
        ...     data['version'] = 3
        ...     return data
        >>> MyUpgrader.register_step(upgrade_v2_to_v3, name="v2_to_v3")

        See Also
        --------
        :meth:`list_steps` : Get all registered steps.
        :class:`~r2x_core.upgrader_utils.UpgradeStep` : Step definition.
        """

        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            """Register a function as an upgrade step when used as decorator.

            Parameters
            ----------
            f : Callable
                Function to register as an upgrade step.

            Returns
            -------
            Callable
                The original function unchanged (for chaining).
            """
            step_name = kwargs.get("name", f.__name__)
            step = UpgradeStep(name=step_name, func=f, **{k: v for k, v in kwargs.items() if k != "name"})
            cls.steps.append(step)
            return f

        if func is not None:
            # Direct call form, not decorator
            step_name = kwargs.get("name", func.__name__)
            step = UpgradeStep(name=step_name, func=func, **{k: v for k, v in kwargs.items() if k != "name"})
            cls.steps.append(step)
            return func

        return decorator

    @classmethod
    def list_steps(cls) -> list[UpgradeStep]:
        """Get all registered upgrade steps in order.

        Returns
        -------
        list[UpgradeStep]
            Ordered list of upgrade steps registered for this upgrader.
            Empty list if no steps registered. Steps are executed in this order.

        See Also
        --------
        :meth:`register_step` : Register a new upgrade step.
        """
        return cls.steps


# Backward compatibility alias
PluginUpgrader = BaseUpgrader
