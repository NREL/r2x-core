"""Translation context and result data structures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .context import Context

if TYPE_CHECKING:
    from . import System
    from .rules import Rule


@dataclass(frozen=True, slots=True)
class TranslationContext(Context):
    """Immutable context for component transformation."""

    source_system: System
    target_system: System
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
        if self.config is None:
            raise ValueError("TranslationContext requires a config instance")

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
