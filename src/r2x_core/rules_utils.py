"""Utility functions for rules management."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from loguru import logger

from . import Err, Ok, Result

if TYPE_CHECKING:
    from .translation_rules import Rule, RuleFilter, TranslationContext


_COMPONENT_TYPE_CACHE: dict[str, type] = {}


def _resolve_component_type(type_name: str, context: TranslationContext) -> Result[type, TypeError]:
    """Resolve a component type name to a class.

    Uses cache to avoid repeated module imports for the same type.
    Searches modules specified in config.models (defaults to r2x_sienna.models, r2x_plexos.models).

    Parameters
    ----------
    type_name : str
        Name of the component type to resolve
    context : TranslationContext
        Translation context to get models from config

    Returns
    -------
    Result[type, TypeError]
        Ok with the resolved class, or Err if not found

    Notes
    -----
    Uses a module-level cache dict to optimize repeated type lookups.
    Modules to search are configured via config.models.
    """
    if type_name in _COMPONENT_TYPE_CACHE:
        return Ok(_COMPONENT_TYPE_CACHE[type_name])

    modules_to_search: list[str] = list(context.config.models)

    for module_name in modules_to_search:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, type_name):
                component_type = getattr(module, type_name)
                _COMPONENT_TYPE_CACHE[type_name] = component_type
                return Ok(component_type)
        except ImportError:
            continue

    return Err(TypeError(f"Component type '{type_name}' not found in modules: {modules_to_search}"))


def _create_target_component(target_class: type, kwargs: dict[str, Any]) -> Any:
    """Instantiate a target component safely."""
    logger.trace("Building {} with kwargs {}", target_class, kwargs)
    return target_class(**kwargs)


def _make_attr_getter(chain: list[str]) -> Callable[[TranslationContext, Any], Result[Any, ValueError]]:
    """Create a getter that safely walks nested attributes and returns a Result."""

    def _getter(_: TranslationContext, src: Any) -> Result[Any, ValueError]:
        """Extract attributes."""
        val = src
        for attr in chain:
            val = getattr(val, attr, None)
            if val is None:
                break
        return Ok(val)

    return _getter


def _build_target_fields(
    rule: Rule,
    source_component: Any,
    context: TranslationContext,
) -> Result[dict[str, Any], ValueError]:
    """Build field map for the target component.

    All getters must return Result types. Fails fast if source_field has no getter.
    Gracefully falls back to defaults on getter errors.
    """
    kwargs: dict[str, Any] = {}

    for target_field, source_field in rule.field_map.items():
        if isinstance(source_field, list):
            # Multi-field mappings must be handled by a getter; skip direct assignment.
            continue
        value = getattr(source_component, source_field, None)
        if value is None and target_field in rule.defaults:
            value = rule.defaults[target_field]
        elif value is None:
            return Err(
                ValueError(
                    f"No attribute '{source_field}' on source component and no default for '{target_field}'"
                )
            )

        kwargs[target_field] = value

    for target_field, getter_func in rule.getters.items():
        if callable(getter_func):
            result = getter_func(context, source_component)
        else:
            return Err(ValueError(f"Getter for '{target_field}' is not callable: {getter_func}"))

        match result:
            case Ok(value):
                if value is not None:
                    kwargs[target_field] = value
            case Err(e):
                if target_field in rule.defaults:
                    kwargs[target_field] = rule.defaults[target_field]
                else:
                    return Err(ValueError(f"Getter for '{target_field}' failed: {e}"))

    return Ok(kwargs)


def _evaluate_rule_filter(rule_filter: RuleFilter, component: Any) -> bool:
    """Return True if the component satisfies the rule filter."""
    if rule_filter.any_of is not None:
        return any(_evaluate_rule_filter(child, component) for child in rule_filter.any_of)
    if rule_filter.all_of is not None:
        return all(_evaluate_rule_filter(child, component) for child in rule_filter.all_of)

    assert rule_filter.field is not None and rule_filter.op is not None and rule_filter.values is not None

    attr = getattr(component, rule_filter.field, None)
    if attr is None:
        return rule_filter.on_missing == "include"

    candidate = str(attr).casefold() if rule_filter.casefold and isinstance(attr, str) else attr
    values = [
        str(val).casefold() if rule_filter.casefold and isinstance(val, str) else val
        for val in rule_filter.values
    ]

    if rule_filter.op == "eq":
        return candidate == values[0]
    if rule_filter.op == "neq":
        return candidate != values[0]
    if rule_filter.op == "in":
        return candidate in values
    if rule_filter.op == "not_in":
        return candidate not in values
    if rule_filter.op == "geq":
        try:
            cand_num = float(candidate)
            threshold = float(values[0])
        except (TypeError, ValueError):
            return False
        return cand_num >= threshold
    return False
