"""Tests for rule-based component translation using functional dispatcher."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from r2x_core import TranslationContext


def test_convert_rule_single_component(context_example: TranslationContext):
    """convert_rule applies a rule to all matching source components."""
    from fixtures.target_system import CircuitComponent, NodeComponent, StationComponent

    from r2x_core import apply_rules_to_context

    result = apply_rules_to_context(context_example)

    assert result.success
    assert result.total_rules == 3
    assert result.total_converted == 3
    assert all(rule_result.success for rule_result in result.rule_results)
    assert all(rule_result.converted == 1 for rule_result in result.rule_results)

    target_system = context_example.target_system

    bus_nodes = [node for node in target_system.get_components(NodeComponent) if node.name == "bus_a"]
    assert bus_nodes and bus_nodes[0].demand_mw == 150.0

    circuits = [
        circuit for circuit in target_system.get_components(CircuitComponent) if circuit.name == "line_ab"
    ]
    assert circuits and circuits[0].capacity_mw == 300.0

    stations = [
        station for station in target_system.get_components(StationComponent) if station.name == "plant_alpha"
    ]
    assert stations and stations[0].resource == "gas"
