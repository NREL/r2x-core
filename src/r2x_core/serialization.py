"""Serialization system for classes/functions with optional metadata and JSON schemas.

Provides transparent serialization of callables (functions, classes) as importable
paths ("module:Name" format) with optional rich metadata including signatures and
parameter information. Uses Pydantic's custom schema system for seamless integration.

Key components:
- Importable: Annotation for fields holding serializable classes/functions
- Fast path: Basic serialization with module, name, type (no introspection)
- Full path: Extended serialization with parameter signatures and defaults
- Schema export: Generate JSON schemas for plugin documentation

Usage:

    from pydantic import BaseModel
    from r2x_core.serialization import Importable

    class MyConfig(BaseModel):
        handler: Annotated[type, Importable]  # Can serialize/deserialize handler class

    # Automatically serializes to {"module": "mymod", "name": "MyHandler", "type": "class"}

The serialization system is used internally for plugin metadata, allowing classes
and functions to be stored in config files and reconstructed at runtime.

See Also
--------
:class:`~r2x_core.plugin.BasePlugin` : Uses Importable for plugin callables.
:func:`get_pydantic_schema` : Export Pydantic model JSON schemas.
"""

import inspect
import json
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import core_schema

INCLUDE_FULL_METADATA = True

_module_cache: dict[int, str] = {}


def get_pydantic_schema(model_class: type[BaseModel]) -> dict[str, Any]:
    """Get JSON schema for a Pydantic model.

    Generates a JSON Schema (language-agnostic) representation of the Pydantic model's
    structure, field types, descriptions, and validation constraints. Useful for
    documentation generation, API schema publishing, and validation.

    Parameters
    ----------
    model_class : type[BaseModel]
        A Pydantic BaseModel subclass to extract schema from.

    Returns
    -------
    dict[str, Any]
        JSON Schema dictionary with $schema, title, properties, required, etc.
        Can be serialized to JSON for documentation or API schemas.

    Examples
    --------
    >>> from pydantic import BaseModel, Field
    >>> from r2x_core.serialization import get_pydantic_schema
    >>> class Config(BaseModel):
    ...     name: str = Field(description="Config name")
    ...     version: int = Field(default=1, ge=0)
    >>> schema = get_pydantic_schema(Config)
    >>> schema['properties']['name']
    {'title': 'Name', 'type': 'string', 'description': 'Config name'}
    """
    return model_class.model_json_schema()


def export_schemas_for_documentation(
    output_path: str, include_models: list[type[BaseModel]] | None = None
) -> None:
    """Export JSON schemas for models to a file for documentation.

    Generates JSON schemas for specified Pydantic models and writes them to a JSON
    file. Useful for generating OpenAPI/Swagger docs, API documentation, or
    schema validation specifications.

    Parameters
    ----------
    output_path : str
        File path to write JSON schemas to (e.g., "/path/to/schemas.json").
    include_models : list[type[BaseModel]] | None
        List of Pydantic model classes to export. If None, uses default list:
        [Package, ParserPlugin, UpgraderPlugin, ExporterPlugin].
        Default is None.

    Returns
    -------
    None

    Examples
    --------
    Export default plugin schemas:

    >>> from r2x_core.serialization import export_schemas_for_documentation
    >>> export_schemas_for_documentation("schemas.json")

    Export custom models:

    >>> from pydantic import BaseModel
    >>> class CustomModel(BaseModel):
    ...     field: str
    >>> export_schemas_for_documentation("out.json", [CustomModel])
    """
    if include_models is None:
        from r2x_core.package import Package
        from r2x_core.plugin import ExporterPlugin, ParserPlugin, UpgraderPlugin

        include_models = [Package, ParserPlugin, UpgraderPlugin, ExporterPlugin]

    schemas = {model.__name__: get_pydantic_schema(model) for model in include_models}

    with open(output_path, "w") as f:
        json.dump(schemas, f, indent=2)


class _ImportableAnnotation:
    """Annotation for serializable callables/types with rich metadata."""

    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """Generate Pydantic core schema for custom serialization/deserialization.

        Creates a schema that validates and serializes importable callables
        (classes/functions) with optional full metadata including signatures.

        Parameters
        ----------
        source_type : Any
            Type annotation being processed (e.g., `Annotated[Type, Importable]`).
        handler : GetCoreSchemaHandler
            Pydantic handler for generating nested schemas.

        Returns
        -------
        core_schema.CoreSchema
            Core schema with validator and serializer functions.
        """
        expected_type = _get_expected_type(source_type)

        def validator(v: Any) -> Any:
            """Validate and deserialize importable callables."""
            obj = _deserialize_value(v)
            if (
                expected_type
                and obj is not None
                and not isinstance(obj, list | tuple)
                and (not isinstance(obj, type) or not issubclass(obj, expected_type))
            ):
                raise TypeError(
                    f"Expected {expected_type.__name__} subclass, got {obj!r}"
                )  # pragma: no cover
            return obj

        def serializer(v: Any) -> Any:
            """Serialize importable callables to JSON-compatible format."""
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
        _args = get_args(source_type)
        return _args[0] if _args else None
    return None
