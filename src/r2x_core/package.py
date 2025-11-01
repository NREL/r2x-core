"""Package data model."""

from typing import Any

from pydantic import BaseModel, Field

from r2x_core.plugin import ExporterPlugin, ParserPlugin, UpgraderPlugin


class Package(BaseModel):
    """Package registry."""

    name: str
    plugins: list[ParserPlugin | ExporterPlugin | UpgraderPlugin] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
