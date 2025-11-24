"""Tests for rules that produce supplemental attributes."""

from __future__ import annotations

from uuid import uuid4

from fixtures.source_system import BusComponent, BusGeographicInfo
from fixtures.target_system import NodeComponent

from r2x_core import PluginConfig
from r2x_core.rules import Rule
from r2x_core.rules_executor import apply_rules_to_context
from r2x_core.system import System
from r2x_core.translation import TranslationContext


def _build_test_config() -> PluginConfig:
    """Create a PluginConfig pointing at fixture modules for component resolution."""
    return PluginConfig(models=["fixtures.source_system", "fixtures.target_system"])


def test_rule_creates_supplemental_attribute():
    """Test that a rule can create and attach a supplemental attribute to a component."""
    source_system = System(name="source", system_base=100.0)
    source_uuid = str(uuid4())
    bus_component = BusComponent(
        name="test_bus",
        uuid=source_uuid,
        voltage_kv=230.0,
        load_mw=150.0,
        zone="north",
    )
    source_system.add_component(bus_component)

    target_system = System(name="target", system_base=100.0)

    component_rule = Rule(
        source_type="BusComponent",
        target_type="NodeComponent",
        version=1,
        field_map={
            "name": "name",
            "uuid": "uuid",
            "kv_rating": "voltage_kv",
            "demand_mw": "load_mw",
            "area": "zone",
        },
    )

    supplemental_rule = Rule(
        source_type="BusComponent",
        target_type="BusGeographicInfo",
        version=1,
        field_map={"location_name": "zone", "latitude": "voltage_kv", "longitude": "load_mw"},
    )

    context = TranslationContext(
        source_system=source_system,
        target_system=target_system,
        config=_build_test_config(),
        rules=[component_rule, supplemental_rule],
    )

    result = apply_rules_to_context(context)

    assert result.successful_rules == 2
    assert result.failed_rules == 0
    assert result.total_converted == 2

    target_nodes = list(target_system.get_components(NodeComponent))
    assert len(target_nodes) == 1
    target_node = target_nodes[0]
    assert target_node.kv_rating == 230.0
    assert target_node.demand_mw == 150.0
    assert target_node.area == "north"
    assert str(target_node.uuid) == source_uuid

    supplemental_attrs = target_system.get_supplemental_attributes_with_component(target_node)
    assert len(supplemental_attrs) == 1
    supplemental_attr = supplemental_attrs[0]
    assert isinstance(supplemental_attr, BusGeographicInfo)
    assert supplemental_attr.location_name == "north"
    assert supplemental_attr.latitude == 230.0  # Mapped from voltage_kv
    assert supplemental_attr.longitude == 150.0  # Mapped from load_mw


def test_supplemental_attribute_without_target_component_fails():
    """Test that creating a supplemental attribute without a target component fails."""
    source_system = System(name="source", system_base=100.0)
    source_uuid = str(uuid4())
    bus_component = BusComponent(
        name="test_bus",
        uuid=source_uuid,
        voltage_kv=230.0,
        load_mw=150.0,
        zone="north",
    )
    source_system.add_component(bus_component)

    target_system = System(name="target", system_base=100.0)

    supplemental_rule = Rule(
        source_type="BusComponent",
        target_type="BusGeographicInfo",
        version=1,
        field_map={"location_name": "zone", "latitude": "voltage_kv", "longitude": "load_mw"},
    )

    context = TranslationContext(
        source_system=source_system,
        target_system=target_system,
        config=_build_test_config(),
        rules=[supplemental_rule],
    )

    result = apply_rules_to_context(context)

    assert result.successful_rules == 0
    assert result.failed_rules == 1
    assert "not found in target system" in result.rule_results[0].error


def test_multiple_supplemental_attributes_on_same_component():
    """Test that multiple supplemental attributes can be attached to the same component."""
    source_system = System(name="source", system_base=100.0)
    source_uuid = str(uuid4())
    bus_component = BusComponent(
        name="test_bus",
        uuid=source_uuid,
        voltage_kv=230.0,
        load_mw=150.0,
        zone="north",
    )
    source_system.add_component(bus_component)

    target_system = System(name="target", system_base=100.0)

    component_rule = Rule(
        source_type="BusComponent",
        target_type="NodeComponent",
        version=1,
        field_map={
            "name": "name",
            "uuid": "uuid",
            "kv_rating": "voltage_kv",
            "demand_mw": "load_mw",
            "area": "zone",
        },
    )

    supplemental_rule1 = Rule(
        source_type="BusComponent",
        target_type="BusGeographicInfo",
        version=1,
        field_map={"location_name": "zone", "latitude": "voltage_kv"},
        defaults={"longitude": -122.4194},
    )

    supplemental_rule2 = Rule(
        source_type="BusComponent",
        target_type="BusGeographicInfo",
        version=2,  # Different version to avoid duplicate rule key
        field_map={"location_name": "zone", "latitude": "load_mw"},
        defaults={"longitude": -74.0060},  # Different location
    )

    context = TranslationContext(
        source_system=source_system,
        target_system=target_system,
        config=_build_test_config(),
        rules=[component_rule, supplemental_rule1, supplemental_rule2],
    )

    result = apply_rules_to_context(context)

    assert result.successful_rules == 3
    assert result.failed_rules == 0

    target_node = next(iter(target_system.get_components(NodeComponent)))
    supplemental_attrs = target_system.get_supplemental_attributes_with_component(target_node)
    assert len(supplemental_attrs) == 2
    assert all(isinstance(attr, BusGeographicInfo) for attr in supplemental_attrs)
