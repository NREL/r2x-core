"""System helpers."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from infrasys import Component

    from . import System

ComponentT = TypeVar("ComponentT", bound="Component")


def _iter_system_components(
    system: System,
    class_type: type[ComponentT],
    filter_func: Callable[[ComponentT], bool] | None = None,
) -> Generator[ComponentT, None, None]:
    """Yield all source components of a specific type."""
    yield from system.get_components(class_type, filter_func=filter_func)
