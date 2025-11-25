"""Shared context objects for parsers, exporters, and translation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Self, TypeVar

if TYPE_CHECKING:
    from .plugin_config import PluginConfig
    from .rules import Rule
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


ContextT = TypeVar("ContextT", bound="Context", contravariant=True)


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


@dataclass(frozen=True, slots=True, kw_only=True)
class TranslationContext(Context):
    """Immutable context for component transformation."""

    config: PluginConfig
    source_system: System
    target_system: System
    rules: list[Rule]

    def __post_init__(self) -> None:
        """Build internal rule index after initialization and validate entries."""
        rule_index: dict[tuple[str, str, int], Rule] = {}
        for rule in self.rules:
            for source_type in rule.get_source_types():
                for target_type in rule.get_target_types():
                    key = (source_type, target_type, rule.version)
                    if key in rule_index:
                        raise ValueError(
                            f"Duplicate rule key {key}: cannot have multiple rules with the same "
                            f"source_type, target_type, and version"
                        )
                    rule_index[key] = rule

        object.__setattr__(self, "_rule_index", rule_index)

    def get_rule(
        self,
        source_type: str,
        target_type: str,
        version: int | None = None,
    ) -> Rule:
        """Retrieve a transformation rule."""
        if version is None:
            active_versions = getattr(self.config, "active_versions", {})
            version = active_versions.get(source_type, 1)

        assert version is not None
        key: tuple[str, str, int] = (source_type, target_type, version)
        rule_index: dict[tuple[str, str, int], Rule] = object.__getattribute__(self, "_rule_index")
        if key not in rule_index:
            raise KeyError(f"No rule found for {source_type} → {target_type} (v{version})")
        return rule_index[key]

    def list_rules(self) -> list[Rule]:
        """List all available transformation rules."""
        return list(self.rules)

    def list_available_conversions(self) -> dict[str, list[tuple[str, int]]]:
        """List available conversions by source type."""
        conversions: dict[str, list[tuple[str, int]]] = {}
        for rule in self.rules:
            for source_type in rule.get_source_types():
                if source_type not in conversions:
                    conversions[source_type] = []
                for target_type in rule.get_target_types():
                    conversions[source_type].append((target_type, rule.version))
        for targets in conversions.values():
            targets.sort()
        return conversions

    def get_rules_for_source(self, source_type: str) -> list[Rule]:
        """Get all rules for a specific source type."""
        matching = [r for r in self.rules if source_type in r.get_source_types()]
        matching.sort(key=lambda r: (str(r.target_type), r.version))
        return matching

    def get_rules_for_conversion(self, source_type: str, target_type: str) -> list[Rule]:
        """Get all versions of a conversion between two types."""
        matching = [
            r
            for r in self.rules
            if source_type in r.get_source_types() and target_type in r.get_target_types()
        ]
        matching.sort(key=lambda r: r.version)
        return matching
