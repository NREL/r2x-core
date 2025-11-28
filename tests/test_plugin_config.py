"""Tests for :class:`r2x_core.plugin_config.PluginConfig` helpers."""

import json
from pathlib import Path

import pytest

from r2x_core.plugin_config import PluginConfig, PluginConfigAsset
from r2x_core.utils.overrides import override_dictionary


class SampleConfig(PluginConfig):
    """Minimal PluginConfig subclass for testing."""

    param1: str
    param2: int = 42


def _write_assets(tmp_path: Path, payloads: dict[PluginConfigAsset, object]) -> None:
    for asset, payload in payloads.items():
        (tmp_path / asset.value).write_text(json.dumps(payload))


def test_models_defaults_to_empty_tuple():
    config = SampleConfig(param1="test")
    assert config.models == ()


def test_models_accept_string():
    config = SampleConfig(param1="test", models="r2x_sienna.models")
    assert config.models == ("r2x_sienna.models",)


def test_models_accept_iterable():
    config = SampleConfig(param1="test", models=("mod.a", "mod.b"))
    assert config.models == ("mod.a", "mod.b")


def test_config_path_override(tmp_path):
    override = tmp_path / "custom"
    override.mkdir()
    config = SampleConfig(param1="test", config_path_override=override)
    assert config.config_path == override


@pytest.mark.parametrize(
    "prop, asset",
    (
        ("fmap_path", PluginConfigAsset.FILE_MAPPING),
        ("defaults_path", PluginConfigAsset.DEFAULTS),
        ("exporter_rules_path", PluginConfigAsset.EXPORTER_RULES),
        ("parser_rules_path", PluginConfigAsset.PARSER_RULES),
        ("translation_rules_path", PluginConfigAsset.TRANSLATION_RULES),
    ),
)
def test_asset_paths_follow_config_path(prop, asset, tmp_path):
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    config = SampleConfig(param1="test", config_path_override=config_dir)
    expected = config_dir / asset.value
    assert getattr(config, prop) == expected


def test_config_path_uses_existing_config_directory(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    module_file = config_dir / "module.py"
    module_file.write_text("# dummy")

    monkeypatch.setattr(
        "r2x_core.plugin_config.inspect.getfile",
        lambda cls: module_file,
    )

    config = SampleConfig(param1="test")
    assert config.config_path == config_dir


def test_config_path_appends_config_directory_when_missing(monkeypatch, tmp_path):
    module_dir = tmp_path / "module"
    module_dir.mkdir()
    module_file = module_dir / "module.py"
    module_file.write_text("# dummy")

    monkeypatch.setattr(
        "r2x_core.plugin_config.inspect.getfile",
        lambda cls: module_file,
    )

    expected = module_dir / "config"
    expected.mkdir()
    config = SampleConfig(param1="test")
    assert config.config_path == expected


def test_load_config_reads_all_assets(tmp_path):
    payloads = {
        PluginConfigAsset.FILE_MAPPING: [{"name": "data", "fpath": "file.csv"}],
        PluginConfigAsset.DEFAULTS: {"value": 1},
        PluginConfigAsset.EXPORTER_RULES: [{"step": "export"}],
        PluginConfigAsset.PARSER_RULES: [{"step": "parse"}],
        PluginConfigAsset.TRANSLATION_RULES: [{"rule": "map"}],
    }
    _write_assets(tmp_path, payloads)

    config = SampleConfig(param1="test")
    result = config.load_config(config_path=tmp_path)

    assert result == {asset.value.split(".")[0]: payload for asset, payload in payloads.items()}


def test_load_config_respects_overrides(tmp_path):
    payloads = {
        PluginConfigAsset.FILE_MAPPING: [{"name": "data", "fpath": "file.csv"}],
        PluginConfigAsset.DEFAULTS: {"value": 1, "items": ["a", "b"]},
        PluginConfigAsset.EXPORTER_RULES: [],
        PluginConfigAsset.PARSER_RULES: [],
        PluginConfigAsset.TRANSLATION_RULES: [],
    }
    _write_assets(tmp_path, payloads)

    overrides = {
        "defaults": {"value": 2, "items": ["c"]},
        "file_mapping": [{"name": "data", "fpath": "override.csv"}],
    }

    result = SampleConfig(param1="test").load_config(config_path=tmp_path, overrides=overrides)
    assert result["defaults"]["value"] == 2
    assert result["defaults"]["items"][0] == "c"
    assert result["file_mapping"][0]["fpath"] == "override.csv"


def test_load_config_missing_asset_raises(tmp_path):
    (tmp_path / PluginConfigAsset.FILE_MAPPING.value).write_text(json.dumps([]))
    with pytest.raises(FileNotFoundError):
        SampleConfig(param1="test").load_config(config_path=tmp_path)


def test_override_dictionary_merges_scalars():
    base = {"a": 1, "b": 2}
    overrides = {"a": 10}
    result = override_dictionary(base, overrides)
    assert result["a"] == 10
    assert result["b"] == 2


def test_override_dictionary_merges_lists():
    base = {"items": ["a", "b", "c"]}
    overrides = {"items": ["x", "y"]}
    result = override_dictionary(base, overrides)
    assert result["items"][0] == "x"
    assert result["items"][1] == "y"
    assert result["items"][2:] == ["c"]


def test_override_dictionary_merges_nested_dicts():
    base = {"nested": {"value": 1, "extra": 2}}
    overrides = {"nested": {"value": 10, "new": 5}}
    result = override_dictionary(base, overrides)
    assert result["nested"]["value"] == 10
    assert result["nested"]["extra"] == 2
    assert result["nested"]["new"] == 5
