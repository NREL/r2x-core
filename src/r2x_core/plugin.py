"""Plugin data modeling."""

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
    """If is a class or a function."""

    CLASS = "class"
    FUNCTION = "function"


class IOType(str, Enum):
    """Type of input and output for the plugin."""

    STDIN = "stdin"
    STDOUT = "stdout"
    BOTH = "both"


class BasePlugin(BaseModel):
    """Base representation of a plugin."""

    name: str
    obj: Annotated[type | Callable[..., Any], Importable]
    io_type: IOType | None = None
    plugin_type: PluginType = PluginType.FUNCTION


class ClassPlugin(BasePlugin):
    """Plugin of type class."""

    plugin_type: PluginType = PluginType.CLASS
    call_method: str


class UpgraderPlugin(BasePlugin):
    """Plugin for upgraders."""

    plugin_type: PluginType = PluginType.CLASS
    requires_store: bool = False
    version_strategy: Annotated[type[VersionStrategy], Importable]
    version_reader: Annotated[type[VersionReader], Importable]
    upgrade_steps: list[UpgradeStep] = Field(default_factory=list)


class ParserPlugin(ClassPlugin):
    """Plugin for parsers."""

    requires_store: bool = False
    config: Annotated[type[PluginConfig] | None, Importable] = None


class ExporterPlugin(ClassPlugin):
    """Plugin for exporters."""

    config: Annotated[type[PluginConfig] | None, Importable] = None
