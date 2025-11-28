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
* Helper constructors (:meth:`PluginSpec.parser`, etc.) for plugin authors
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from importlib import import_module
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import ArgumentSource, ImplementationType, IOSlotKind, PluginKind, StoreMode
from .upgrader_utils import UpgradeStep, UpgradeType


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
        """Ensure literal arguments declare a default value."""
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
        """Validate that functions do not specify a call method."""
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
        """Normalise config model references to import paths."""
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
        """Normalise upgrade step entry to import path."""
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
        """Normalise strategy/reader paths."""
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
        """Normalise plugin entry path."""
        return _as_import_path(value)

    def resolve_entry(self) -> Any:
        """Import and return the entry callable/class."""
        return _import_from_path(self.entry)

    @classmethod
    def parser(
        cls,
        *,
        name: str,
        entry: str | type,
        config: ConfigSpec | type | str | None = None,
        config_optional: bool = False,
        store: StoreSpec | bool | str | None = True,
        method: str = "build_system",
        description: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> PluginSpec:
        """Create a parser plugin with sensible defaults."""
        store_spec = _coerce_store_spec(store)
        config_spec = _coerce_config_spec(config, required=not config_optional)
        invocation = InvocationSpec(
            method=method,
            constructor=list(_maybe_config_argument(config_spec)),
            call=list(_maybe_store_argument(store_spec)),
        )
        io = _parser_io(store_spec, config_spec)
        resources = _maybe_resources(store_spec, config_spec)
        return cls(
            name=name,
            kind=PluginKind.PARSER,
            entry=_as_import_path(entry),
            invocation=invocation,
            io=io,
            resources=resources,
            description=description,
            tags=_normalize_tags(tags),
        )

    @classmethod
    def exporter(
        cls,
        *,
        name: str,
        entry: str | type,
        config: ConfigSpec | type | str | None = None,
        config_optional: bool = False,
        method: str = "export",
        output_kind: IOSlotKind = IOSlotKind.FILE,
        description: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> PluginSpec:
        """Create an exporter plugin with default IO contract."""
        config_spec = _coerce_config_spec(config, required=not config_optional)
        invocation = InvocationSpec(
            method=method,
            constructor=list(_maybe_config_argument(config_spec)),
            call=[
                ArgumentSpec(name="system", source=ArgumentSource.SYSTEM),
            ],
        )
        io = _exporter_io(config_spec, output_kind)
        resources = _maybe_resources(None, config_spec)
        return cls(
            name=name,
            kind=PluginKind.EXPORTER,
            entry=_as_import_path(entry),
            invocation=invocation,
            io=io,
            resources=resources,
            description=description,
            tags=_normalize_tags(tags),
        )

    @classmethod
    def function(
        cls,
        *,
        name: str,
        entry: str | Callable[..., Any],
        takes_system: bool = True,
        returns_system: bool = True,
        description: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> PluginSpec:
        """Create a function-based modifier plugin."""
        call = []
        consumes = []
        produces = []
        if takes_system:
            call.append(ArgumentSpec(name="system", source=ArgumentSource.SYSTEM))
            consumes.append(IOSlot(kind=IOSlotKind.SYSTEM))
        if returns_system:
            produces.append(IOSlot(kind=IOSlotKind.SYSTEM))
        io = IOContract(consumes=consumes, produces=produces or [IOSlot(kind=IOSlotKind.VOID)])
        invocation = InvocationSpec(
            implementation=ImplementationType.FUNCTION,
            call=call,
        )
        return cls(
            name=name,
            kind=PluginKind.MODIFIER,
            entry=_as_import_path(entry),
            invocation=invocation,
            io=io,
            description=description,
            tags=_normalize_tags(tags),
        )

    @classmethod
    def upgrader(
        cls,
        *,
        name: str,
        entry: str | type | Callable[..., Any],
        version_strategy: str | type,
        version_reader: str | type,
        steps: Sequence[UpgradeStepSpec | UpgradeStep] | None = None,
        implementation: ImplementationType | None = None,
        description: str | None = None,
        tags: Sequence[str] | None = None,
    ) -> PluginSpec:
        """Create an upgrader plugin that operates on data folders."""
        step_specs = _coerce_step_specs(steps, entry)
        upgrade = UpgradeSpec(
            strategy=_as_import_path(version_strategy),
            reader=_as_import_path(version_reader),
            steps=step_specs,
        )
        store_spec = StoreSpec(required=True, modes=[StoreMode.FOLDER])
        invocation = InvocationSpec(
            implementation=implementation or _guess_implementation(entry),
        )
        return cls(
            name=name,
            kind=PluginKind.UPGRADER,
            entry=_as_import_path(entry),
            invocation=invocation,
            io=_upgrader_io(),
            resources=ResourceSpec(store=store_spec),
            upgrade=upgrade,
            description=description,
            tags=_normalize_tags(tags),
        )


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

    def add(self, plugin: PluginSpec) -> PluginSpec:
        """Append a plugin to the manifest (builder convenience)."""
        self.plugins.append(plugin)
        return plugin


def _normalize_tags(tags: Sequence[str] | None) -> list[str]:
    """Return a list of tags or an empty list when none provided."""
    return list(tags) if tags else []


def _coerce_store_spec(
    store: StoreSpec | bool | str | None,
) -> StoreSpec | None:
    """Convert loose store specifications into a StoreSpec instance."""
    if store is None:
        return None
    if isinstance(store, StoreSpec):
        return store
    if isinstance(store, bool):
        return StoreSpec(required=store, modes=[StoreMode.FOLDER])
    if isinstance(store, str):
        return StoreSpec(required=True, modes=[StoreMode.FOLDER], default_path=store)
    raise TypeError(f"Unsupported store specification: {store!r}")


def _coerce_config_spec(
    config: ConfigSpec | type | str | None,
    *,
    required: bool,
) -> ConfigSpec | None:
    """Convert loose config specifications into a ConfigSpec instance."""
    if config is None:
        return None
    if isinstance(config, ConfigSpec):
        return config.model_copy(update={"required": required})
    return ConfigSpec(model=_as_import_path(config), required=required)


def _maybe_config_argument(config: ConfigSpec | None) -> Iterable[ArgumentSpec]:
    """Yield an ArgumentSpec for config when required by the plugin."""
    if config is None:
        return
    yield ArgumentSpec(
        name="config",
        source=ArgumentSource.CONFIG,
        optional=not config.required,
    )


def _maybe_store_argument(store: StoreSpec | None) -> Iterable[ArgumentSpec]:
    """Yield an ArgumentSpec for the store when required by the plugin."""
    if store is None:
        return
    yield ArgumentSpec(
        name="store",
        source=ArgumentSource.STORE,
        optional=not store.required,
    )


def _maybe_resources(
    store: StoreSpec | None,
    config: ConfigSpec | None,
) -> ResourceSpec | None:
    """Create a ResourceSpec when at least one resource is declared."""
    if store is None and config is None:
        return None
    return ResourceSpec(store=store, config=config)


def _parser_io(store: StoreSpec | None, config: ConfigSpec | None) -> IOContract:
    """Build the IO contract for parser plugins."""
    consumes: list[IOSlot] = []
    if store is not None:
        consumes.append(IOSlot(kind=IOSlotKind.STORE_FOLDER, optional=not store.required))
    if config is not None:
        consumes.append(IOSlot(kind=IOSlotKind.CONFIG_FILE, optional=not config.required))
    produces = [IOSlot(kind=IOSlotKind.SYSTEM)]
    return IOContract(consumes=consumes, produces=produces)


def _exporter_io(config: ConfigSpec | None, output_kind: IOSlotKind) -> IOContract:
    """Build the IO contract for exporter plugins."""
    consumes = [IOSlot(kind=IOSlotKind.SYSTEM)]
    if config is not None:
        consumes.append(IOSlot(kind=IOSlotKind.CONFIG_FILE, optional=not config.required))
    produces = [IOSlot(kind=output_kind)]
    return IOContract(consumes=consumes, produces=produces)


def _upgrader_io() -> IOContract:
    """Return the IO contract shared by upgrader plugins."""
    return IOContract(
        consumes=[IOSlot(kind=IOSlotKind.STORE_FOLDER)],
        produces=[IOSlot(kind=IOSlotKind.STORE_FOLDER)],
    )


def _coerce_step_specs(
    steps: Sequence[UpgradeStepSpec | UpgradeStep] | None,
    entry: str | type | Callable[..., Any],
) -> list[UpgradeStepSpec]:
    """Convert UpgradeStep objects to UpgradeStepSpec instances."""
    if steps:
        return [_convert_step(step) for step in steps]
    if isinstance(entry, type) and hasattr(entry, "list_steps"):
        raw_steps = entry.list_steps()
        return [_convert_step(step) for step in raw_steps]
    return []


def _convert_step(step: UpgradeStepSpec | UpgradeStep) -> UpgradeStepSpec:
    """Adapt UpgradeStep inputs into spec objects."""
    if isinstance(step, UpgradeStepSpec):
        return step
    return UpgradeStepSpec(
        name=step.name,
        entry=_as_import_path(step.func),
        upgrade_type=step.upgrade_type,
        priority=step.priority,
        metadata={
            "target_version": step.target_version,
            "min_version": step.min_version,
            "max_version": step.max_version,
        },
    )


def _guess_implementation(entry: str | type | Callable[..., Any]) -> ImplementationType:
    """Guess implementation type based on entry object."""
    if isinstance(entry, type):
        return ImplementationType.CLASS
    if callable(entry):
        return ImplementationType.FUNCTION
    return ImplementationType.CLASS
