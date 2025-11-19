from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fixtures.context import FIXTURE_MODEL_MODULES
from pydantic import Field

from r2x_core import PluginConfig

if TYPE_CHECKING:
    from r2x_core import PluginConfig, Rule, System, TranslationContext


def build_fixture_config() -> PluginConfig:
    """Create a PluginConfig aligned with the fixtures' component modules."""

    return PluginConfig(models=FIXTURE_MODEL_MODULES)


class ConfigWithActiveVersions(PluginConfig):
    """Test helper config that can declare active versions for source types."""

    active_versions: dict[str, int] = Field(default_factory=dict)


def build_context(
    rules: list[Rule],
    source_system: System,
    target_system: System,
    config: PluginConfig | None = None,
) -> TranslationContext:
    """Construct a TranslationContext wired to the fixture systems."""
    from r2x_core import TranslationContext

    return TranslationContext(
        source_system=source_system,
        target_system=target_system,
        config=config or build_fixture_config(),
        rules=rules,
    )


def test_context_creation(context_example):
    """Create context_example and verify all required fields are present."""
    ctx = context_example

    assert ctx.source_system is not None
    assert ctx.target_system is not None
    assert ctx.config is not None
    assert len(ctx.rules) > 0


def test_context_rejects_duplicate_rules():
    """Creating context_example with duplicate rule keys raises ValueError."""
    from r2x_core import Rule, System, TranslationContext

    rule1 = Rule(
        source_type="Bus",
        target_type="Node",
        version=1,
        field_map={"name": "name"},
    )
    rule2 = Rule(
        source_type="Bus",
        target_type="Node",
        version=1,
        field_map={"name": "name", "extra": "extra"},
    )
    with pytest.raises(ValueError, match="Duplicate rule key"):
        TranslationContext(
            source_system=System(name="Source"),
            target_system=System(name="Target"),
            config=PluginConfig(),
            rules=[rule1, rule2],
        )


def test_context_is_frozen(context_example):
    """Verify context_example is frozen (immutable)."""
    with pytest.raises(AttributeError):
        context_example.rules = []


def test_context_source_system_immutable(context_example):
    """Verify source_system cannot be modified."""
    with pytest.raises(AttributeError):
        context_example.source_system = None


def test_context_config_immutable(context_example):
    """Verify config cannot be modified."""
    with pytest.raises(AttributeError):
        context_example.config = None


def test_get_rule_by_types_and_version(context_example):
    """Retrieve rule by source type, target type, and explicit version."""
    rule = context_example.get_rule("BusComponent", "NodeComponent", version=1)

    assert rule.source_type == "BusComponent"
    assert rule.target_type == "NodeComponent"
    assert rule.version == 1


def test_get_rule_not_found_raises_keyerror(context_example):
    """Retrieve non-existent rule raises KeyError."""
    with pytest.raises(KeyError, match="No rule found"):
        context_example.get_rule("NonExistent", "Type", version=99)


def test_get_rule_version_mismatch_raises_keyerror(context_example):
    """Request non-existent version of existing rule raises KeyError."""
    with pytest.raises(KeyError, match="No rule found"):
        context_example.get_rule("BusComponent", "NodeComponent", version=99)


def test_get_rule_with_different_versions(source_system, target_system):
    """Retrieve different versions of same conversion."""
    from r2x_core import Rule

    rule_v1 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=1, field_map={"name": "name"}
    )
    rule_v2 = Rule(
        source_type="BusComponent",
        target_type="NodeComponent",
        version=2,
        field_map={"name": "name", "extra": "extra"},
    )
    ctx = build_context([rule_v1, rule_v2], source_system, target_system)

    retrieved_v1 = ctx.get_rule("BusComponent", "NodeComponent", version=1)
    retrieved_v2 = ctx.get_rule("BusComponent", "NodeComponent", version=2)

    assert retrieved_v1.version == 1
    assert retrieved_v2.version == 2
    assert len(retrieved_v1.field_map) == 1
    assert len(retrieved_v2.field_map) == 2


def test_list_rules_returns_all_rules(context_example):
    """List all rules in context."""
    from r2x_core import Rule

    rules = context_example.list_rules()

    assert len(rules) == 3
    assert all(isinstance(r, Rule) for r in rules)


def test_list_rules_includes_all_types(context_example):
    """list_rules includes rules for all component types."""
    rules = context_example.list_rules()
    source_types = {r.source_type for r in rules}

    assert "BusComponent" in source_types
    assert "LineComponent" in source_types
    assert "PlantComponent" in source_types


def test_list_available_conversions_structure(context_example):
    """list_available_conversions returns correct structure."""
    conversions = context_example.list_available_conversions()

    assert isinstance(conversions, dict)
    assert all(isinstance(k, str) for k in conversions)
    assert all(isinstance(v, list) for v in conversions.values())
    assert all(isinstance(item, tuple) and len(item) == 2 for items in conversions.values() for item in items)


def test_list_available_conversions_content(context_example):
    """list_available_conversions returns correct content."""
    conversions = context_example.list_available_conversions()

    assert conversions["BusComponent"] == [("NodeComponent", 1)]
    assert conversions["LineComponent"] == [("CircuitComponent", 1)]
    assert conversions["PlantComponent"] == [("StationComponent", 1)]


def test_list_available_conversions_is_sorted(context_example):
    """list_available_conversions returns sorted target types and versions."""
    conversions = context_example.list_available_conversions()

    for targets in conversions.values():
        assert targets == sorted(targets)


def test_list_available_conversions_with_multiple_versions(source_system, target_system):
    """list_available_conversions with multiple versions of same type."""
    from r2x_core import Rule

    rule_v1 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=1, field_map={"name": "name"}
    )
    rule_v2 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=2, field_map={"name": "name"}
    )
    ctx = build_context([rule_v1, rule_v2], source_system, target_system)

    conversions = ctx.list_available_conversions()

    assert len(conversions["BusComponent"]) == 2
    assert ("NodeComponent", 1) in conversions["BusComponent"]
    assert ("NodeComponent", 2) in conversions["BusComponent"]


def test_list_available_conversions_with_multiple_targets(source_system, target_system):
    """list_available_conversions with same source type but different targets."""
    from r2x_core import Rule

    rule_1 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=1, field_map={"name": "name"}
    )
    rule_2 = Rule(
        source_type="BusComponent",
        target_type="StationComponent",
        version=1,
        field_map={"name": "name"},
    )
    ctx = build_context([rule_1, rule_2], source_system, target_system)

    conversions = ctx.list_available_conversions()

    assert len(conversions["BusComponent"]) == 2
    assert conversions["BusComponent"] == [("NodeComponent", 1), ("StationComponent", 1)]


def test_get_rules_for_source(context_example):
    """Get all rules for a specific source type."""
    bus_rules = context_example.get_rules_for_source("BusComponent")

    assert len(bus_rules) == 1
    assert all(r.source_type == "BusComponent" for r in bus_rules)


def test_get_rules_for_source_multiple_versions(source_system, target_system):
    """Get rules for source with multiple versions."""
    from r2x_core import Rule

    rule_v1 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=1, field_map={"name": "name"}
    )
    rule_v2 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=2, field_map={"name": "name"}
    )
    ctx = build_context([rule_v1, rule_v2], source_system, target_system)

    bus_rules = ctx.get_rules_for_source("BusComponent")

    assert len(bus_rules) == 2
    assert all(r.source_type == "BusComponent" for r in bus_rules)


def test_get_rules_for_source_not_found():
    """Get rules for non-existent source returns empty list."""
    from r2x_core import PluginConfig, System, TranslationContext

    ctx = TranslationContext(
        source_system=System(name="source"),
        target_system=System(name="target"),
        config=PluginConfig(),
        rules=[],
    )

    rules = ctx.get_rules_for_source("NonExistent")
    assert rules == []


def test_get_rules_for_conversion(context_example):
    """Get all versions of a specific conversion."""
    rules = context_example.get_rules_for_conversion("BusComponent", "NodeComponent")

    assert len(rules) == 1
    assert all(r.source_type == "BusComponent" and r.target_type == "NodeComponent" for r in rules)


def test_get_rules_for_conversion_multiple_versions(source_system, target_system):
    """Get multiple versions of a conversion."""
    from r2x_core import Rule

    rule_v1 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=1, field_map={"name": "name"}
    )
    rule_v2 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=2, field_map={"name": "name"}
    )
    rule_v3 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=3, field_map={"name": "name"}
    )
    ctx = build_context([rule_v1, rule_v2, rule_v3], source_system, target_system)

    rules = ctx.get_rules_for_conversion("BusComponent", "NodeComponent")

    assert len(rules) == 3
    assert [r.version for r in rules] == [1, 2, 3]


def test_get_rules_for_conversion_not_found():
    """Get conversion that doesn't exist returns empty list."""

    from r2x_core import PluginConfig, System, TranslationContext

    ctx = TranslationContext(
        source_system=System(name="source"),
        target_system=System(name="target"),
        config=PluginConfig(),
        rules=[],
    )

    rules = ctx.get_rules_for_conversion("BusComponent", "NodeComponent")
    assert rules == []


def test_rule_retrieved_from_context_is_usable(context_example):
    """Rule retrieved from context can be used immediately."""
    rule = context_example.get_rule("PlantComponent", "StationComponent", version=1)

    assert rule.source_type == "PlantComponent"
    assert rule.target_type == "StationComponent"
    assert rule.field_map["max_output_mw"] == "capacity_mw"
    assert rule.defaults["resource"] == "unknown"


def test_creating_context_with_rule_from_fixture(
    source_system,
    target_system,
    rules_simple,
):
    """Create context with a rule fixture."""
    simple_rule = rules_simple[0]
    ctx = build_context([simple_rule], source_system, target_system)

    retrieved_rule = ctx.get_rule("BusComponent", "NodeComponent", version=1)
    assert retrieved_rule is simple_rule


def test_context_with_versioned_rules_fixture(source_system, target_system):
    """Active versions in config determine which rule is returned."""
    from r2x_core import Rule

    config = ConfigWithActiveVersions(models=FIXTURE_MODEL_MODULES, active_versions={"BusComponent": 2})
    rule_v1 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=1, field_map={"name": "name"}
    )
    rule_v2 = Rule(
        source_type="BusComponent", target_type="NodeComponent", version=2, field_map={"name": "name"}
    )
    ctx = build_context([rule_v1, rule_v2], source_system, target_system, config=config)

    rule_active = ctx.get_rule("BusComponent", "NodeComponent")
    assert rule_active.version == 2

    explicit_rule = ctx.get_rule("BusComponent", "NodeComponent", version=1)
    assert explicit_rule.version == 1


def test_rules_list_preserves_order(source_system, target_system):
    """Rules are returned in the order they were provided."""
    from r2x_core import Rule

    rule_a = Rule(source_type="A", target_type="X", version=1, field_map={"f": "f"})
    rule_b = Rule(source_type="B", target_type="Y", version=1, field_map={"f": "f"})
    rule_c = Rule(source_type="C", target_type="Z", version=1, field_map={"f": "f"})

    ctx = build_context([rule_a, rule_b, rule_c], source_system, target_system)

    listed_rules = ctx.list_rules()
    assert listed_rules == [rule_a, rule_b, rule_c]
