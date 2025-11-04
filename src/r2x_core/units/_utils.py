"""Internal utility functions for unit conversion and formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, cast, get_origin

import pint

if TYPE_CHECKING:
    from ._mixins import HasUnits
    from ._specs import UnitSpec

ureg = pint.UnitRegistry()


def _convert_to_internal(
    value: Any,
    spec: UnitSpec,
    base_value: float | None = None,
    base_unit: str | None = None,
) -> float:
    """Convert an input value to internal stored representation.

    Parameters
    ----------
    value : float, int, or dict
        Input value; if dict, must contain 'value' and 'unit' keys
    spec : UnitSpec
        Unit specification containing unit metadata
    base_value : float, optional
        Base quantity value for per-unit conversion
    base_unit : str, optional
        Unit string of the base quantity

    Returns
    -------
    float
        Converted value in internal representation (pu for relative units)

    Raises
    ------
    ValueError
        If base field is required but not provided or base unit cannot be determined
    """
    if isinstance(value, int | float):
        return float(value)

    if not isinstance(value, dict):
        return 0.0

    if "value" not in value or "unit" not in value:
        return 0.0

    input_value = float(cast(Any, value["value"]))
    input_unit_str = str(cast(Any, value["unit"]))

    if spec.base is None:
        return input_value

    # For pu conversions, base value and unit are required
    if base_value is None:
        msg = f"Base field '{spec.base}' is required for unit conversion but was not provided or is None"
        raise ValueError(msg)

    if base_unit is None:
        msg = f"Base unit for field '{spec.base}' could not be determined - check field annotations"
        raise ValueError(msg)

    if input_unit_str == base_unit:
        return input_value / base_value

    try:
        input_qty = input_value * ureg(input_unit_str)
        base_qty = base_value * ureg(base_unit)
        ratio = cast(Any, input_qty / base_qty)
        magnitude = getattr(ratio, "magnitude", ratio)
        return float(magnitude)

    except (pint.UndefinedUnitError, pint.DimensionalityError):
        return input_value / base_value


def _format_for_display(
    value: float,
    spec: UnitSpec,
    unit_system: Any,
    base_value: float | None = None,
    base_unit: str | None = None,
    system_base: float | None = None,
) -> str:
    """Format internal float for display based on unit system.

    Parameters
    ----------
    value : float
        Internal stored value (pu for relative units, absolute otherwise)
    spec : UnitSpec
        Unit specification containing unit metadata
    unit_system : UnitSystem
        Display mode (DEVICE_BASE, NATURAL_UNITS, or SYSTEM_BASE)
    base_value : float, optional
        Base quantity value for natural unit conversion
    base_unit : str, optional
        Unit string of the base quantity
    system_base : float, optional
        System-wide base for system-base display

    Returns
    -------
    str
        Formatted string representation with value and unit
    """
    from . import UnitSystem

    if spec.base is None:
        return f"{value} {spec.unit}"

    if unit_system == UnitSystem.DEVICE_BASE:
        return f"{value} pu"

    elif unit_system == UnitSystem.NATURAL_UNITS:
        if base_value is None or base_unit is None:
            return f"{value} pu"
        natural_value = value * base_value
        return f"{natural_value:.4g} {base_unit}"

    elif unit_system == UnitSystem.SYSTEM_BASE:
        if base_value is None:
            return f"{value} pu"
        natural_value = value * base_value
        if system_base is not None and isinstance(system_base, int | float):
            system_pu = natural_value / system_base
            return f"{system_pu:.4g} pu (system)"
        return f"{value} pu"

    return f"{value} pu"


def _is_annotated(obj: Any) -> bool:
    """Check if an object is an Annotated type hint.

    Parameters
    ----------
    obj : Any
        Type annotation object to check

    Returns
    -------
    bool
        True if obj is Annotated[...], False otherwise
    """
    try:
        return get_origin(obj) is Annotated
    except Exception:
        return False


def _get_base_unit_from_context(context: Any, base_field: str) -> str | None:
    """Extract base unit string from validation context.

    Parameters
    ----------
    context : dict or None
        Validation context dictionary
    base_field : str
        Name of the base field to look up

    Returns
    -------
    str or None
        Base unit string if found, None otherwise
    """
    if not isinstance(context, dict):
        return None
    base_units_map = context.get("base_units")
    if not isinstance(base_units_map, dict):
        return None
    bu = base_units_map.get(base_field)
    return bu if isinstance(bu, str) else None


def _get_base_unit_from_subclass(owner_name: str | None, base_field: str) -> str | None:
    """Get base unit by scanning subclasses when context unavailable.

    Parameters
    ----------
    owner_name : str or None
        Name of the owning model class
    base_field : str
        Name of the base field to look up

    Returns
    -------
    str or None
        Base unit string if found, None otherwise
    """
    if not owner_name:
        return None

    from ._mixins import HasUnits

    def _search_subclasses(base_cls: type[HasUnits]) -> str | None:
        """Recursive search of subclasses."""
        for subcls in base_cls.__subclasses__():
            if subcls.__name__ == owner_name:
                specs = subcls._get_unit_specs_map()
                base_spec = specs.get(base_field)
                if base_spec:
                    return base_spec.unit
            result = _search_subclasses(subcls)
            if result:
                return result
        return None

    return _search_subclasses(HasUnits)
