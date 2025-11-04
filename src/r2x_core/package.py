"""Plugin package metadata and registry.

A Package represents a collection of related plugins (parsers, exporters, upgraders)
discovered from a single Python package via entry points. Packages serve as the
registry of available plugins and their metadata for the plugin discovery system.

Each Package contains:
- name: Package identifier (e.g., "r2x-reeds", "r2x-plexos")
- plugins: List of discovered/registered plugins from the package
- metadata: Arbitrary package-level metadata (version, author, etc.)

See Also
--------
:class:`~r2x_core.plugin.BasePlugin` : Individual plugin metadata.
:class:`~r2x_core.plugin.ParserPlugin` : Parser plugin type.
:class:`~r2x_core.plugin.ExporterPlugin` : Exporter plugin type.
:class:`~r2x_core.plugin.UpgraderPlugin` : Upgrader plugin type.
"""

from typing import Any

from pydantic import BaseModel, Field

from r2x_core.plugin import BasePlugin, ExporterPlugin, ParserPlugin, UpgraderPlugin


class Package(BaseModel):
    """Package containing discovered plugins and metadata.

    Represents a Python package that exports plugins via entry points or
    programmatic registration. Serves as the registry unit for plugin discovery
    and management.

    Attributes
    ----------
    name : str
        Package identifier (e.g., "r2x-reeds", "r2x-plexos", "my-custom-plugins").
        Should match the package name for clarity and consistency.
    plugins : list[ParserPlugin | ExporterPlugin | UpgraderPlugin | BasePlugin]
        Discovered plugins from this package. Can mix different plugin types.
        ParserPlugin and ExporterPlugin are most common; UpgraderPlugin for
        versioning systems; BasePlugin for function-based modifiers.
        Default is empty list.
    metadata : dict[str, Any]
        Package-level metadata (version, author, description, etc.).
        Used for reporting and plugin browser interfaces. Default is empty dict.

    Examples
    --------
    >>> parser_plugin = ParserPlugin(
    ...     name="reeds-parser",
    ...     obj=ReEDSParser,
    ...     plugin_type=PluginType.CLASS,
    ...     call_method="build_system",
    ...     config=ReEDSParserConfig,
    ...     requires_store=True,
    ... )
    >>> pkg = Package(
    ...     name="r2x-reeds",
    ...     plugins=[parser_plugin],
    ...     metadata={"version": "1.0.0", "author": "NREL"},
    ... )

    See Also
    --------
    :class:`~r2x_core.plugin.ParserPlugin` : Parser plugin metadata.
    :class:`~r2x_core.plugin.ExporterPlugin` : Exporter plugin metadata.
    :class:`~r2x_core.plugin.UpgraderPlugin` : Upgrader plugin metadata.
    """

    name: str
    plugins: list[ParserPlugin | ExporterPlugin | UpgraderPlugin | BasePlugin] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
