"""Plugin metadata and configuration models.

This module defines the data models representing different plugin types and their
configurations. Plugins are discovered via entry points and instantiated based on
their metadata (class vs function, I/O patterns, configuration requirements).

Plugin types:
- **ClassPlugin**: Class-based plugins (parsers, exporters, modifiers).
- **FunctionPlugin**: Function-based system modifiers.
- **UpgraderPlugin**: Versioning/upgrade plugins with version strategies and steps.
- **ParserPlugin**: Parser plugins reading model data into power systems.
- **ExporterPlugin**: Exporter plugins writing systems to various formats.

All plugins are Pydantic models with serializable fields using the Importable
annotation to handle class/function references as strings (for config portability).

See Also
--------
:class:`~r2x_core.plugin_config.PluginConfig` : Plugin configuration base class.
:class:`~r2x_core.parser.BaseParser` : Parser plugin base class.
:class:`~r2x_core.exporter.BaseExporter` : Exporter plugin base class.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field

from r2x_core.plugin_config import PluginConfig
from r2x_core.serialization import Importable
from r2x_core.upgrader_utils import UpgradeStep
from r2x_core.versioning import VersionReader, VersionStrategy


class PluginType(str, Enum):
    """Whether the plugin is implemented as a class or function.

    Attributes
    ----------
    CLASS : str
        Plugin is a class that inherits from a base plugin (e.g., BaseParser).
        Class plugins must implement required abstract methods and support configuration.
    FUNCTION : str
        Plugin is a function that transforms data. Functions are typically used
        for simple system modifications without state.
    """

    CLASS = "class"
    FUNCTION = "function"


class IOType(str, Enum):
    """Plugin I/O pattern for data flow in pipelines.

    Attributes
    ----------
    STDIN : str
        Plugin reads input from standard input (e.g., parser plugins).
    STDOUT : str
        Plugin writes output to standard output (e.g., exporter plugins).
    BOTH : str
        Plugin reads from stdin and writes to stdout (e.g., system modifiers).
    """

    STDIN = "stdin"
    STDOUT = "stdout"
    BOTH = "both"


class BasePlugin(BaseModel):
    """Base representation of a plugin.

    Contains metadata about a plugin discovered via entry points or registered
    programmatically. All class/function references use the Importable annotation
    to serialize as module paths (e.g., "my_package.MyClass").

    Attributes
    ----------
    name : str
        Plugin display name (e.g., "reeds-parser", "plexos-exporter").
    obj : type | Callable
        The actual plugin class or function. Importable fields allow serialization
        as "module:Name" strings for portability across environments.
    io_type : IOType | None
        Data flow pattern (STDIN, STDOUT, BOTH). None for non-pipeline plugins.
        Default is None.
    plugin_type : PluginType
        Whether plugin is CLASS or FUNCTION. Default is FUNCTION.

    See Also
    --------
    :class:`ClassPlugin` : Plugin wrapping a class with call_method.
    :class:`UpgraderPlugin` : Plugin with versioning and upgrade steps.
    :class:`ParserPlugin` : Parser-specific plugin metadata.
    """

    name: str
    obj: Annotated[type | Callable[..., Any], Importable]
    io_type: IOType | None = None
    plugin_type: PluginType = PluginType.FUNCTION


class ClassPlugin(BasePlugin):
    """Class-based plugin with a designated entry point method.

    Class plugins inherit from base classes (BaseParser, BaseExporter) and require
    specification of which method serves as the plugin entry point.

    Attributes
    ----------
    plugin_type : PluginType
        Always PluginType.CLASS for class-based plugins.
    call_method : str
        Name of the method to call when invoking the plugin.
        Examples: "build_system" for parsers, "export" for exporters.

    See Also
    --------
    :class:`ParserPlugin` : Class plugin specialized for parsers.
    :class:`ExporterPlugin` : Class plugin specialized for exporters.
    """

    plugin_type: PluginType = PluginType.CLASS
    call_method: str


class UpgraderPlugin(BasePlugin):
    """Plugin for managing data structure versioning and upgrades.

    Upgrader plugins handle version detection and migration of data structures
    when schema or format changes occur. They define the versioning strategy
    (how to detect versions) and ordered steps to apply for each version transition.

    Attributes
    ----------
    plugin_type : PluginType
        Always PluginType.CLASS for upgrader plugins.
    requires_store : bool
        Whether the upgrader requires a DataStore for operation. Default is False.
    version_strategy : type[VersionStrategy]
        Strategy class for determining current data version (e.g., file timestamps,
        git tags, embedded version markers). Importable field.
    version_reader : type[VersionReader]
        Strategy class for reading version information from data objects.
        Importable field.
    upgrade_steps : list[UpgradeStep]
        Ordered list of upgrade transformations to apply. Each step transforms
        data from one version to the next. Applied sequentially based on detected
        version. Default is empty list.

    See Also
    --------
    :class:`~r2x_core.versioning.VersionStrategy` : Base class for version detection.
    :class:`~r2x_core.versioning.VersionReader` : Base class for reading versions.
    :class:`~r2x_core.upgrader_utils.UpgradeStep` : Individual upgrade transformation.
    """

    plugin_type: PluginType = PluginType.CLASS
    requires_store: bool = False
    version_strategy: Annotated[type[VersionStrategy], Importable]
    version_reader: Annotated[type[VersionReader], Importable]
    upgrade_steps: list[UpgradeStep] = Field(default_factory=list)


class ParserPlugin(ClassPlugin):
    """Parser plugin for reading model data into power systems.

    Parser plugins read files or other sources and construct infrasys System objects.
    They typically inherit from BaseParser and implement abstract methods:
    build_system_components(), build_time_series(), and validate_inputs().

    Attributes
    ----------
    requires_store : bool
        Whether parser requires a DataStore for operation. Default is False.
        Parsers typically require a store for accessing multiple input files.
    config : type[PluginConfig] | None
        Configuration class for the parser (e.g., ReEDSParserConfig).
        Allows parsers to accept structured, validated configuration. None means
        parser doesn't accept configuration beyond DataStore. Importable field.

    See Also
    --------
    :class:`~r2x_core.parser.BaseParser` : Base class for all parsers.
    :class:`~r2x_core.plugin_config.PluginConfig` : Configuration base class.
    """

    requires_store: bool = False
    config: Annotated[type[PluginConfig] | None, Importable] = None


class ExporterPlugin(ClassPlugin):
    """Exporter plugin for writing power systems to various formats.

    Exporter plugins write infrasys System objects to files or other outputs
    (CSV, JSON, XML, HDF5, etc.). They typically inherit from BaseExporter
    and implement abstract methods: export() and export_time_series().

    Attributes
    ----------
    config : type[PluginConfig] | None
        Configuration class for the exporter (e.g., PlexosExporterConfig).
        Allows exporters to accept structured, validated configuration. None means
        exporter doesn't accept configuration beyond System and output folder.
        Importable field.

    See Also
    --------
    :class:`~r2x_core.exporter.BaseExporter` : Base class for all exporters.
    :class:`~r2x_core.plugin_config.PluginConfig` : Configuration base class.
    """

    config: Annotated[type[PluginConfig] | None, Importable] = None
