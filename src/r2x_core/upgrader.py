"""Upgrade system for R2X Core."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from .upgrader_utils import UpgradeStep


class BaseUpgrader:
    """Shared base for all plugin upgraders."""

    steps: ClassVar[list[UpgradeStep]] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Isolate steps per subclass."""
        cls.steps = []

    @classmethod
    def register_step(cls, func: Callable[..., Any] | None = None, **kwargs):
        """Register an upgrade step."""

        def decorator(f: Callable[..., Any]):
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
        """Return list of steps."""
        return cls.steps


# Backward compatibility alias
PluginUpgrader = BaseUpgrader
