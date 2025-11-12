"""Utilities for loading and exporting plugin manifests."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

from loguru import logger

from .plugin import PluginManifest


def load_manifest_from_module(module_path: str, attribute: str = "manifest") -> PluginManifest:
    """Load a :class:`PluginManifest` from a Python module attribute.

    Parameters
    ----------
    module_path : str
        Dotted module path (e.g., ``"my_package.plugins"``).
    attribute : str, optional
        Attribute name that holds the manifest. Defaults to ``"manifest"``.
    """
    module = import_module(module_path)
    if not hasattr(module, attribute):
        msg = f"Module '{module_path}' does not define attribute '{attribute}'."
        raise AttributeError(msg)

    obj = getattr(module, attribute)
    if isinstance(obj, PluginManifest):
        return obj
    if isinstance(obj, dict):
        return PluginManifest.model_validate(obj)

    msg = f"Attribute '{attribute}' on module '{module_path}' is not a PluginManifest."
    raise TypeError(msg)


def dump_manifest(
    module_path: str,
    *,
    attribute: str = "manifest",
    output: str | Path | None = None,
    indent: int | None = 2,
) -> Path:
    """Export a manifest to JSON for downstream tooling."""
    manifest = load_manifest_from_module(module_path, attribute)
    payload = manifest.model_dump(mode="json")

    target_path = Path(output) if output else Path("plugins.json")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Writing manifest for %s to %s", module_path, target_path)
    with target_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=indent)

    return target_path
