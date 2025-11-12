"""Declarative plugin manifest models.

The legacy plugin registry used a collection of loosely typed Pydantic models
(`Package`, `ParserPlugin`, `ExporterPlugin`, `UpgraderPlugin`) that mirrored the
runtime objects. Downstream tooling had to import Python modules to figure out
how to instantiate a plugin, whether a DataStore was required, or which inputs
and outputs were involved.

This module replaces that design with a declarative manifest that is easy to
inspect statically (AST/`ast-grep` friendly) and expressive enough for the CLI
to construct plugin instances without bespoke heuristics. Everything that a
downstream application needs to know—how to instantiate an object, which
resources to prepare, and what each plugin consumes or produces—is encoded in
plain data structures.

Key concepts
------------
* :class:`PluginManifest` - package-level registry exported by entry points
* :class:`PluginSpec` - description of a single plugin (parser/exporter/etc.)
* :class:`InvocationSpec` - instructions for constructing and calling the entry
* :class:`IOContract` - inputs/outputs exchanged with the pipeline
* :class:`ResourceSpec` - how to materialize configs and data stores
* :class:`UpgradeSpec` - declarative upgrader metadata (strategy + steps)
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from importlib import import_module
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from r2x_core.upgrader_utils import UpgradeType


def _as_import_path(value: str | Callable[..., Any] | type | None) -> str | None:
    """Normalise import targets to ``module:qualname`` strings."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    module = getattr(value, "__module__", None)
    qualname = getattr(value, "__qualname__", None)
    if not module or not qualname:  # pragma: no cover - defensive
        raise TypeError(f"Cannot derive import path from {value!r}")
    return f"{module}:{qualname}"


def _import_from_path(path: str) -> Any:
    """Import an object from ``module:attr`` or ``module.attr`` syntax."""
    module_name: str
    attr_name: str
    if ":" in path:
        module_name, attr_name = path.split(":", 1)
    else:
        module_name, attr_name = path.rsplit(".", 1)
    module = import_module(module_name)
    return getattr(module, attr_name)


class PluginKind(str, Enum):
    """High-level category for a plugin."""

    PARSER = "parser"
    EXPORTER = "exporter"
    MODIFIER = "modifier"
    UPGRADER = "upgrader"
    UTILITY = "utility"


class ImplementationType(str, Enum):
    """Whether the plugin entry point is a class or a simple function."""

    CLASS = "class"
    FUNCTION = "function"


class ArgumentSource(str, Enum):
    """Source for an invocation argument."""

    SYSTEM = "system"
    STORE = "store"
    STORE_MANIFEST = "store_manifest"
    CONFIG = "config"
    CONFIG_PATH = "config_path"
    PATH = "path"
    STDIN = "stdin"
    CONTEXT = "context"
    LITERAL = "literal"
    CUSTOM = "custom"


class IOSlotKind(str, Enum):
    """Canonical inputs/outputs handled by plugins."""

    SYSTEM = "system"
    STORE_FOLDER = "store_folder"
    STORE_MANIFEST = "store_manifest"
    STORE_INLINE = "store_inline"
    CONFIG_FILE = "config_file"
    CONFIG_INLINE = "config_inline"
    FILE = "file"
    FOLDER = "folder"
    STDIN = "stdin"
    STDOUT = "stdout"
    ARTIFACT = "artifact"
    VOID = "void"


class StoreMode(str, Enum):
    """How a plugin expects its :class:`~r2x_core.store.DataStore`."""

    FOLDER = "folder"
    MANIFEST = "manifest"
    INLINE = "inline"


class IOSlot(BaseModel):
    """Describe a single input/output slot."""

    kind: IOSlotKind
    name: str | None = None
    optional: bool = False
    description: str | None = None


class IOContract(BaseModel):
    """Describe the data flow for a plugin."""

    consumes: list[IOSlot] = Field(default_factory=list)
    produces: list[IOSlot] = Field(default_factory=list)
    description: str | None = None


class ArgumentSpec(BaseModel):
    """Describe how to source a constructor or call argument."""

    name: str
    source: ArgumentSource
    optional: bool = False
    default: Any | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _require_default_for_literal(self) -> ArgumentSpec:
        provided_fields: set[str] = getattr(self, "model_fields_set", set())
        if self.source == ArgumentSource.LITERAL and "default" not in provided_fields:
            msg = f"Argument '{self.name}' uses LITERAL source but has no default value."
            raise ValueError(msg)
        return self


class InvocationSpec(BaseModel):
    """Instructions for instantiating/calling the plugin entry."""

    implementation: ImplementationType = ImplementationType.CLASS
    method: str | None = None
    constructor: list[ArgumentSpec] = Field(default_factory=list)
    call: list[ArgumentSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_method(self) -> InvocationSpec:
        if self.implementation == ImplementationType.FUNCTION and self.method:
            msg = "Functions cannot declare a method to call."
            raise ValueError(msg)
        return self


class StoreSpec(BaseModel):
    """Describe how a CLI should build a store for the plugin."""

    required: bool = False
    modes: list[StoreMode] = Field(default_factory=list)
    default_path: str | None = None
    manifest_path: str | None = None
    description: str | None = None


class ConfigSpec(BaseModel):
    """Describe configuration requirements and helpers."""

    model: str | None = Field(default=None, description="Import path to PluginConfig subclass.")
    required: bool = False
    defaults_path: str | None = None
    file_mapping_path: str | None = None
    description: str | None = None

    @field_validator("model", mode="before")
    @classmethod
    def _normalise_model(cls, value: Any) -> Any:
        return _as_import_path(value)


class ResourceSpec(BaseModel):
    """Aggregate store/config requirements."""

    store: StoreSpec | None = None
    config: ConfigSpec | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class UpgradeStepSpec(BaseModel):
    """Declarative description of a single upgrade step."""

    name: str
    entry: str
    upgrade_type: UpgradeType
    consumes: list[IOSlot] = Field(default_factory=list)
    produces: list[IOSlot] = Field(default_factory=list)
    priority: int | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("entry", mode="before")
    @classmethod
    def _normalise_entry(cls, value: Any) -> Any:
        return _as_import_path(value)


class UpgradeSpec(BaseModel):
    """Metadata necessary to run an upgrader plugin."""

    strategy: str
    reader: str
    steps: list[UpgradeStepSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("strategy", "reader", mode="before")
    @classmethod
    def _normalise_paths(cls, value: Any) -> Any:
        return _as_import_path(value)


class PluginSpec(BaseModel):
    """Fully describe how to run a plugin."""

    name: str
    kind: PluginKind
    entry: str
    invocation: InvocationSpec = Field(default_factory=InvocationSpec)
    io: IOContract = Field(default_factory=IOContract)
    resources: ResourceSpec | None = None
    upgrade: UpgradeSpec | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("entry", mode="before")
    @classmethod
    def _normalise_entry(cls, value: Any) -> Any:
        return _as_import_path(value)

    def resolve_entry(self) -> Any:
        """Import and return the entry callable/class."""
        return _import_from_path(self.entry)


class PluginManifest(BaseModel):
    """Package-level registry of plugins."""

    package: str
    plugins: list[PluginSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_plugin(self, name: str) -> PluginSpec:
        """Return a plugin by name, raising ``KeyError`` if missing."""
        for plugin in self.plugins:
            if plugin.name == name:
                return plugin
        raise KeyError(f"Plugin '{name}' not found in manifest '{self.package}'.")

    def group_by_kind(self, kind: PluginKind) -> list[PluginSpec]:
        """Return plugins that match a given :class:`PluginKind`."""
        return [plugin for plugin in self.plugins if plugin.kind == kind]

    def resolve_all_entries(self) -> dict[str, Any]:
        """Import every plugin entry and return a mapping."""
        return {plugin.name: plugin.resolve_entry() for plugin in self.plugins}
