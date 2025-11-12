"""Tests for the declarative plugin manifest."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from r2x_core.plugin import (
    ArgumentSource,
    ArgumentSpec,
    ConfigSpec,
    ImplementationType,
    InvocationSpec,
    IOContract,
    IOSlot,
    IOSlotKind,
    PluginKind,
    PluginManifest,
    PluginSpec,
    ResourceSpec,
    StoreMode,
    StoreSpec,
    UpgradeSpec,
    UpgradeStepSpec,
)
from r2x_core.plugin_config import PluginConfig
from r2x_core.serialization import export_schemas_for_documentation, get_pydantic_schema
from r2x_core.upgrader_utils import UpgradeType


class SampleConfig(PluginConfig):
    scenario: str
    solve_year: int


class SampleParser:
    def __init__(self, config: SampleConfig) -> None:
        self.config = config

    def build_system(self, store: object) -> object:
        return {"store": store}


def upgrade_filesystem(path: Path) -> None:  # pragma: no cover - simple placeholder
    path.touch()


def sample_manifest() -> PluginManifest:
    parser_plugin = PluginSpec(
        name="demo.parser",
        kind=PluginKind.PARSER,
        entry="tests.test_plugin:SampleParser",
        invocation=InvocationSpec(
            method="build_system",
            constructor=[ArgumentSpec(name="config", source=ArgumentSource.CONFIG)],
            call=[ArgumentSpec(name="store", source=ArgumentSource.STORE)],
        ),
        io=IOContract(
            consumes=[
                IOSlot(kind=IOSlotKind.STORE_FOLDER, description="Input data folder"),
                IOSlot(kind=IOSlotKind.CONFIG_FILE, optional=True),
            ],
            produces=[IOSlot(kind=IOSlotKind.SYSTEM)],
        ),
        resources=ResourceSpec(
            store=StoreSpec(required=True, modes=[StoreMode.FOLDER], default_path="./data"),
            config=ConfigSpec(
                model="tests.test_plugin:SampleConfig",
                required=True,
                defaults_path="config/defaults.json",
            ),
        ),
    )

    upgrader_plugin = PluginSpec(
        name="demo.upgrader",
        kind=PluginKind.UPGRADER,
        entry="tests.test_plugin:SampleParser",
        invocation=InvocationSpec(
            implementation=ImplementationType.CLASS,
            constructor=[ArgumentSpec(name="config", source=ArgumentSource.CONFIG, optional=True)],
        ),
        io=IOContract(
            consumes=[IOSlot(kind=IOSlotKind.STORE_FOLDER)],
            produces=[IOSlot(kind=IOSlotKind.STORE_FOLDER)],
            description="Transforms on-disk inputs in-place.",
        ),
        upgrade=UpgradeSpec(
            strategy="r2x_core.versioning:SemanticVersioningStrategy",
            reader="tests.test_plugin:SampleParser",
            steps=[
                UpgradeStepSpec(
                    name="touch-files",
                    entry="tests.test_plugin:upgrade_filesystem",
                    upgrade_type=UpgradeType.FILE,
                    consumes=[IOSlot(kind=IOSlotKind.FOLDER)],
                    produces=[IOSlot(kind=IOSlotKind.FOLDER)],
                    priority=10,
                )
            ],
        ),
    )

    return PluginManifest(package="tests.demo", plugins=[parser_plugin, upgrader_plugin])


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
    assert upgrader.upgrade.steps[0].entry == "tests.test_plugin:upgrade_filesystem"


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
