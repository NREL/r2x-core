"""Execute a set of rules for a given translation context."""

from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from loguru import logger

from . import Err, Ok, Result
from .rules_utils import (
    _build_target_fields,
    _create_target_component,
    _resolve_component_type,
)
from .system_utils import _iter_system_components
from .time_series import transfer_time_series_metadata
from .translation_rules import Rule, RuleResult, TranslationContext, TranslationResult


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
        If the context has no rules defined
    """
    if not context.rules:
        raise ValueError(f"{type(context).__name__} has no rules. Use context.list_rules().")

    rule_results: list[RuleResult] = []
    total_converted = 0
    successful_rules = 0
    failed_rules = 0

    for rule in context.list_rules():
        logger.debug("Applying rule: {}", rule)
        result = apply_single_rule(rule, context)

        if result.is_ok():
            converted, skipped = result.unwrap()
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
        else:
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

    # Transfer time series metadata
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

    for source_type in rule.get_source_types():
        source_class_result = _resolve_component_type(source_type, context)
        if source_class_result.is_err():
            logger.error("Failed to resolve source type '{}': {}", source_type, source_class_result.err())
            return Err(ValueError(str(source_class_result.err())))

        source_class = source_class_result.unwrap()

        for src_component in _iter_system_components(context.source_system, source_class):  # type: Any
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
                converted += 1

    logger.debug("Rule {}: {} converted", rule, converted)
    return Ok((converted, 0))


def _convert_component(
    rule: Rule,
    source_component: Any,
    target_type: str,
    context: TranslationContext,
    regenerate_uuid: bool,
) -> Result[None, ValueError]:
    """Convert a single source component to a target type.

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
    Result[None, ValueError]
        Ok if conversion succeeds, Err otherwise
    """
    target_class_result = _resolve_component_type(target_type, context)
    if target_class_result.is_err():
        logger.error("Failed to resolve target type '{}': {}", target_type, target_class_result.err())
        return Err(ValueError(str(target_class_result.err())))

    target_class = target_class_result.unwrap()

    fields_result = _build_target_fields(rule, source_component, context)
    if fields_result.is_err():
        src_name = getattr(
            source_component, "label", getattr(source_component, "name", str(source_component))
        )
        logger.error("Failed to build fields for {} -> {}: {}", src_name, target_type, fields_result.err())
        return Err(ValueError(str(fields_result.err())))

    kwargs = fields_result.unwrap()

    if regenerate_uuid and "uuid" in kwargs:
        kwargs = dict(kwargs)
        kwargs["uuid"] = str(uuid4())

    target = _create_target_component(target_class, kwargs)
    context.target_system.add_component(target)
    return Ok(None)
