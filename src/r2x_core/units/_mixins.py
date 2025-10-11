"""Mixin classes for unit-aware models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, get_args

from pydantic import PrivateAttr, model_validator

if TYPE_CHECKING:
    from ._specs import UnitSpec


class HasUnits:
    """Mixin providing unit-aware field formatting.

    This mixin provides unit-aware field formatting in repr without per-unit
    conversion capabilities. Suitable for components that only have absolute
    unit fields (e.g., voltages in kV, power in MW) without base conversions.

    Can be combined with any Pydantic BaseModel or Component:
        class MyComponent(HasUnits, Component): ...
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate that subclass inherits from BaseModel.

        Raises
        ------
        TypeError
            If the subclass does not inherit from pydantic.BaseModel
        """
        super().__init_subclass__(**kwargs)
        from pydantic import BaseModel

        # Skip validation for HasPerUnit (which is also a mixin)
        if cls.__name__ == "HasPerUnit":
            return

        # Check if any base class is BaseModel
        if not any(issubclass(base, BaseModel) for base in cls.__mro__ if base not in (cls, HasUnits)):
            raise TypeError(
                f"{cls.__name__} must inherit from pydantic.BaseModel or infrasys.Component. "
                f"Example: class {cls.__name__}(HasUnits, Component): ..."
            )

    def _get_system_base(self) -> float | None:
        """Get system base value if this component supports it.

        Returns
        -------
        float or None
            System base value, or None if not supported
        """
        return None

    @classmethod
    def _get_unit_specs_map(cls) -> dict[str, UnitSpec]:
        """Build and cache unit specifications for all annotated fields.

        Returns
        -------
        dict[str, UnitSpec]
            Mapping of field names to their unit specifications
        """
        # Import here to avoid circular dependency
        from ._specs import UnitSpec
        from ._utils import _is_annotated

        cache_attr = f"_unit_specs_cache_{cls.__name__}"
        if not hasattr(cls, cache_attr):
            specs: dict[str, UnitSpec] = {}
            annotations = getattr(cls, "__annotations__", {})
            for fname, ann in annotations.items():
                if _is_annotated(ann):
                    for meta in get_args(ann)[1:]:
                        if isinstance(meta, UnitSpec):
                            specs[fname] = meta
            setattr(cls, cache_attr, specs)
        cached: dict[str, UnitSpec] = getattr(cls, cache_attr)
        return cached

    @model_validator(mode="wrap")
    @classmethod
    def _seed_unit_context(cls, values: Any, handler: Any, info: Any) -> Any:
        """Seed validation context with unit specs and base units map.

        Parameters
        ----------
        values : Any
            Input values to validate
        handler : Any
            Validation handler
        info : Any
            Validation info containing context

        Returns
        -------
        Any
            Validated model instance
        """
        ctx = info.context if info.context is not None else {}
        if isinstance(ctx, dict) and ("unit_specs" not in ctx or "base_units" not in ctx):
            specs = cls._get_unit_specs_map()
            base_units = {fname: spec.unit for fname, spec in specs.items() if spec.base is None}
            ctx.setdefault("unit_specs", specs)
            ctx.setdefault("base_units", base_units)
        return handler(values)

    def __repr_args__(self) -> list[tuple[str | None, Any]]:
        """Format fields respecting current display mode.

        Returns
        -------
        list[tuple[str | None, Any]]
            List of (field_name, formatted_value) tuples for repr
        """
        # Import here to avoid circular dependency
        from . import get_unit_system
        from ._utils import _format_for_display

        repr_args: list[tuple[str | None, Any]] = []
        specs_map = type(self)._get_unit_specs_map()
        unit_system = get_unit_system()

        for field_name in type(self).model_fields:  # type: ignore[attr-defined]
            if field_name.startswith("_"):
                continue

            value = getattr(self, field_name)
            unit_spec = specs_map.get(field_name)

            if unit_spec is None:
                repr_args.append((field_name, value))
            else:
                base_value: float | None = None
                base_unit: str | None = None
                if unit_spec.base:
                    base_value = getattr(self, unit_spec.base, None)
                    base_spec = specs_map.get(unit_spec.base)
                    base_unit = base_spec.unit if base_spec else None

                formatted = _format_for_display(
                    value, unit_spec, unit_system, base_value, base_unit, self._get_system_base()
                )
                repr_args.append((field_name, formatted))

        return repr_args


class HasPerUnit(HasUnits):
    """Component class with per-unit conversion capabilities.

    This class extends HasUnits with system-base per-unit display support.
    Use this for components that have both absolute unit fields (base values)
    and per-unit fields that reference those bases.

    Attributes
    ----------
    _system_base : float or None
        System-wide base power for system-base per-unit display
    """

    _system_base: float | None = PrivateAttr(default=None)

    def _get_system_base(self) -> float | None:
        """Get system base value for this component.

        Returns
        -------
        float or None
            System base value, or None if not set
        """
        return self.__dict__.get("_system_base")
