"""Getter registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, overload

from loguru import logger

from r2x_core import Err, Ok

if TYPE_CHECKING:
    from r2x_core import Result

    from .translation_rules import TranslationContext

GetterFunc = Callable[[TranslationContext, Any], Any]
F = TypeVar("F", bound=GetterFunc)

GETTER_REGISTRY: dict[str, GetterFunc] = {}


@overload
def getter(func: F) -> F: ...


@overload
def getter(*, name: str | None = None) -> Callable[[F], F]: ...


def getter(func: F | None = None, *, name: str | None = None) -> F | Callable[[F], F]:
    """Decorate a getter function by name.

    Supports three usage patterns:
    1. @getter - uses function name as registry key
    2. @getter(name="custom_name") - uses provided string as registry key
    3. @getter() - uses function name as registry key

    Parameters
    ----------
    func : F | None
        The decorated function when used without parentheses,
        or None when used as @getter() / @getter(name="...")

    Returns
    -------
    F | Callable[[F], F]
        Returns the original function (preserving type) when used as @getter,
        or a decorator function when used with arguments

    Raises
    ------
    ValueError
        If a getter with the same name is already registered

    Examples
    --------
    Register with function name:
    >>> @getter
    ... def get_max_capacity(ctx, component):
    ...     return component.rating * 1.5

    Register with custom name:
    >>> @getter(name="thermal_capacity")
    ... def get_max_capacity(ctx, component):
    ...     return component.rating * 1.5

    Register with empty parentheses:
    >>> @getter()
    ... def get_max_capacity(ctx, component):
    ...     return component.rating * 1.5
    """
    # @getter (without parentheses) - func is the function
    if func is not None:
        if name is not None:
            raise TypeError(
                "Cannot specify 'name' when using @getter without parentheses. Use keywords instead."
            )
        return _register_getter(func, func.__name__)

    # @getter() or @getter(name="...") - func is None
    def _decorator(f: F) -> F:
        registry_key = name or f.__name__
        return _register_getter(f, registry_key)

    return _decorator


def _register_getter(func: F, name: str) -> F:
    """Register a getter and return the function."""
    if name in GETTER_REGISTRY:
        raise ValueError(f"Getter '{name}' already registered by {GETTER_REGISTRY[name].__module__}")

    GETTER_REGISTRY[name] = func
    logger.trace("Registered getter '{}' from {}.{}", name, func.__module__, func.__qualname__)
    return func


def _preprocess_rule_getters(getters_dict: dict[str, Any]) -> Result[dict[str, Any], TypeError]:
    """Convert string-based getters in a rule into callables."""
    from .rules_utils import _make_attr_getter

    resolved: dict[str, GetterFunc] = {}
    for field, getter in getters_dict.items():
        if callable(getter):
            resolved[field] = getter
        elif isinstance(getter, str):
            if getter in GETTER_REGISTRY:
                resolved[field] = GETTER_REGISTRY[getter]
            else:
                resolved[field] = _make_attr_getter(getter.split("."))
        else:
            return Err(TypeError(f"Invalid getter type for '{field}': {type(getter).__name__}"))
    return Ok(resolved)


def get_registered_getter(name: str) -> Callable[[TranslationContext, Any], Any]:
    """Retrieve a registered getter by name.

    Parameters
    ----------
    name : str
        The name under which the getter was registered

    Returns
    -------
    Callable[[TranslationContext, Any], Any]
        The getter function

    Raises
    ------
    KeyError
        If no getter with the given name is registered

    Examples
    --------
    >>> getter_func = get_registered_getter("get_voltage")
    >>> result = getter_func(context, component)
    """
    if name not in GETTER_REGISTRY:
        available = ", ".join(sorted(GETTER_REGISTRY.keys()))
        raise KeyError(
            f"Getter '{name}' not found in registry. Available getters: {available or '(none registered)'}"
        )
    return GETTER_REGISTRY[name]


def list_registered_getters() -> dict[str, GetterFunc]:
    """List all registered getters.

    Returns
    -------
    dict[str, Callable]
        Mapping of getter names to their functions

    Examples
    --------
    >>> getters = list_registered_getters()
    >>> for name, func in getters.items():
    ...     print(f"{name}: {func.__doc__}")
    """
    return GETTER_REGISTRY.copy()


def clear_getter_registry() -> None:
    """Clear all registered getters.

    Useful for testing or when resetting the conversion environment.

    Warning
    -------
    This removes all registered getters. Use with caution in tests.
    """
    GETTER_REGISTRY.clear()
    logger.debug("Cleared getter registry")
