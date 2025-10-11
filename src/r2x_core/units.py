"""Unit handling for power system models.

Core ideas:
* Annotate numeric fields with ``Annotated[float, Unit("kV"|"MVA"|"pu", base="base_field")]``.
* Natural-unit inputs (``{"value": 138, "unit": "kV"}``) are converted to per-unit when ``base`` is set.
* Internal storage is always float (device-base per-unit for relative quantities).
* Global display mode (device base, system base, or natural units) affects ``__repr__`` formatting only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, cast, get_args, get_origin

import pint
from infrasys import Component
from pydantic import GetCoreSchemaHandler, PrivateAttr
from pydantic_core import core_schema

if TYPE_CHECKING:
    from pydantic import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue

# Initialize default Pint unit registry for standalone use
ureg = pint.UnitRegistry()


class UnitSystem(str, Enum):
    """Available display modes for formatted representation."""

    DEVICE_BASE = "device_base"
    SYSTEM_BASE = "system_base"
    NATURAL_UNITS = "natural_units"


# Track the current display unit system (global setting)
_current_unit_system: UnitSystem = UnitSystem.DEVICE_BASE


def get_unit_system() -> UnitSystem:
    """Return current global display mode."""
    return _current_unit_system


def set_unit_system(unit_system: UnitSystem) -> None:
    """Set global display mode (affects repr only)."""
    global _current_unit_system
    _current_unit_system = unit_system


@dataclass(frozen=True)
class UnitSpec:
    """Descriptor metadata for unit-aware fields."""

    unit: str  # Unit string (e.g., "MVA", "pu", "kV")
    base: str | None = None  # Field name for device base lookup (for pu units)

    def convert_to_base_units(
        self, value: Any, base_value: float | None = None, base_unit: str | None = None
    ) -> float:
        """Convert an input (float or {"value","unit"}) to stored float."""
        if isinstance(value, (int, float)):
            return float(value)

        if not isinstance(value, dict):
            return 0.0

        if "value" not in value or "unit" not in value:
            return 0.0

        input_value = float(cast(Any, value["value"]))
        input_unit_str = str(cast(Any, value["unit"]))

        if self.base is None:
            return input_value

        if base_value is None:
            return input_value

        if base_unit is None:
            return input_value

        try:
            input_qty = input_value * ureg(input_unit_str)
            base_qty = base_value * ureg(base_unit)

            # Pint typing incomplete; ignore for conversion
            ratio = cast(Any, input_qty / base_qty)
            # ratio should already be dimensionless quantity
            magnitude = getattr(ratio, "magnitude", ratio)
            return float(magnitude)

        except (pint.UndefinedUnitError, pint.DimensionalityError):
            return input_value / base_value

    def _validate_value(self, value: Any, info: core_schema.ValidationInfo) -> float:
        """Validator used by Pydantic core schema."""
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, dict) and "value" in value and "unit" in value:
            input_value = float(cast(Any, value["value"]))

            if self.base is None:
                return input_value

            # Base numeric value (e.g. base_power) must already be validated
            base_value = info.data.get(self.base) if info.data else None
            if base_value is None:
                return input_value

            # Resolve base field's declared unit via subclass annotation scan
            base_unit: str | None = None
            cfg = info.config  # runtime core config mapping
            owner = cfg.get("title") if cfg else None
            if owner:
                # Look through subclasses to find matching model class by name
                for subcls in UnitAwareModel.__subclasses__():
                    if subcls.__name__ == owner:
                        annotations = getattr(subcls, "__annotations__", {})
                        ann = annotations.get(self.base)
                        if _is_annotated(ann):
                            for meta in get_args(ann)[1:]:
                                if isinstance(meta, UnitSpec):
                                    base_unit = meta.unit
                                    break
                        break

            return self.convert_to_base_units(value, base_value, base_unit)

        raise ValueError("Expected float or dict with 'value' and 'unit'")

    def __get_pydantic_core_schema__(
        self,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Attach custom validator (float or mapping -> float)."""
        python_schema = core_schema.with_info_after_validator_function(
            self._validate_value,
            core_schema.union_schema([core_schema.float_schema(), core_schema.dict_schema()]),
        )

        return core_schema.json_or_python_schema(
            json_schema=core_schema.float_schema(),
            python_schema=python_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: float(x) if isinstance(x, (int, float)) else x,
                return_schema=core_schema.float_schema(),
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """JSON schema: treat as number."""
        return handler(core_schema.float_schema())


def unit_spec(
    unit: str,
    base: str | None = None,
) -> UnitSpec:
    """Factory for concise annotation usage."""
    return UnitSpec(unit=unit, base=base)


# Alias for backwards compatibility and annotation style
Unit = unit_spec


def _is_annotated(obj: Any) -> bool:
    try:
        return get_origin(obj) is Annotated
    except Exception:
        return False


class UnitAwareModel(Component):
    """Mixin providing unit-aware storage + formatted repr."""

    _system_base: float | None = PrivateAttr(default=None)

    # Cache of field -> UnitSpec for subclasses (avoids repeated annotation walks)
    _unit_specs_cache: dict[str, UnitSpec] | None = None

    @classmethod
    def _get_unit_specs_map(cls) -> dict[str, UnitSpec]:
        if cls._unit_specs_cache is None:
            specs: dict[str, UnitSpec] = {}
            annotations = getattr(cls, "__annotations__", {})
            for fname, ann in annotations.items():
                if _is_annotated(ann):
                    for meta in get_args(ann)[1:]:
                        if isinstance(meta, UnitSpec):
                            specs[fname] = meta
            cls._unit_specs_cache = specs
        return cls._unit_specs_cache

    @classmethod
    def _get_unit_spec(cls, field_name: str) -> UnitSpec | None:
        """Return UnitSpec for field if annotated."""
        for base_cls in cls.__mro__:
            if not hasattr(base_cls, "__annotations__"):
                continue
            if field_name not in base_cls.__annotations__:
                continue

            annotation = base_cls.__annotations__[field_name]

            # Check if field has Annotated metadata
            if _is_annotated(annotation):
                args = get_args(annotation)
                # Look for UnitSpec in metadata
                for arg in args[1:]:  # Skip first arg (the actual type)
                    if isinstance(arg, UnitSpec):
                        return arg

        return None

    def __repr_args__(self) -> list[tuple[str | None, Any]]:
        """Format fields respecting current display mode."""
        repr_args: list[tuple[str | None, Any]] = []

        for field_name in type(self).model_fields:
            if field_name.startswith("_"):
                continue

            value = getattr(self, field_name)
            unit_spec = self._get_unit_spec(field_name)

            if unit_spec is None:
                repr_args.append((field_name, value))
            else:
                formatted = self._format_field_for_display(field_name, value, unit_spec)
                repr_args.append((field_name, formatted))

        return repr_args

    def _format_field_for_display(self, field_name: str, value: float, unit_spec: UnitSpec) -> str:
        """Convert internal stored float to human string."""
        # Get the global unit system setting
        unit_system = get_unit_system()

        # For absolute units (no base field), always display with their unit
        if unit_spec.base is None:
            return f"{value} {unit_spec.unit}"

        # For relative units (pu):
        # In device base display mode, show pu
        if unit_system == UnitSystem.DEVICE_BASE:
            return f"{value} pu"

        # For natural units, convert using Pint
        elif unit_system == UnitSystem.NATURAL_UNITS:
            if unit_spec.base:
                try:
                    base_value = getattr(self, unit_spec.base, None)
                    if base_value is None:
                        return f"{value} pu"
                    base_spec = self._get_unit_spec(unit_spec.base)
                    natural_unit = base_spec.unit if base_spec else "dimensionless"
                    natural_value = value * base_value
                    return f"{natural_value:.4g} {natural_unit}"
                except AttributeError:
                    return f"{value} pu"
            return f"{value} pu"

        # For system base, convert using component's _system_base if available
        elif unit_system == UnitSystem.SYSTEM_BASE:
            if unit_spec.base:
                try:
                    # Get device base value
                    base_value = getattr(self, unit_spec.base, None)
                    if base_value is None:
                        return f"{value} pu"

                    # Convert to natural units
                    natural_value = value * base_value

                    # If component has a _system_base set, use it for conversion
                    if self._system_base is not None:
                        system_pu = natural_value / self._system_base
                        return f"{system_pu:.4g} pu (system)"
                    else:
                        # No system_base set, show device base pu
                        return f"{value} pu"
                except AttributeError:
                    pass
            return f"{value} pu"

        return f"{value} pu"

    @staticmethod
    def _is_annotated(obj: Any) -> bool:
        """Return True if obj is an Annotated type."""
        try:
            return get_origin(obj) is Annotated
        except Exception:
            return False
