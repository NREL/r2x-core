"""Helpful types."""

from typing import Any, TypeAlias

JSONType: TypeAlias = dict[str, "JSONType"] | list["JSONType"]
JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | dict[str, Any] | list[Any]
