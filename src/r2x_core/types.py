"""Helpful types."""

from typing import TypeAlias

JSONType: TypeAlias = dict[str, "JSONType"] | list["JSONType"]
