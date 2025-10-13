"""Unit specification and annotation types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

if TYPE_CHECKING:
    from pydantic import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue


@dataclass(frozen=True)
class UnitSpec:
    """Metadata descriptor for unit-aware fields.

    Attributes
    ----------
    unit : str
        Unit string (e.g., "MVA", "pu", "kV")
    base : str, optional
        Field name for device base lookup (for pu units)
    """

    unit: str
    base: str | None = None

    def _validate_value(self, value: Any, info: core_schema.ValidationInfo) -> float:
        """Validate and convert input value to internal representation.

        Parameters
        ----------
        value : float, int, or dict
            Input value to validate
        info : core_schema.ValidationInfo
            Pydantic validation context

        Returns
        -------
        float
            Validated and converted value

        Raises
        ------
        ValueError
            If value format is invalid
        """
        # Import here to avoid circular dependency
        from ._utils import _convert_to_internal, _get_base_unit_from_context, _get_base_unit_from_subclass

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, dict) and "value" in value and "unit" in value:
            input_value = float(cast(Any, value["value"]))

            if self.base is None:
                return input_value

            base_value = info.data.get(self.base) if info.data else None
            if base_value is None:
                return input_value

            ctx_raw = getattr(info, "context", None)
            base_unit = _get_base_unit_from_context(ctx_raw, self.base)

            if base_unit is None:
                cfg = info.config
                owner = cfg.get("title") if cfg else None
                base_unit = _get_base_unit_from_subclass(owner, self.base)

            return _convert_to_internal(value, self, base_value, base_unit)

        raise ValueError("Expected float or dict with 'value' and 'unit'")

    def __get_pydantic_core_schema__(
        self,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Attach custom validator for float or mapping to float conversion.

        Parameters
        ----------
        source_type : Any
            Source type being annotated
        handler : GetCoreSchemaHandler
            Pydantic schema handler

        Returns
        -------
        core_schema.CoreSchema
            Pydantic core schema for validation
        """
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
        """Generate JSON schema representation.

        Parameters
        ----------
        _core_schema : core_schema.CoreSchema
            Pydantic core schema
        handler : GetJsonSchemaHandler
            JSON schema handler

        Returns
        -------
        JsonSchemaValue
            JSON schema treating this as a number
        """
        return handler(core_schema.float_schema())


def unit_spec(
    unit: str,
    base: str | None = None,
) -> UnitSpec:
    """Create a UnitSpec for field annotation.

    Parameters
    ----------
    unit : str
        Unit string (e.g., "MVA", "kV", "pu")
    base : str, optional
        Field name for device base lookup

    Returns
    -------
    UnitSpec
        Unit specification instance
    """
    return UnitSpec(unit=unit, base=base)


Unit = unit_spec
