"""Unit specification and annotation types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast, get_args, get_origin

from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import core_schema

from ._utils import _convert_to_internal, _get_base_unit_from_context, _get_base_unit_from_subclass

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

    def _validate_value(self, value: Any, info: core_schema.ValidationInfo) -> float | BaseModel | None:
        """Customize validation for Unit."""
        if value is None:
            return None

        if isinstance(value, BaseModel):
            return self._convert_structured_type(value, info)

        if isinstance(value, int | float):
            return float(value)

        if isinstance(value, dict):
            if "value" in value and "unit" in value:
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

            raise ValueError("Dict must contain 'value' and 'unit' keys for unit conversion")

        raise ValueError("Expected float, dict with 'value' and 'unit', or BaseModel instance")

    def _convert_structured_type(self, value: BaseModel, info: core_schema.ValidationInfo) -> BaseModel:
        """Handle custom base models from applications."""
        if self.base is None:
            return value

        base_value = info.data.get(self.base) if info.data else None
        if base_value is None:
            return value

        ctx_raw = getattr(info, "context", None)
        base_unit = _get_base_unit_from_context(ctx_raw, self.base)

        if base_unit is None:
            cfg = info.config
            owner = cfg.get("title") if cfg else None
            base_unit = _get_base_unit_from_subclass(owner, self.base)

        model_fields = type(value).model_fields
        converted_fields = {}

        for field_name, field_value in value.model_dump().items():
            field_info = model_fields.get(field_name)
            if not field_info:
                converted_fields[field_name] = field_value
                continue

            field_type = field_info.annotation
            origin = get_origin(field_type)

            if origin is type(None) or (hasattr(origin, "__name__") and "Union" in str(origin)):
                args = get_args(field_type)
                non_none_types = [arg for arg in args if arg is not type(None)]
                if non_none_types:
                    field_type = non_none_types[0]

            is_numeric = field_type in (int, float) or (
                isinstance(field_type, type)
                and issubclass(field_type, int | float)
                and not issubclass(field_type, bool)
            )

            if is_numeric and isinstance(field_value, int | float) and not isinstance(field_value, bool):
                converted_fields[field_name] = field_value / base_value
            else:
                converted_fields[field_name] = field_value

        return type(value)(**converted_fields)

    def __get_pydantic_core_schema__(
        self,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Set pydantic serialization."""
        actual_type = source_type
        origin = get_origin(source_type)
        if origin is type(None) or (hasattr(origin, "__name__") and "Union" in str(origin)):
            args = get_args(source_type)
            non_none_types = [arg for arg in args if arg is not type(None)]
            if non_none_types:
                actual_type = non_none_types[0]

        is_structured_type = False
        try:
            if isinstance(actual_type, type) and issubclass(actual_type, BaseModel):
                is_structured_type = True
        except TypeError:
            pass

        if is_structured_type:
            python_schema = core_schema.with_info_after_validator_function(
                self._validate_value,
                core_schema.union_schema([handler(actual_type), core_schema.none_schema()]),
            )

            def serialize_structured(x: Any) -> Any:
                """Serialize base model."""
                if isinstance(x, BaseModel):
                    return x.model_dump()
                return x

            return core_schema.json_or_python_schema(
                json_schema=handler(actual_type),
                python_schema=python_schema,
                serialization=core_schema.plain_serializer_function_ser_schema(
                    serialize_structured,
                    return_schema=core_schema.dict_schema(),
                    when_used="json-unless-none",
                ),
            )

        python_schema = core_schema.with_info_after_validator_function(
            self._validate_value,
            core_schema.union_schema(
                [core_schema.float_schema(), core_schema.dict_schema(), core_schema.none_schema()]
            ),
        )

        return core_schema.json_or_python_schema(
            json_schema=core_schema.float_schema(),
            python_schema=python_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: float(x) if isinstance(x, int | float) else x,
                return_schema=core_schema.float_schema(),
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Set pydantic json serialization."""
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
