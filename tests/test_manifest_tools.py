"""Tests for manifest export utilities."""

import json
import os
import subprocess
import sys
from pathlib import Path

from r2x_core.manifest_tools import dump_manifest, load_manifest_from_module
from r2x_core.plugin import (
    PluginManifest,
)


def create_temp_manifest(tmp_path: Path) -> tuple[str, Path]:
    pkg_dir = tmp_path / "dummy_pkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")

    manifest_code = """
from r2x_core.plugin import PluginManifest, PluginSpec, PluginKind, InvocationSpec, ArgumentSpec, ArgumentSource, IOContract, IOSlot, IOSlotKind

manifest = PluginManifest(
    package="dummy_pkg",
    plugins=[
        PluginSpec(
            name="dummy.parser",
            kind=PluginKind.PARSER,
            entry="dummy_pkg.parser:Parser",
            invocation=InvocationSpec(
                call=[ArgumentSpec(name="store", source=ArgumentSource.STORE)]
            ),
            io=IOContract(
                consumes=[IOSlot(kind=IOSlotKind.STORE_FOLDER)],
                produces=[IOSlot(kind=IOSlotKind.SYSTEM)],
            ),
        )
    ],
)
"""
    manifest_module = pkg_dir / "plugins.py"
    manifest_module.write_text(manifest_code)
    return "dummy_pkg.plugins", pkg_dir


def test_load_manifest_from_module(tmp_path, monkeypatch):
    module_path, _pkg_dir = create_temp_manifest(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    manifest = load_manifest_from_module(module_path)
    assert isinstance(manifest, PluginManifest)
    assert manifest.package == "dummy_pkg"
    assert manifest.plugins[0].name == "dummy.parser"


def test_dump_manifest_writes_json(tmp_path, monkeypatch):
    module_path, _pkg_dir = create_temp_manifest(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    output = tmp_path / "export" / "plugins.json"
    path = dump_manifest(module_path, output=output, indent=None)
    data = json.loads(path.read_text())

    assert data["package"] == "dummy_pkg"
    assert data["plugins"][0]["name"] == "dummy.parser"


def test_cli_export(tmp_path, monkeypatch):
    module_path, _pkg_dir = create_temp_manifest(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    output = tmp_path / "manifest.json"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "r2x_core.export_manifest",
            "--module",
            module_path,
            "--output",
            str(output),
            "--compact",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert output.exists()
