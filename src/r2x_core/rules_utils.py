"""Utility functions for rules management."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from loguru import logger
from rust_ok import Err, Ok, Result

from .context import ContextT

if TYPE_CHECKING:
    from .context import TranslationContext
    from .rules import Rule, RuleFilter, RuleLike


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
    """Build field map for the target component."""
    return build_component_kwargs(rule, source_component, context)


def _as_attr_source(source_component: Any) -> Any:
    """Return an object that supports attribute access for the provided record."""
    if isinstance(source_component, Mapping):
        return SimpleNamespace(**source_component)
    return source_component


def build_component_kwargs(
    rule: RuleLike[ContextT],
    source_component: Any,
    context: ContextT,
) -> Result[dict[str, Any], ValueError]:
    """Construct kwargs for instantiating a target component.

    Parameters
    ----------
    rule : RuleLike
        Object exposing field_map, getters, and defaults.
    source_component : Any
        Source object or parser record providing attributes referenced by the rule.
    context : Context
        Active context passed to getters (TranslationContext or custom).
    """
    source_obj = _as_attr_source(source_component)
    field_map = getattr(rule, "field_map", {})
    getters = getattr(rule, "getters", {})
    defaults = getattr(rule, "defaults", {})
    kwargs: dict[str, Any] = {}

    for target_field, source_field in field_map.items():
        if isinstance(source_field, list):
            # Multi-field mappings must be handled by a getter; skip direct assignment.
            continue
        value = getattr(source_obj, source_field, None)
        if value is None and target_field in defaults:
            value = defaults[target_field]
        elif value is None:
            return Err(
                ValueError(
                    f"No attribute '{source_field}' on source component and no default for '{target_field}'"
                )
            )

        kwargs[target_field] = value

    for target_field, getter_func in getters.items():
        if callable(getter_func):
            result = getter_func(context, source_obj)
        else:
            return Err(ValueError(f"Getter for '{target_field}' is not callable: {getter_func}"))

        match result:
            case Ok(value):
                if value is not None:
                    kwargs[target_field] = value
            case Err(e):
                if target_field in defaults:
                    kwargs[target_field] = defaults[target_field]
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

    candidate_for_general = str(attr).casefold() if rule_filter.casefold and isinstance(attr, str) else attr
    values = [
        str(val).casefold() if rule_filter.casefold and isinstance(val, str) else val
        for val in rule_filter.values
    ]

    if rule_filter.op == "eq":
        return candidate_for_general == values[0]
    if rule_filter.op == "neq":
        return candidate_for_general != values[0]
    if rule_filter.op == "in":
        return candidate_for_general in values
    if rule_filter.op == "not_in":
        return candidate_for_general not in values
    if rule_filter.op == "geq":
        try:
            cand_num = float(candidate_for_general)
            threshold = float(values[0])
        except (TypeError, ValueError):
            return False
        return cand_num >= threshold
    if rule_filter.op in {"startswith", "not_startswith"}:
        candidate_str = str(attr)
        if rule_filter.casefold:
            candidate_str = candidate_str.casefold()
        prefixes = rule_filter.normalized_prefixes()
        if rule_filter.op == "startswith":
            return any(candidate_str.startswith(prefix) for prefix in prefixes)
        return all(not candidate_str.startswith(prefix) for prefix in prefixes)
    return False


def _sort_rules_by_dependencies(rules: list[Rule]) -> Result[list[Rule], ValueError]:
    """Sort rules by dependencies using topological sort.

    Parameters
    ----------
    rules : list[Rule]
        Rules to sort

    Returns
    -------
    Result[list[Rule], ValueError]
        Ok with sorted rules, or Err if circular dependencies detected

    Notes
    -----
    Rules without names or dependencies are placed at the beginning.
    Uses Kahn's algorithm for topological sorting.
    """
    named_rules: dict[str, Rule] = {}
    unnamed_rules: list[Rule] = []

    for rule in rules:
        if rule.name:
            if rule.name in named_rules:
                return Err(ValueError(f"Duplicate rule name: {rule.name}"))
            named_rules[rule.name] = rule
        else:
            unnamed_rules.append(rule)

    # Dependency graph
    in_degree: dict[str, int] = dict.fromkeys(named_rules, 0)
    adjacency: dict[str, list[str]] = {name: [] for name in named_rules}

    for name, rule in named_rules.items():
        if rule.depends_on:
            for dep in rule.depends_on:
                if dep not in named_rules:
                    return Err(ValueError(f"Rule '{name}' depends on unknown rule '{dep}'"))
                adjacency[dep].append(name)
                in_degree[name] += 1

    # Kahn's algorithm
    queue = [name for name, degree in in_degree.items() if degree == 0]
    sorted_names: list[str] = []

    while queue:
        current = queue.pop(0)
        sorted_names.append(current)

        for neighbor in adjacency[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_names) != len(named_rules):
        unsorted = set(named_rules.keys()) - set(sorted_names)
        return Err(ValueError(f"Circular dependencies detected in rules: {', '.join(unsorted)}"))

    sorted_rules = unnamed_rules + [named_rules[name] for name in sorted_names]
    return Ok(sorted_rules)
