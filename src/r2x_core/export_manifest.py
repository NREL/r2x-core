"""CLI utility to export plugin manifests as JSON artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from .manifest_tools import dump_manifest


def build_arg_parser() -> argparse.ArgumentParser:
    """Return argument parser for export CLI."""
    parser = argparse.ArgumentParser(description="Export a PluginManifest to JSON.")
    parser.add_argument(
        "--module",
        required=True,
        help="Python module containing the manifest (e.g., my_package.plugins).",
    )
    parser.add_argument(
        "--attribute",
        default="manifest",
        help="Attribute name holding the manifest (default: manifest).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("plugins.json"),
        help="Destination JSON file (default: plugins.json).",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Write JSON without indentation (default is pretty printed).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for manifest export."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    indent = None if args.compact else 2
    path = dump_manifest(
        args.module,
        attribute=args.attribute,
        output=args.output,
        indent=indent,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
