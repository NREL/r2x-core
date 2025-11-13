"""Tests for the declarative plugin manifest."""

import json
import math
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
    IOSlotKind,
    PluginKind,
    PluginManifest,
    PluginSpec,
    StoreMode,
    StoreSpec,
    UpgradeStepSpec,
    _as_import_path,
    _coerce_config_spec,
    _coerce_step_specs,
    _coerce_store_spec,
    _convert_step,
    _exporter_io,
    _guess_implementation,
    _import_from_path,
    _maybe_config_argument,
    _maybe_resources,
    _maybe_store_argument,
    _parser_io,
    _upgrader_io,
)
from r2x_core.plugin_config import PluginConfig
from r2x_core.serialization import export_schemas_for_documentation, get_pydantic_schema
from r2x_core.upgrader import BaseUpgrader
from r2x_core.upgrader_utils import UpgradeStep, UpgradeType
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


def test_helper_import_path_utils():
    assert _as_import_path(None) is None
    assert _as_import_path("pkg.symbol") == "pkg.symbol"
    assert _import_from_path("math.sqrt") is math.sqrt


def test_function_builder_void_output():
    def _noop():
        return None

    spec = PluginSpec.function(name="noop", entry=_noop, takes_system=False, returns_system=False)
    assert spec.io.produces[0].kind is IOSlotKind.VOID


def test_function_builder_returns_system_by_default():
    def passthrough(system):
        return system

    spec = PluginSpec.function(name="echo", entry=passthrough)
    assert spec.io.produces[0].kind is IOSlotKind.SYSTEM


def test_manifest_helpers_error_and_resolve():
    manifest = PluginManifest(package="pkg")
    with pytest.raises(KeyError):
        manifest.get_plugin("missing")
    assert manifest.resolve_all_entries() == {}


def test_store_and_config_coercion_helpers():
    assert _coerce_store_spec(None) is None
    base_store = StoreSpec(required=False, modes=[StoreMode.FOLDER])
    assert _coerce_store_spec(base_store) is base_store
    store_spec = _coerce_store_spec(True)
    assert isinstance(store_spec, StoreSpec) and store_spec.required
    path_spec = _coerce_store_spec("inputs")
    assert path_spec.default_path == "inputs"
    with pytest.raises(TypeError):
        _coerce_store_spec(123)  # type: ignore[arg-type]

    config_spec_obj = ConfigSpec(model="tests.test_plugin:SampleConfig", required=True)
    assert _coerce_config_spec(config_spec_obj, required=False).required is False
    config_spec = _coerce_config_spec(SampleConfig, required=True)
    assert config_spec is not None and config_spec.required
    assert _coerce_config_spec(None, required=True) is None

    assert list(_maybe_config_argument(None)) == []
    assert list(_maybe_store_argument(None)) == []
    assert _maybe_resources(None, None) is None


def test_io_helper_builders():
    store_spec = StoreSpec(required=False, modes=[StoreMode.FOLDER])
    config_spec = ConfigSpec(model="tests.test_plugin:SampleConfig", required=True)
    parser_io = _parser_io(store_spec, config_spec)
    assert parser_io.consumes[0].optional is True
    exporter_io = _exporter_io(config_spec, IOSlotKind.FILE)
    assert exporter_io.produces[0].kind is IOSlotKind.FILE
    upgrader_io = _upgrader_io()
    assert upgrader_io.consumes[0].kind is IOSlotKind.STORE_FOLDER


def test_step_conversion_helpers():
    spec = UpgradeStepSpec(
        name="spec-step",
        entry="tests.test_plugin:touch_files",
        upgrade_type=UpgradeType.FILE,
    )
    result = _coerce_step_specs([spec], entry="tests.test_plugin:touch_files")
    assert result[0].name == "spec-step"

    class Dummy:
        @classmethod
        def list_steps(cls):
            return [
                UpgradeStep(
                    name="upgrade",
                    func=touch_files,
                    target_version="1.0",
                    upgrade_type=UpgradeType.FILE,
                )
            ]

    result_from_class = _coerce_step_specs(None, entry=Dummy)
    assert result_from_class and result_from_class[0].name == "upgrade"
    assert _convert_step(spec) is spec
    assert _coerce_step_specs(None, entry="math.sqrt") == []


def test_guess_implementation_variants():
    class Dummy: ...

    def fn(): ...

    assert _guess_implementation(Dummy) is ImplementationType.CLASS
    assert _guess_implementation(fn) is ImplementationType.FUNCTION
    assert _guess_implementation("module.path") is ImplementationType.CLASS
