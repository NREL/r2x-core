"""Tests for the declarative plugin manifest."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from r2x_core.plugin import (
    ArgumentSource,
    ArgumentSpec,
    ImplementationType,
    InvocationSpec,
    IOSlotKind,
    PluginKind,
    PluginManifest,
    PluginSpec,
)
from r2x_core.plugin_config import PluginConfig
from r2x_core.serialization import export_schemas_for_documentation, get_pydantic_schema
from r2x_core.upgrader import BaseUpgrader
from r2x_core.upgrader_utils import UpgradeType
from r2x_core.versioning import VersionReader


class SampleConfig(PluginConfig):
    scenario: str
    solve_year: int


class SampleParser:
    def __init__(self, config: SampleConfig) -> None:
        self.config = config

    def build_system(self, store: object) -> object:
        return {"store": store}


class SampleExporter:
    def __init__(self, config: SampleConfig | None = None) -> None:
        self.config = config

    def export(self, system: object) -> object:
        return system


class SampleVersionReader(VersionReader):
    def read_version(self, folder_path: Path) -> str | None:
        return "0.0.0"


class SampleUpgrader(BaseUpgrader):
    """Stub upgrader used for manifest helpers."""


@SampleUpgrader.register_step(
    name="touch-files",
    upgrade_type=UpgradeType.FILE,
    target_version="1.0.0",
)
def touch_files(path: Path) -> Path:  # pragma: no cover - simple placeholder
    return path


def sample_manifest() -> PluginManifest:
    manifest = PluginManifest(package="tests.demo")
    manifest.add(
        PluginSpec.parser(
            name="demo.parser",
            entry=SampleParser,
            config=SampleConfig,
        )
    )
    manifest.add(
        PluginSpec.upgrader(
            name="demo.upgrader",
            entry=SampleUpgrader,
            version_strategy="r2x_core.versioning:SemanticVersioningStrategy",
            version_reader="tests.test_plugin:SampleVersionReader",
        )
    )
    return manifest


def test_manifest_roundtrip():
    manifest = sample_manifest()
    payload = manifest.model_dump_json()
    restored = PluginManifest.model_validate_json(payload)
    assert restored.package == "tests.demo"
    assert len(restored.plugins) == 2
    assert restored.get_plugin("demo.parser").resources is not None


def test_manifest_group_by_kind():
    manifest = sample_manifest()
    parsers = manifest.group_by_kind(PluginKind.PARSER)
    assert len(parsers) == 1
    assert parsers[0].name == "demo.parser"


def test_resolve_entry():
    manifest = sample_manifest()
    parser_spec = manifest.get_plugin("demo.parser")
    assert parser_spec.resolve_entry() is SampleParser


def test_literal_argument_requires_default():
    with pytest.raises(ValueError):
        ArgumentSpec(name="flag", source=ArgumentSource.LITERAL)


def test_function_invocation_validation():
    with pytest.raises(ValueError):
        InvocationSpec(implementation=ImplementationType.FUNCTION, method="not-allowed")


def test_upgrade_spec_normalises_paths():
    manifest = sample_manifest()
    upgrader = manifest.get_plugin("demo.upgrader")
    assert upgrader.upgrade is not None
    assert upgrader.upgrade.steps[0].entry.endswith("touch_files")


def test_schema_generation(tmp_path):
    schema = get_pydantic_schema(PluginSpec)
    assert schema["title"] == "PluginSpec"
    output_file = tmp_path / "schemas.json"
    export_schemas_for_documentation(str(output_file))
    assert json.loads(output_file.read_text())["PluginManifest"]["title"] == "PluginManifest"


def test_export_schemas_subset(tmp_path):
    custom_models = [PluginManifest]
    with tempfile.NamedTemporaryFile(delete=False) as fh:
        fh.close()
        try:
            export_schemas_for_documentation(fh.name, custom_models)
            data = json.loads(Path(fh.name).read_text())
            assert list(data.keys()) == ["PluginManifest"]
        finally:
            os.unlink(fh.name)


def test_parser_builder_defaults():
    spec = PluginSpec.parser(name="demo.parser", entry=SampleParser, config=SampleConfig)
    assert spec.resources is not None
    assert spec.resources.store is not None
    assert spec.resources.store.required is True
    assert spec.invocation.call[0].name == "store"


def test_exporter_builder_optional_config():
    spec = PluginSpec.exporter(
        name="demo.exporter",
        entry=SampleExporter,
        config=SampleConfig,
        config_optional=True,
    )
    assert spec.kind is PluginKind.EXPORTER
    assert spec.invocation.constructor[0].optional is True
    assert spec.io.produces[0].kind is IOSlotKind.FILE


def test_function_builder_system_flags():
    spec = PluginSpec.function(name="noop", entry="tests.test_plugin:sample_manifest", returns_system=False)
    assert spec.invocation.implementation is ImplementationType.FUNCTION
    assert spec.io.produces[0].kind is IOSlotKind.VOID


def test_upgrader_builder_from_class():
    spec = PluginSpec.upgrader(
        name="upgrade",
        entry=SampleUpgrader,
        version_strategy="r2x_core.versioning:SemanticVersioningStrategy",
        version_reader="tests.test_plugin:SampleVersionReader",
    )
    assert spec.upgrade is not None
    assert spec.upgrade.steps, "Steps should be derived from upgrader class"
    assert spec.resources is not None
    assert spec.resources.store is not None
