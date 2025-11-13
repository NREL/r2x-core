"""Export all plugin manifests under ``src/*/plugins.py`` to JSON artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from r2x_core.manifest_tools import dump_manifest


def export_manifests(src_root: Path) -> None:
    plugin_files = sorted(src_root.glob("*/plugins.py"))
    if not plugin_files:
        print("::warning::No plugin manifests found under", src_root)
        return

    for plugin_file in plugin_files:
        package = plugin_file.parent.name
        module = f"{package}.plugins"
        output = plugin_file.parent / "manifest.json"
        print(f"Exporting {module} -> {output}")
        dump_manifest(module, output=output, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export manifests for all src/*/plugins.py modules.")
    parser.add_argument("--src", type=Path, default=Path("src"), help="Root folder to scan (default: src)")
    args = parser.parse_args()
    export_manifests(args.src)


if __name__ == "__main__":
    main()
