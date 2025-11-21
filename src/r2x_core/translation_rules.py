"""Data models for the functional converter architecture.

This module defines the core data structures for transformation rules and
translation context, following a declarative, schema-driven approach with
clear separation of concerns.

Design Principles:
- TransformationRule: Declarative descriptions of component mappings
- TranslationContext: Static configuration holder (no mutable state)
- Getters: Responsible for all field extraction, computation, and formatting
- Rule metadata is single-source-of-truth (source_type, target_type, version)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from . import System
    from .plugin_config import PluginConfig


class RuleFilter(BaseModel):
    """Declarative predicate for selecting source components."""

    field: str | None = None
    op: Literal["eq", "neq", "in", "not_in", "geq"] | None = None
    values: list[Any] | None = None
    any_of: list[RuleFilter] | None = None
    all_of: list[RuleFilter] | None = None
    casefold: bool = True
    on_missing: Literal["include", "exclude"] = "exclude"

    @model_validator(mode="after")
    def _validate_structure(self) -> RuleFilter:
        """Ensure the filter is either a leaf or a composition."""
        is_leaf = self.field is not None or self.op is not None or self.values is not None
        has_children = bool(self.any_of) or bool(self.all_of)

        if is_leaf and has_children:
            raise ValueError("RuleFilter cannot mix field/op/values with any_of/all_of")
        if not is_leaf and not has_children:
            raise ValueError("RuleFilter requires field/op/values or any_of/all_of")
        if self.any_of and self.all_of:
            raise ValueError("RuleFilter cannot set both any_of and all_of")

        if is_leaf:
            if not self.field:
                raise ValueError("RuleFilter.field is required for leaf filters")
            if self.op is None:
                raise ValueError("RuleFilter.op is required for leaf filters")
            if not self.values:
                raise ValueError("RuleFilter.values must contain at least one value")
            if self.op == "geq" and len(self.values) != 1:
                raise ValueError("RuleFilter.geq expects exactly one comparison value")

        return self

    def matches(self, component: Any) -> bool:
        """Evaluate this filter against a component instance."""
        from .rules_utils import _evaluate_rule_filter

        return _evaluate_rule_filter(self, component)


RuleFilter.model_rebuild()


@dataclass(frozen=True, slots=True)
class Rule:
    """Declarative rule for converting one component type to another.

    Describes how to transform a Sienna component into a PLEXOS component,
    including field mappings, type conversions, and custom extraction logic.

    The rule's metadata (source_type, target_type, version) is the single
    source of truth for rule identification. Rules are stored in a list
    with automatic indexing for fast lookups.

    Attributes
    ----------
    source_type : str | list[str]
        Name of the source component type (e.g., "ACBus") or list of source types.
        When a list is provided, the same transformation is applied to all source types.
        Cannot be a list if target_type is also a list.
    target_type : str | list[str]
        Name of the target component type (e.g., "PLEXOSNode") or list of target types.
        When a list is provided, the source component is split into multiple targets.
        Cannot be a list if source_type is also a list.
    version : int
        Version of this rule for tracking changes and revisions.
        Users can have multiple versions of the same source→target conversion
        and select which version(s) to use via config.active_versions.
    field_map : dict[str, str | list[str]]
        Mapping from target fields to source fields.
        - Single field: "target_field": "source_field"
        - Multi-field: "target_field": ["source_field1", "source_field2"]
        Multi-field mappings require a getter function.
    getters : dict[str, Callable]
        Functions for extracting/computing multi-field source values.
        Key is the target field name, value is the getter function.
        Getters should return the final value (float, dict, or PLEXOSPropertyValue),
        handling any necessary scaling, aggregation, unit conversion, or formatting.
        Signature: getter(ctx: TranslationContext, component: Any) -> Any
    defaults : dict[str, Any]
        Default values for target fields if source is None/missing.
        Key is the target field name, value is the default.
    system : Literal["source", "target"]
        Which system to read components from. Defaults to "source".
        When set to "target", the rule reads from target_system instead of source_system.
        Useful for creating relationship components that link previously created components.
    name : str | None
        Optional identifier for this rule. Used for dependency tracking via depends_on.
    depends_on : list[str] | None
        Optional list of rule names that must execute before this rule.
        Used to enforce ordering when rules have dependencies.
    """

    source_type: str | list[str]
    target_type: str | list[str]
    version: int
    field_map: dict[str, str | list[str]] = field(default_factory=dict)
    getters: dict[str, Callable[[TranslationContext, Any], Any] | str] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    filter: RuleFilter | None = field(default=None)
    system: Literal["source", "target"] = "source"
    name: str | None = None
    depends_on: list[str] | None = None

    def __str__(self) -> str:
        """Represent string."""
        return f"{self.source_type}->{self.target_type}(v{self.version})"

    def __post_init__(self) -> Any:
        """Validate init."""
        # Validate that we don't have both multiple sources and multiple targets
        if self.has_multiple_sources() and self.has_multiple_targets():
            raise NotImplementedError(
                f"Rule cannot have both multiple sources and multiple targets. "
                f"source_type={self.source_type}, target_type={self.target_type}"
            )

        # Validate multi-field mappings have getters
        for target_field, source_fields in self.field_map.items():
            if isinstance(source_fields, list) and target_field not in self.getters:
                msg = f"Multi-field mapping for '{target_field}' requires a getter function"
                raise ValueError(msg)
        if self.filter is not None and not isinstance(self.filter, RuleFilter):
            raise TypeError(f"Rule.filter must be a RuleFilter, not {type(self.filter).__name__}")

    def __hash__(self) -> int:
        """Hash based on rule's unique identifier.

        Rules are uniquely identified by (source_type, target_type, version).
        This allows rules to be used in sets and as dict keys if needed.

        Notes
        -----
        For lists, we convert to tuples for hashing.
        """
        source_key = tuple(self.source_type) if isinstance(self.source_type, list) else self.source_type
        target_key = tuple(self.target_type) if isinstance(self.target_type, list) else self.target_type
        return hash((source_key, target_key, self.version))

    def __eq__(self, other: object) -> bool:
        """Equality based on rule's unique identifier.

        Two rules are equal if they have the same source_type, target_type,
        and version. Other attributes are not considered for equality since
        the metadata uniquely identifies the rule.

        Notes
        -----
        Handles comparison of both string and list types.
        """
        if not isinstance(other, Rule):
            return NotImplemented
        return (
            self.source_type == other.source_type
            and self.target_type == other.target_type
            and self.version == other.version
        )

    def has_multiple_sources(self) -> bool:
        """Check if rule applies to multiple source types.

        Returns
        -------
        bool
            True if source_type is a list, False otherwise.
        """
        return isinstance(self.source_type, list)

    def has_multiple_targets(self) -> bool:
        """Check if rule creates multiple target types.

        Returns
        -------
        bool
            True if target_type is a list, False otherwise.
        """
        return isinstance(self.target_type, list)

    def get_source_types(self) -> list[str]:
        """Return source types as list.

        Returns
        -------
        list[str]
            List of source type names. If source_type is a string,
            returns a single-element list.
        """
        return self.source_type if isinstance(self.source_type, list) else [self.source_type]

    def get_target_types(self) -> list[str]:
        """Return target types as list.

        Returns
        -------
        list[str]
            List of target type names. If target_type is a string,
            returns a single-element list.
        """
        return self.target_type if isinstance(self.target_type, list) else [self.target_type]

    @classmethod
    def from_records(cls, records: list[dict[str, Any]]) -> list[Rule]:
        """Create rules from json objects."""
        from .getters import _preprocess_rule_getters

        rules_list = []
        for rule in records:
            if getters := rule.get("getters"):
                rule["getters"] = _preprocess_rule_getters(getters).unwrap_or_raise()
            if "filter" in rule:
                rule["filter"] = (
                    RuleFilter.model_validate(rule["filter"]) if rule["filter"] is not None else None
                )
            rules_list.append(cls(**rule))
        return rules_list


@dataclass(frozen=True)
class TranslationContext:
    """Immutable context for component transformation."""

    source_system: System
    target_system: System
    config: PluginConfig
    rules: list[Rule]

    def __post_init__(self) -> None:
        """Build internal index after initialization and validate rules.

        Raises
        ------
        ValueError
            If rules contain duplicate (source_type, target_type, version)
            combinations.

        Notes
        -----
        For rules with multiple sources or targets, creates index entries
        for each combination to enable efficient lookups.
        """
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
        """Retrieve a transformation rule.

        Parameters
        ----------
        source_type : str
            Name of source component type
        target_type : str
            Name of target component type
        version : int | None, default=None
            Specific version to retrieve. If None, uses active version from
            config.active_versions. If no active version is configured,
            defaults to version 1.

        Returns
        -------
        Rule
            The matching transformation rule

        Raises
        ------
        KeyError
            If no matching rule is found for the given source_type,
            target_type, and version combination.

        Examples
        --------
        Get the active version for a source type (from config):
        >>> rule = context.get_rule("Bus", "Node")

        Get a specific version explicitly:
        >>> rule = context.get_rule("Bus", "Node", version=1)

        Get version when multiple conversions exist for same source:
        >>> rule = context.get_rule("Bus", "PLEXOSNode", version=2)
        """
        if version is None:
            active_versions = getattr(self.config, "active_versions", {})
            version = active_versions.get(source_type, 1)

        # At this point, version is guaranteed to be int
        assert version is not None, "version should be set by now"
        key: tuple[str, str, int] = (source_type, target_type, version)
        rule_index: dict[tuple[str, str, int], Rule] = object.__getattribute__(self, "_rule_index")
        if key not in rule_index:
            raise KeyError(f"No rule found for {source_type} → {target_type} (v{version})")
        return rule_index[key]

    def list_rules(self) -> list[Rule]:
        """List all available transformation rules.

        Returns all rules in the context. Rules are returned in the order
        they were provided during initialization.

        Returns
        -------
        list[Rule]
            All transformation rules in the context

        Examples
        --------
        Get all rules:
        >>> all_rules = context.list_rules()
        >>> print(f"Total rules: {len(all_rules)}")

        Filter rules for a specific source type:
        >>> bus_rules = [r for r in context.list_rules() if r.source_type == "Bus"]
        """
        return list(self.rules)

    def list_available_conversions(self) -> dict[str, list[tuple[str, int]]]:
        """List available conversions by source type.

        Returns a mapping showing what target types and versions are
        available for each source type. Useful for understanding what
        conversions the system supports.

        Returns
        -------
        dict[str, list[tuple[str, int]]]
            Mapping of source_type → [(target_type, version), ...]
            sorted by target_type then version within each source type.

        Examples
        --------
        Get all available conversions:
        >>> conversions = context.list_available_conversions()
        >>> for source, targets in conversions.items():
        ...     print(f"{source} can convert to: {targets}")

        Check if a specific conversion exists:
        >>> conversions = context.list_available_conversions()
        >>> ("Node", 1) in conversions.get("Bus", [])
        True
        """
        conversions: dict[str, list[tuple[str, int]]] = {}
        for rule in self.rules:
            # Handle both single and multiple source types
            for source_type in rule.get_source_types():
                if source_type not in conversions:
                    conversions[source_type] = []
                # Handle both single and multiple target types
                for target_type in rule.get_target_types():
                    conversions[source_type].append((target_type, rule.version))

        # Sort target types and versions for consistent output
        for targets in conversions.values():
            targets.sort()

        return conversions

    def get_rules_for_source(self, source_type: str) -> list[Rule]:
        """Get all rules for a specific source type.

        Returns all rules where the source_type matches, including all
        versions and target types. Useful for discovering what conversions
        are available for a component type.

        Parameters
        ----------
        source_type : str
            Name of source component type

        Returns
        -------
        list[Rule]
            Rules matching the source type, sorted by target_type and version

        Examples
        --------
        Get all Bus conversion rules:
        >>> bus_rules = context.get_rules_for_source("Bus")
        >>> for rule in bus_rules:
        ...     print(f"Bus → {rule.target_type} (v{rule.version})")
        """
        # Match rules where source_type is either the string or in the list
        matching = [r for r in self.rules if source_type in r.get_source_types()]
        # Sort for consistent output
        matching.sort(key=lambda r: (str(r.target_type), r.version))
        return matching

    def get_rules_for_conversion(self, source_type: str, target_type: str) -> list[Rule]:
        """Get all versions of a conversion between two types.

        Returns all rules for the given source→target pair, sorted by
        version. Useful for discovering what versions are available or
        for implementing version selection logic.

        Parameters
        ----------
        source_type : str
            Name of source component type
        target_type : str
            Name of target component type

        Returns
        -------
        list[Rule]
            Rules matching the conversion, sorted by version.
            Empty list if no rules exist for this conversion.

        Examples
        --------
        Get all versions of Bus → Node conversion:
        >>> versions = context.get_rules_for_conversion("Bus", "Node")
        >>> print(f"Available versions: {[r.version for r in versions]}")

        Check if conversion exists:
        >>> if context.get_rules_for_conversion("Bus", "Node"):
        ...     print("Bus to Node conversion is supported")
        """
        # Match rules where both source and target types match
        matching = [
            r
            for r in self.rules
            if source_type in r.get_source_types() and target_type in r.get_target_types()
        ]
        matching.sort(key=lambda r: r.version)
        return matching


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Result of applying a single transformation rule.

    Attributes
    ----------
    rule : Rule
        The rule that was executed (stringified only when displaying summaries)
    converted : int
        Number of components successfully converted
    skipped : int
        Number of components skipped (always 0 with fail-fast)
    success : bool
        Whether the rule executed successfully
    error : str | None
        Error message if rule failed, None otherwise
    """

    rule: Rule
    converted: int
    skipped: int
    success: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """Rich result of translating a complete system.

    Provides detailed statistics and reporting for the translation process.

    Attributes
    ----------
    total_rules : int
        Total number of rules attempted
    successful_rules : int
        Number of rules that completed successfully
    failed_rules : int
        Number of rules that failed
    total_converted : int
        Total number of components converted across all rules
    rule_results : list[RuleResult]
        Detailed results for each rule
    time_series_transferred : int
        Number of time series metadata transferred
    time_series_updated : int
        Number of time series metadata updated
    """

    total_rules: int
    successful_rules: int
    failed_rules: int
    total_converted: int
    rule_results: list[RuleResult]
    time_series_transferred: int = 0
    time_series_updated: int = 0

    @property
    def success(self) -> bool:
        """Check if translation was completely successful."""
        return self.failed_rules == 0

    def summary(self) -> None:
        """Display a rich-formatted table of rule results to the console.

        Uses the rich library to create a beautiful, color-coded table
        showing per-rule conversion results.
        """
        from rich.console import Console
        from rich.table import Table

        console = Console()

        if self.rule_results:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Status", justify="center", style="white", width=6)
            table.add_column("Rule", style="cyan")
            table.add_column("Converted", justify="right", style="yellow")
            table.add_column("Details", style="white")

            for result in self.rule_results:
                status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
                converted = str(result.converted) if result.converted > 0 else "[dim]0[/dim]"
                details = "[dim]success[/dim]" if result.success else f"[red]{result.error}[/red]"

                table.add_row(status, str(result.rule), converted, details)

            console.print(table)
