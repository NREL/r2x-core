"""Shared context objects for parsers, exporters, and translation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from .store import DataStore
    from .system import System


@dataclass(frozen=True, kw_only=True)
class Context:
    """Generic context with optional config, data store, and metadata."""

    config: Any = None
    data_store: DataStore | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_updates(self: Self, **kwargs: Any) -> Self:
        """Return a new context instance with updated fields."""
        return replace(self, **kwargs)


@dataclass(frozen=True, slots=True)
class ParserContext(Context):
    """Context for parser workflows."""

    system: System | None = None
    skip_validation: bool = False
    auto_add_composed_components: bool = True


@dataclass(frozen=True, slots=True)
class ExporterContext(Context):
    """Context for exporter workflows."""

    system: System | None = None
