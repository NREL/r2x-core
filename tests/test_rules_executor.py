"""Tests for the translation rule executor helpers."""

import pytest
from fixtures.context import FIXTURE_MODEL_MODULES
from fixtures.source_system import BusComponent, BusGeographicInfo

from r2x_core import (
    PluginConfig,
    Rule,
    System,
    TranslationContext,
    apply_rules_to_context,
    apply_single_rule,
)
from r2x_core.rules_executor import _attach_component


def _build_context(
    *,
    rules: list[Rule],
    source_system: System | None = None,
    target_system: System | None = None,
) -> TranslationContext:
    """Helper to build a translation context for executor tests."""
    source_system = source_system or System(name="executor-source")
    target_system = target_system or System(name="executor-target")
    return TranslationContext(
        source_system=source_system,
        target_system=target_system,
        config=PluginConfig(models=FIXTURE_MODEL_MODULES),
        rules=rules,
    )


def test_apply_rules_rejects_duplicate_rule_names(source_system, target_system):
    """Duplicate rule names trigger sorting errors before execution."""
    rule_a = Rule(
        source_type="BusComponent",
        target_type="NodeComponent",
        version=1,
        field_map={"name": "name"},
        name="dup",
    )
    rule_b = Rule(
        source_type="BusComponent",
        target_type="CircuitComponent",
        version=1,
        field_map={"name": "name"},
        name="dup",
    )

    context = _build_context(
        rules=[rule_a, rule_b],
        source_system=source_system,
        target_system=target_system,
    )

    with pytest.raises(ValueError, match="Duplicate rule name"):
        apply_rules_to_context(context)


def test_apply_rules_detects_missing_dependency(source_system, target_system):
    """Rules depending on unknown names error out."""
    dependent = Rule(
        source_type="BusComponent",
        target_type="NodeComponent",
        version=1,
        field_map={"name": "name"},
        name="dependent",
        depends_on=["missing"],
    )
    context = _build_context(
        rules=[dependent],
        source_system=source_system,
        target_system=target_system,
    )

    with pytest.raises(ValueError, match="depends on unknown rule"):
        apply_rules_to_context(context)


def test_apply_single_rule_missing_source_attribute(source_system, target_system):
    """Fields missing on the source component produce Err results."""
    rule = Rule(
        source_type="BusComponent",
        target_type="NodeComponent",
        version=1,
        field_map={"unknown": "missing_attribute"},
    )
    context = _build_context(
        rules=[rule],
        source_system=source_system,
        target_system=target_system,
    )

    result = apply_single_rule(rule, context)
    assert result.is_err()
    assert "No attribute" in str(result.err())


def test_attach_component_supplemental_attribute_target_missing(source_system):
    """Supplemental attributes without matching target UUID fail gracefully."""
    target_system = System(name="executor-target")
    context = _build_context(
        rules=[],
        source_system=source_system,
        target_system=target_system,
    )

    bus = next(source_system.get_components(BusComponent))
    attribute = BusGeographicInfo(
        uuid=bus.uuid,
        latitude=12.3,
        longitude=45.6,
        location_name="nowhere",
    )

    result = _attach_component(attribute, bus, context)
    assert result.is_err()
    assert "Cannot attach supplemental attribute" in str(result.err())


def test_attach_component_non_supplemental_success(source_system):
    """Non-supplemental components are added directly to the target system."""
    target_system = System(name="executor-target-success")
    context = _build_context(
        rules=[],
        source_system=source_system,
        target_system=target_system,
    )

    bus = next(source_system.get_components(BusComponent))
    result = _attach_component(bus, bus, context)
    assert result.is_ok()
