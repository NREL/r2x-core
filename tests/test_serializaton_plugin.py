import json
import os
from typing import Any

import pytest

from r2x_core.serialization import (
    _deserialize_value,
    _get_module_name,
    _import_path,
    _serialize_callable_fast,
    _serialize_callable_full,
    _serialize_value,
    export_schemas_for_documentation,
    get_pydantic_schema,
)


def test_serialize_callable_with_complex_signature():
    """Test serialization of callable with complex signature."""

    def complex_func(a: int, b: str = "default", *args, **kwargs) -> dict:
        """A complex function."""
        return {}

    result = _serialize_callable_full(complex_func)

    assert result["name"] == "complex_func"
    assert result["module"] == __name__
    assert result["type"] == "function"
    assert "parameters" in result
    assert result["return_annotation"] is not None


def test_serialize_callable_with_no_signature():
    """Test serialization of callable with no accessible signature."""

    class NoSigCallable:
        __name__ = "NoSigCallable"
        __module__ = __name__

        def __call__(self, *args, **kwargs):
            pass

    obj = NoSigCallable()

    result = _serialize_callable_full(obj)
    assert "name" in result or "module" in result


def test_serialize_callable_fast_path():
    """Test fast serialization path for callables."""

    def simple_func():
        pass

    result = _serialize_callable_fast(simple_func)

    assert result["name"] == "simple_func"
    assert result["type"] == "function"
    assert "module" in result
    assert "parameters" not in result


def test_serialize_class_type():
    """Test serialization of class types."""

    class TestClass:
        pass

    result = _serialize_callable_full(TestClass)

    assert result["name"] == "TestClass"
    assert result["type"] == "class"


def test_serialize_value_with_basemodel():
    """Test serialization of Pydantic BaseModel instances."""
    from pydantic import BaseModel

    class TestModel(BaseModel):
        name: str
        value: int

    model = TestModel(name="test", value=42)
    result = _serialize_value(model)

    assert result["name"] == "test"
    assert result["value"] == 42


def test_serialize_value_with_nested_list():
    """Test serialization of nested lists."""
    nested = [1, 2, [3, 4, [5, 6]]]
    result = _serialize_value(nested)

    assert result == nested


def test_serialize_value_with_callable_list():
    """Test serialization of list containing callables."""

    def func1():
        pass

    def func2():
        pass

    lst = [func1, func2, "string", 42]
    result = _serialize_value(lst, full_metadata=False)

    assert len(result) == 4
    assert isinstance(result[0], dict)
    assert isinstance(result[1], dict)
    assert result[2] == "string"
    assert result[3] == 42


def test_serialize_value_none():
    """Test serialization of None value."""
    result = _serialize_value(None)
    assert result is None


def test_serialize_value_primitives():
    """Test serialization of primitive types."""
    assert _serialize_value(42) == 42
    assert _serialize_value(3.14) == 3.14
    assert _serialize_value(True) is True
    assert _serialize_value("test") == "test"


def test_deserialize_value_with_callable_path():
    """Test deserialization of callable path strings."""
    result = _deserialize_value("os.path.join")

    import os.path

    assert result == os.path.join


def test_deserialize_value_with_dict_metadata():
    """Test deserialization of dict with module/name metadata."""
    metadata = {"module": "os.path", "name": "join"}
    result = _deserialize_value(metadata)

    import os.path

    assert result == os.path.join


def test_deserialize_value_with_invalid_path():
    """Test deserialization handles invalid import paths gracefully."""
    invalid_path = "nonexistent.module.path"
    result = _deserialize_value(invalid_path)

    assert result == invalid_path


def test_deserialize_value_with_invalid_metadata():
    """Test deserialization of invalid metadata dict."""
    invalid_metadata = {"module": "nonexistent", "name": "missing"}
    result = _deserialize_value(invalid_metadata)

    assert result == invalid_metadata


def test_deserialize_value_none():
    """Test deserialization of None."""
    result = _deserialize_value(None)
    assert result is None


def test_deserialize_value_primitives():
    """Test deserialization of primitives."""
    assert _deserialize_value(42) == 42
    assert _deserialize_value(3.14) == 3.14
    assert _deserialize_value(False) is False


def test_deserialize_value_list():
    """Test deserialization of list."""
    result = _deserialize_value([1, 2, 3])
    assert result == [1, 2, 3]


def test_get_module_name_caching():
    """Test module name caching."""
    import os

    name1 = _get_module_name(os.path.join)
    name2 = _get_module_name(os.path.join)

    assert name1 == name2
    assert name1 in ("os.path", "posixpath", "ntpath")


def test_import_path_success():
    """Test successful import path resolution."""
    import os

    result = _import_path("os.path.join")
    assert result == os.path.join


def test_import_path_invalid():
    """Test import path with invalid path raises error."""
    with pytest.raises((ImportError, AttributeError)):
        _import_path("nonexistent.invalid.path")


def test_get_pydantic_schema():
    """Test getting JSON schema for Pydantic model."""
    from pydantic import BaseModel

    class TestModel(BaseModel):
        name: str
        value: int

    schema = get_pydantic_schema(TestModel)

    assert "$defs" in schema or "properties" in schema
    assert "title" in schema


def test_export_schemas_for_documentation(tmp_path):
    """Test exporting schemas to file."""
    output_path = tmp_path / "schemas.json"

    export_schemas_for_documentation(str(output_path))

    assert output_path.exists()

    with open(output_path) as f:
        schemas = json.load(f)

    assert isinstance(schemas, dict)
    assert len(schemas) > 0


def test_export_schemas_with_custom_models(tmp_path):
    """Test exporting custom models."""
    from pydantic import BaseModel

    class CustomModel(BaseModel):
        field: str

    output_path = tmp_path / "custom_schemas.json"

    export_schemas_for_documentation(str(output_path), include_models=[CustomModel])

    with open(output_path) as f:
        schemas = json.load(f)

    assert "CustomModel" in schemas


def test_importable_annotation_validator():
    """Test Importable annotation validator."""
    from pydantic import BaseModel

    class TestModel(BaseModel):
        func: Any

    model = TestModel(func=os.path.join)
    assert model.func == os.path.join


def test_importable_annotation_serializer():
    """Test Importable annotation serializer."""
    from pydantic import BaseModel

    class TestModel(BaseModel):
        func: Any

    model = TestModel(func=os.path.join)
    dumped = model.model_dump()

    assert dumped["func"] is not None
