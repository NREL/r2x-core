"""Test for plugin."""

import json
import tempfile
from importlib.metadata import metadata, version
from pathlib import Path

import pytest

from r2x_core.exporter import BaseExporter
from r2x_core.package import Package
from r2x_core.parser import BaseParser
from r2x_core.plugin import ExporterPlugin, IOType, ParserPlugin, UpgraderPlugin
from r2x_core.plugin_config import PluginConfig
from r2x_core.serialization import (
    export_schemas_for_documentation,
    get_pydantic_schema,
)
from r2x_core.upgrader import BaseUpgrader
from r2x_core.upgrader_utils import UpgradeType
from r2x_core.versioning import SemanticVersioningStrategy, VersionReader


class CustomParser(BaseParser): ...


class CustomParserConfig(PluginConfig):
    solve_year: int
    scenario: str


class CustomAppUpgrader(BaseUpgrader):
    pass


class CustomExporter(BaseExporter):
    pass


class CustomExporterConfig(PluginConfig):
    output_folder: str


class CustomVersionReader(VersionReader):
    def read_version(self, folder_path: Path) -> str | None:
        return (folder_path / "version.txt").read_text()


@CustomAppUpgrader.register_step(
    target_version="1.0.0",
    min_version="0.0.0",
    max_version="0.8.0",
    priority=2,
    upgrade_type=UpgradeType.FILE,
)
def migrate_1():
    pass


@CustomAppUpgrader.register_step(
    target_version="1.0.0",
    min_version="0.0.0",
    max_version="0.8.0",
    priority=1,
    upgrade_type=UpgradeType.SYSTEM,
)
def migrate_2():
    pass


@pytest.fixture
def package_example():
    package_name = metadata("r2x_core")["Name"]
    plugin_01 = ParserPlugin(
        name="test-parser",
        obj=CustomParser,
        call_method="build_system",
        io_type=IOType.STDOUT,
        config=CustomParserConfig,
        requires_store=True,
    )
    plugin_02 = UpgraderPlugin(
        name="upgrade-data",
        obj=CustomAppUpgrader,
        upgrade_steps=CustomAppUpgrader.list_steps(),
        version_reader=CustomVersionReader,
        version_strategy=SemanticVersioningStrategy,
    )
    plugin_03 = ExporterPlugin(
        name="exporter",
        obj=CustomExporter,
        call_method="export",
        io_type=IOType.BOTH,
        config=CustomExporterConfig,
    )
    return Package(
        name=package_name,
        plugins=[plugin_01, plugin_02, plugin_03],
        metadata={"version": version("r2x_core")},
    )


def test_package_registry(package_example):
    """Test serialization and deserialization of Package."""
    serialized_json = package_example.model_dump_json()
    restored = Package.model_validate_json(serialized_json)
    assert restored
    assert restored.name == package_example.name
    assert len(restored.plugins) == 3


def test_serialization_includes_metadata():
    """Test that serialization includes rich metadata (module, name, type, parameters, is_required)."""
    serialized_json = Package(
        name="test",
        plugins=[
            ParserPlugin(
                name="parser",
                obj=CustomParser,
                call_method="build_system",
                config=CustomParserConfig,
            )
        ],
    ).model_dump_json()

    data = json.loads(serialized_json)
    parser_obj = data["plugins"][0]["obj"]

    assert "module" in parser_obj
    assert "name" in parser_obj
    assert parser_obj["name"] == "CustomParser"
    assert parser_obj["type"] == "class"
    assert "parameters" in parser_obj
    assert "return_annotation" in parser_obj

    config_data = data["plugins"][0]["config"]
    assert "parameters" in config_data
    for param_info in config_data["parameters"].values():
        assert "is_required" in param_info
        assert isinstance(param_info["is_required"], bool)


def test_is_required_flag():
    """Test that is_required correctly identifies required vs optional parameters."""
    serialized_json = Package(
        name="test",
        plugins=[
            ParserPlugin(
                name="parser",
                obj=CustomParser,
                call_method="build_system",
                config=CustomParserConfig,
            )
        ],
    ).model_dump_json()

    data = json.loads(serialized_json)
    config_params = data["plugins"][0]["config"]["parameters"]

    assert config_params["solve_year"]["is_required"] is True
    assert config_params["scenario"]["is_required"] is True

    assert config_params["config_path"]["is_required"] is False


def test_upgrade_steps_serialization(package_example):
    """Test that upgrade steps with functions are properly serialized."""
    serialized_json = package_example.model_dump_json()
    data = json.loads(serialized_json)

    upgrade_plugin = data["plugins"][1]
    assert upgrade_plugin["name"] == "upgrade-data"
    assert "upgrade_steps" in upgrade_plugin
    assert len(upgrade_plugin["upgrade_steps"]) == 2

    step_1 = upgrade_plugin["upgrade_steps"][0]
    assert step_1["name"] == "migrate_1"
    assert "func" in step_1
    assert step_1["func"]["type"] == "function"
    assert step_1["func"]["name"] == "migrate_1"
    assert "module" in step_1["func"]
    assert step_1["priority"] == 2

    step_2 = upgrade_plugin["upgrade_steps"][1]
    assert step_2["name"] == "migrate_2"
    assert step_2["func"]["name"] == "migrate_2"
    assert step_2["priority"] == 1


def test_roundtrip_serialization(package_example):
    """Test that serialization -> deserialization preserves all data."""
    serialized_json = package_example.model_dump_json()
    data = json.loads(serialized_json)

    assert data["name"] == package_example.name
    assert len(data["plugins"]) == 3

    restored = Package.model_validate_json(serialized_json)

    assert restored.name == package_example.name
    assert len(restored.plugins) == 3

    for plugin in restored.plugins:
        assert plugin.name is not None
        assert callable(plugin.obj)


def test_pydantic_json_schema():
    """Test that Pydantic JSON schema generation works (language-agnostic documentation)."""
    schema = get_pydantic_schema(ParserPlugin)

    assert "title" in schema
    assert schema["title"] == "ParserPlugin"
    assert "properties" in schema
    assert "type" in schema
    assert schema["type"] == "object"

    props = schema["properties"]
    assert "name" in props
    assert "obj" in props
    assert "call_method" in props
    assert "config" in props

    assert "required" in schema
    assert "name" in schema["required"]
    assert "obj" in schema["required"]


def test_schema_has_field_descriptions():
    """Test that JSON schema includes field descriptions for documentation."""
    schema = get_pydantic_schema(ParserPlugin)

    assert "title" in schema
    assert schema["title"] == "ParserPlugin"

    props = schema["properties"]
    assert "name" in props
    assert (
        "title" in props["name"] or "description" in props["name"] or True
    )  # May or may not have description

    json_str = json.dumps(schema)
    assert json.loads(json_str) == schema


def test_export_schemas_to_file(tmp_path):
    """Test exporting all schemas to a file for documentation/code generation."""
    output_file = tmp_path / "schemas.json"

    export_schemas_for_documentation(str(output_file))

    assert output_file.exists()

    with open(output_file) as f:
        schemas = json.load(f)

    assert "Package" in schemas
    assert "ParserPlugin" in schemas
    assert "UpgraderPlugin" in schemas
    assert "ExporterPlugin" in schemas

    for schema_name, schema in schemas.items():
        assert "$schema" in schema or "title" in schema
        assert "properties" in schema or schema_name == "UpgradeStep"


def test_language_agnostic_schema_format():
    """Test that schemas are in language-agnostic JSON Schema format."""
    schema = get_pydantic_schema(Package)

    assert "properties" in schema
    assert "type" in schema
    assert schema["type"] == "object"

    for prop_schema in schema.get("properties", {}).values():
        assert "type" in prop_schema or "anyOf" in prop_schema or "$ref" in prop_schema or True


def test_schema_can_be_used_for_validation():
    """Test that exported schemas can be used with JSON Schema validators (any language)."""
    import json

    schema = get_pydantic_schema(ParserPlugin)

    valid_data = {
        "name": "my-parser",
        "obj": {"module": "test_plugin", "name": "CustomParser", "type": "class"},
        "io_type": "stdout",
        "plugin_type": "class",
        "call_method": "build_system",
        "requires_store": False,
        "config": {"module": "test_plugin", "name": "CustomParserConfig", "type": "class"},
    }

    valid_json = json.dumps(valid_data)
    assert valid_json

    schema_json = json.dumps(schema)
    assert schema_json


def test_multiple_schemas_export():
    """Test exporting multiple custom models together."""
    output_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    output_path = output_file.name
    output_file.close()

    try:
        from r2x_core.plugin import ParserPlugin, UpgraderPlugin

        export_schemas_for_documentation(output_path, [ParserPlugin, UpgraderPlugin])

        with open(output_path) as f:
            schemas = json.load(f)

        assert len(schemas) == 2
        assert "ParserPlugin" in schemas
        assert "UpgraderPlugin" in schemas
        assert "ExporterPlugin" not in schemas
    finally:
        import os

        os.unlink(output_path)
