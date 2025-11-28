"""Tests for shared context objects."""

from __future__ import annotations

import pytest

from r2x_core import Context, ExporterContext, ParserContext, PluginConfig, System


def test_context_with_updates_preserves_original():
    """Context.with_updates returns a new instance."""
    config = PluginConfig(models=())
    ctx = Context(config=config, metadata={"stage": "init"})

    updated = ctx.with_updates(metadata={"stage": "build"})

    assert ctx.metadata["stage"] == "init"
    assert updated.metadata["stage"] == "build"
    assert updated.config is config


def test_parser_context_defaults_and_frozen():
    """ParserContext exposes parser-specific flags and is immutable."""
    system = System(name="parser")
    ctx = ParserContext(config=PluginConfig(models=()), system=system)

    assert ctx.system is system
    assert ctx.skip_validation is False
    assert ctx.auto_add_composed_components is True

    with pytest.raises(AttributeError):
        ctx.system = None


def test_exporter_context_holds_system_and_metadata():
    """ExporterContext stores system reference and metadata."""
    system = System(name="export")
    ctx = ExporterContext(config=PluginConfig(models=()), system=system, metadata={"mode": "full"})

    assert ctx.system is system
    assert ctx.metadata["mode"] == "full"
