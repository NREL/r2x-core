"""Execute a set of rules for a given translation context."""

from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from infrasys import Component, SupplementalAttribute
from loguru import logger
from rust_ok import Err, Ok, Result

from .context import TranslationContext
from .result import RuleResult, TranslationResult
from .rules import Rule
from .rules_utils import (
    _build_target_fields,
    _create_target_component,
    _evaluate_rule_filter,
    _resolve_component_type,
    _sort_rules_by_dependencies,
)
from .system_utils import _iter_system_components
from .time_series import transfer_time_series_metadata


def apply_rules_to_context(context: TranslationContext) -> TranslationResult:
    """Apply all transformation rules defined in a TranslationContext.

    Parameters
    ----------
    context : TranslationContext
        The translation context containing rules and systems

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

    sorted_rules_result = _sort_rules_by_dependencies(context.list_rules())
    if sorted_rules_result.is_err():
        raise ValueError(str(sorted_rules_result.err()))

    sorted_rules = sorted_rules_result.unwrap()

    rule_results: list[RuleResult] = []
    total_converted = 0
    successful_rules = 0
    failed_rules = 0

    for rule in sorted_rules:
        logger.debug("Applying rule: {}", rule)
        result = apply_single_rule(rule, context)

        match result:
            case Ok((converted, skipped)):
                rule_results.append(
                    RuleResult(
                        rule=rule,
                        converted=converted,
                        skipped=skipped,
                        success=True,
                        error=None,
                    )
                )
                total_converted += converted
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


def apply_single_rule(rule: Rule, context: TranslationContext) -> Result[tuple[int, int], ValueError]:
    """Apply one transformation rule across matching components.

    Handles both single and multiple source/target types. Fails fast on any error.

    Parameters
    ----------
    rule : Rule
        The transformation rule to apply
    context : TranslationContext
        The translation context containing systems and configuration

    Returns
    -------
    Result[tuple[int, int], ValueError]
        Ok with (converted, 0) if all succeed, or Err with first error encountered

    """
    converted = 0
    should_regenerate_uuid = len(rule.get_target_types()) > 1

    read_system = context.target_system if rule.system == "target" else context.source_system

    for source_type in rule.get_source_types():
        source_class_result = _resolve_component_type(source_type, context)
        if source_class_result.is_err():
            logger.error("Failed to resolve source type '{}': {}", source_type, source_class_result.err())
            return Err(ValueError(str(source_class_result.err())))

        source_class = source_class_result.unwrap()
        filter_func = None
        if rule.filter:
            filter_func = lambda comp: _evaluate_rule_filter(rule.filter, comp)  # noqa: E731

        for src_component in _iter_system_components(read_system, source_class, filter_func=filter_func):  # type: Any
            source_component = cast(Any, src_component)
            for target_type in rule.get_target_types():
                result = _convert_component(
                    rule,
                    source_component,
                    target_type,
                    context,
                    should_regenerate_uuid,
                )
                if result.is_err():
                    return Err(ValueError(str(result.err())))

                component = result.unwrap()
                attach_result = _attach_component(component, source_component, context)
                if attach_result.is_err():
                    return Err(ValueError(str(attach_result.err())))

                converted += 1

    logger.debug("Rule {}: {} converted", rule, converted)
    return Ok((converted, 0))


def _convert_component(
    rule: Rule,
    source_component: Any,
    target_type: str,
    context: TranslationContext,
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
    context : TranslationContext
        The translation context
    regenerate_uuid : bool
        Whether to generate a new UUID (for multiple targets)

    Returns
    -------
    Result[Any, ValueError]
        Ok with the created component if conversion succeeds, Err otherwise
    """
    target_class_result = _resolve_component_type(target_type, context)
    if target_class_result.is_err():
        logger.error("Failed to resolve target type '{}': {}", target_type, target_class_result.err())
        return Err(ValueError(str(target_class_result.err())))

    target_class = target_class_result.unwrap()

    fields_result = _build_target_fields(rule, source_component, context)
    if fields_result.is_err():
        logger.error(
            "Failed to build fields for {} -> {}: {}",
            source_component.label,
            target_type,
            fields_result.err(),
        )
        return Err(ValueError(str(fields_result.err())))

    kwargs = fields_result.unwrap()

    if regenerate_uuid and "uuid" in kwargs:
        kwargs = dict(kwargs)
        kwargs["uuid"] = str(uuid4())

    target = _create_target_component(target_class, kwargs)
    return Ok(target)


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
    context: TranslationContext,
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
    context : TranslationContext
        The translation context

    Returns
    -------
    Result[None, ValueError]
        Ok if attachment succeeds, Err otherwise
    """
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
