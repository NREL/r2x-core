"""Execute a set of rules for a given translation context."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast
from uuid import uuid4

from infrasys import Component, SupplementalAttribute
from loguru import logger
from rust_ok import Err, Ok, Result

from .plugin_context import PluginContext
from .result import RuleApplicationStats, RuleResult, TranslationResult
from .rules import Rule
from .time_series import transfer_time_series_metadata
from .utils import (
    _build_target_fields,
    _create_target_component,
    _evaluate_rule_filter,
    _iter_system_components,
    _resolve_component_type,
    _sort_rules_by_dependencies,
)


def apply_rules_to_context(context: PluginContext) -> TranslationResult:
    """Apply all transformation rules defined in a PluginContext.

    Parameters
    ----------
    context : PluginContext
        The plugin context containing rules and systems

    Returns
    -------
    TranslationResult
        Rich result object with detailed statistics and per-rule results

    Raises
    ------
    ValueError
        If the context has no rules defined or if circular dependencies are detected
    """
    if not context.rules:
        raise ValueError(f"{type(context).__name__} has no rules. Use context.list_rules().")

    sorted_rules = _sort_rules_by_dependencies(context.list_rules()).unwrap_or_raise(exc_type=ValueError)

    rule_results: list[RuleResult] = []
    total_converted = 0
    successful_rules = 0
    failed_rules = 0

    for rule in sorted_rules:
        logger.debug("Applying rule: {}", rule)
        result = apply_single_rule(rule, context=context)

        match result:
            case Ok(stats):
                rule_results.append(
                    RuleResult(
                        rule=rule,
                        converted=stats.converted,
                        skipped=stats.skipped,
                        success=True,
                        error=None,
                    )
                )
                total_converted += stats.converted
                successful_rules += 1
            case Err(_):
                error = str(result.err())
                logger.error("Rule {} failed: {}", rule, error)
                rule_results.append(
                    RuleResult(
                        rule=rule,
                        converted=0,
                        skipped=0,
                        success=False,
                        error=error,
                    )
                )
                failed_rules += 1

    ts_result = transfer_time_series_metadata(context)

    return TranslationResult(
        total_rules=len(context.rules),
        successful_rules=successful_rules,
        failed_rules=failed_rules,
        total_converted=total_converted,
        rule_results=rule_results,
        time_series_transferred=ts_result.transferred,
        time_series_updated=ts_result.updated,
    )


def apply_single_rule(rule: Rule, *, context: PluginContext) -> Result[RuleApplicationStats, ValueError]:
    """Apply one transformation rule across matching components.

    Handles both single and multiple source/target types. Fails fast on any error.

    Parameters
    ----------
    rule : Rule
        The transformation rule to apply
    context : PluginContext
        The plugin context containing systems and configuration

    Returns
    -------
    Result[RuleApplicationStats, ValueError]
        Ok with stats if all succeed, or Err with first error encountered

    """
    converted = 0
    should_regenerate_uuid = len(rule.get_target_types()) > 1

    read_system = context.target_system if rule.system == "target" else context.source_system
    if read_system is None:
        return Err(ValueError(f"System '{rule.system}' is not set in context"))
    assert read_system is not None  # Type guard for type checker

    for source_type in rule.get_source_types():
        # Resolve source class, converting TypeError to ValueError
        source_class_result = _resolve_component_type(source_type, context=context).map_err(
            lambda e, st=source_type: ValueError(f"Failed to resolve source type '{st}': {e}")
        )

        # Skip this source type if resolution failed, but return errors from conversions
        if source_class_result.is_err():
            logger.error("Source type resolution error: {}", source_class_result.err())
            # Return the error properly typed
            return source_class_result.map(lambda _: RuleApplicationStats(converted=0, skipped=0))

        # Extract resolved source class (safe because is_ok() check passed)
        source_class = cast(type[Component], source_class_result.ok())

        filter_func: Callable[[Any], bool] | None = None
        if rule.filter is not None:
            rule_filter = rule.filter
            filter_func = lambda comp: _evaluate_rule_filter(comp, rule_filter=rule_filter)  # noqa: E731, B023

        for src_component in _iter_system_components(
            read_system,
            class_type=source_class,
            filter_func=filter_func,
        ):
            for target_type in rule.get_target_types():
                # Chain conversions: convert then attach using and_then
                conversion_result = _convert_component(
                    rule, src_component, target_type, context, should_regenerate_uuid
                ).and_then(lambda component, sc=src_component: _attach_component(component, sc, context))

                # Return early on conversion failure
                if conversion_result.is_err():
                    return conversion_result.map(lambda _: RuleApplicationStats(converted=0, skipped=0))

                converted += 1

    logger.debug("Rule {}: {} converted", rule, converted)
    return Ok(RuleApplicationStats(converted=converted, skipped=0))


def _convert_component(
    rule: Rule,
    source_component: Any,
    target_type: str,
    context: PluginContext,
    regenerate_uuid: bool,
) -> Result[Any, ValueError]:
    """Convert a single source component to a target type.

    This function creates the target component but does not add it to the system.
    The caller is responsible for attaching the component using _attach_component().

    Parameters
    ----------
    rule : Rule
        The transformation rule
    source_component : Any
        The source component to convert
    target_type : str
        The target component type name
    context : PluginContext
        The plugin context
    regenerate_uuid : bool
        Whether to generate a new UUID (for multiple targets)

    Returns
    -------
    Result[Any, ValueError]
        Ok with the created component if conversion succeeds, Err otherwise
    """
    # Resolve target class, converting TypeError to ValueError
    target_class_result = _resolve_component_type(target_type, context=context).map_err(
        lambda e: ValueError(f"Failed to resolve target type '{target_type}': {e}")
    )

    # Build fields and chain with target class resolution
    def build_and_create(target_class: type) -> Result[Any, ValueError]:
        """Build fields and create the target component."""
        fields_result = _build_target_fields(source_component, rule=rule, context=context).map_err(
            lambda e: ValueError(f"Failed to build fields for {source_component.label}: {e}")
        )

        # Use and_then to chain field building with component creation
        def create_component(kwargs: dict[str, Any]) -> Result[Any, ValueError]:
            """Create target component with optional UUID regeneration."""
            if regenerate_uuid and "uuid" in kwargs:
                kwargs = dict(kwargs)
                kwargs["uuid"] = str(uuid4())

            return Ok(_create_target_component(target_class, kwargs=kwargs))

        return fields_result.and_then(create_component)

    # Chain target class resolution with field building and component creation
    return target_class_result.and_then(build_and_create)


def _is_supplemental_attribute(component: Component) -> bool:
    """Check if a component is a supplemental attribute.

    Parameters
    ----------
    component : Any
        The component to check

    Returns
    -------
    bool
        True if the component is a supplemental attribute, False otherwise
    """
    return isinstance(component, SupplementalAttribute)


def _attach_component(
    component: Any,
    source_component: Any,
    context: PluginContext,
) -> Result[None, ValueError]:
    """Attach a component to the target system.

    For regular components, adds them directly to the system.
    For supplemental attributes, finds the corresponding target component
    and attaches the supplemental attribute to it.

    Parameters
    ----------
    component : Any
        The component or supplemental attribute to attach
    source_component : Any
        The source component that was converted
    context : PluginContext
        The plugin context

    Returns
    -------
    Result[None, ValueError]
        Ok if attachment succeeds, Err otherwise
    """
    if context.target_system is None:
        return Err(ValueError("target_system must be set in context"))
    if not _is_supplemental_attribute(component):
        context.target_system.add_component(component)
        return Ok(None)

    # Find the target component that corresponds to the source component
    # We look for a component with the same UUID in the target system
    try:
        target_component = context.target_system.get_component_by_uuid(source_component.uuid)
    except Exception as e:
        logger.error(
            "Failed to find target component with UUID {} for supplemental attribute attachment: {}",
            source_component.uuid,
            e,
        )
        return Err(
            ValueError(
                f"Cannot attach supplemental attribute: target component with UUID "
                f"{source_component.uuid} not found in target system"
            )
        )

    context.target_system.add_supplemental_attribute(target_component, component)
    logger.debug(
        "Attached supplemental attribute {} to component {}", type(component).__name__, target_component.label
    )
    return Ok(None)
