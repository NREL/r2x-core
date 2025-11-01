"""Optimized serialization for modules with rich metadata and JSON schema support."""

import inspect
import json
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import core_schema

INCLUDE_FULL_METADATA = True

_module_cache: dict[int, str] = {}


def get_pydantic_schema(model_class: type[BaseModel]) -> dict[str, Any]:
    """Get JSON schema for a Pydantic model (language-agnostic format)."""
    return model_class.model_json_schema()


def export_schemas_for_documentation(
    output_path: str, include_models: list[type[BaseModel]] | None = None
) -> None:
    """Export JSON schemas for plugin types to a file."""
    if include_models is None:
        from r2x_core.package import Package
        from r2x_core.plugin import ExporterPlugin, ParserPlugin, UpgraderPlugin

        include_models = [Package, ParserPlugin, UpgraderPlugin, ExporterPlugin]

    schemas = {model.__name__: get_pydantic_schema(model) for model in include_models}

    with open(output_path, "w") as f:
        json.dump(schemas, f, indent=2)


class _ImportableAnnotation:
    """Annotation for serializable callables/types with rich metadata.

    Includes full signature metadata by default (INCLUDE_FULL_METADATA).
    Toggle INCLUDE_FULL_METADATA = False at module level for faster serialization.
    """

    def __get_pydantic_core_schema__(self, source_type, handler):
        expected_type = _get_expected_type(source_type)

        def validator(v: Any) -> Any:
            obj = _deserialize_value(v)
            if (
                expected_type
                and obj is not None
                and not isinstance(obj, list | tuple)
                and (not isinstance(obj, type) or not issubclass(obj, expected_type))
            ):
                raise TypeError(f"Expected {expected_type.__name__} subclass, got {obj!r}")
            return obj

        def serializer(v: Any) -> Any:
            return _serialize_value(v, full_metadata=INCLUDE_FULL_METADATA)

        return core_schema.no_info_after_validator_function(
            validator,
            core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                serializer,
                return_schema=core_schema.any_schema(),
            ),
        )


Importable = _ImportableAnnotation()


def _get_module_name(obj: Any) -> str:
    """Get module name with caching."""
    obj_id = id(obj)
    if obj_id not in _module_cache:
        module = inspect.getmodule(obj)
        _module_cache[obj_id] = module.__name__ if module else "__main__"
    return _module_cache[obj_id]


def _import_path(path: str) -> Any:
    """Import object from 'module.name' path."""
    module_name, attr = path.rsplit(".", 1)
    return getattr(__import__(module_name, fromlist=[attr]), attr)


def _serialize_callable_fast(obj: Any) -> dict[str, Any]:
    """Serialize callable/class without signature (fast path)."""
    return {
        "module": _get_module_name(obj),
        "name": obj.__name__,
        "type": "class" if isinstance(obj, type) else "function",
    }


def _serialize_callable_full(obj: Any) -> dict[str, Any]:
    """Serialize callable/class with full signature metadata."""
    data = _serialize_callable_fast(obj)

    try:
        sig = inspect.signature(obj)
        data["parameters"] = {
            n: {
                "annotation": str(p.annotation) if p.annotation != inspect.Parameter.empty else None,
                "default": p.default if p.default != inspect.Parameter.empty else None,
                "is_required": p.default == inspect.Parameter.empty
                and p.kind
                not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                ),
            }
            for n, p in sig.parameters.items()
        }
        data["return_annotation"] = (
            str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else None
        )
    except (ValueError, TypeError):
        data["parameters"] = {}
        data["return_annotation"] = None

    return data


def _serialize_value(v: Any, full_metadata: bool = False) -> Any:
    """Serialize value with optional full metadata (fast by default)."""
    if v is None:
        return v

    v_type = type(v)
    if v_type in (str, int, float, bool):
        return v

    if v_type in (list, tuple):
        return [_serialize_value(item, full_metadata) for item in v]

    if isinstance(v, BaseModel):
        return v.model_dump()

    if v_type is type or (callable(v) and not isinstance(v, dict | set | frozenset)):
        try:
            return _serialize_callable_full(v) if full_metadata else _serialize_callable_fast(v)
        except Exception:
            return str(v)

    return v


def _deserialize_value(v: Any) -> Any:
    """Deserialize, converting metadata dicts/paths back to objects."""
    if v is None or type(v) in (int, float, bool):
        return v

    v_type = type(v)
    if v_type in (list, tuple):
        return [_deserialize_value(item) for item in v]

    if v_type is dict:
        if "module" in v and "name" in v:
            try:
                return _import_path(f"{v['module']}.{v['name']}")
            except Exception:
                return v
        return v

    if v_type is str and "." in v:
        try:
            return _import_path(v)
        except Exception:
            return v

    return v


def _get_expected_type(source_type: Any) -> Any:
    """Extract base class from type[T] or type[T] | None."""
    origin = get_origin(source_type)
    if origin is Union:
        args = [arg for arg in get_args(source_type) if arg is not type(None)]
        source_type = args[0] if args else source_type
    if get_origin(source_type) is type:
        args = get_args(source_type)
        return args[0] if args else None
    return None
