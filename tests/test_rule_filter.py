"""Tests for declarative rule filters and executor integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fixtures.context import FIXTURE_MODEL_MODULES
from fixtures.target_system import StationComponent

if TYPE_CHECKING:
    from r2x_core import RuleFilter, System


class _Dummy:
    def __init__(self, **attrs):
        for key, value in attrs.items():
            setattr(self, key, value)


def test_rule_filter_matches_leaf_casefold():
    """Leaf filters respect casefolded string comparisons."""
    from r2x_core import RuleFilter
    from r2x_core.rules_utils import _evaluate_rule_filter

    filt = RuleFilter(field="kind", op="eq", values=["gas"])
    assert _evaluate_rule_filter(filt, _Dummy(kind="GAS"))


def test_rule_filter_matches_any_of():
    """Composite any_of evaluates to True when any child matches."""
    from r2x_core import RuleFilter
    from r2x_core.rules_utils import _evaluate_rule_filter

    filt = RuleFilter(
        any_of=[
            RuleFilter(field="kind", op="eq", values=["coal"]),
            RuleFilter(field="kind", op="eq", values=["gas"]),
        ]
    )
    assert _evaluate_rule_filter(filt, _Dummy(kind="gas"))


def test_rule_filter_matches_geq_numeric():
    """Numeric geq comparison works for thresholds."""
    from r2x_core import RuleFilter
    from r2x_core.rules_utils import _evaluate_rule_filter

    filt = RuleFilter(field="capacity", op="geq", values=[400])
    assert _evaluate_rule_filter(filt, _Dummy(capacity=500.0))
    assert not _evaluate_rule_filter(filt, _Dummy(capacity=300))


def _run_rule_with_filter(filter_spec: RuleFilter, source_system: System) -> tuple[int, System]:
    """Apply a single filtered rule and return conversion count and target system."""
    from r2x_core import PluginConfig, Rule, System, TranslationContext, apply_rules_to_context

    config = PluginConfig(models=FIXTURE_MODEL_MODULES)
    rule = Rule(
        source_type="PlantComponent",
        target_type="StationComponent",
        version=1,
        field_map={"name": "name", "uuid": "uuid"},
        filter=filter_spec,
    )
    target_system = System(name="FilteredTarget", auto_add_composed_components=True)
    context = TranslationContext(
        source_system=source_system,
        target_system=target_system,
        config=config,
        rules=[rule],
    )
    result = apply_rules_to_context(context)
    return result.total_converted, target_system


def test_apply_rules_respects_filter_include(source_system):
    """Inclusive filters allow matching components to convert."""

    from r2x_core import RuleFilter

    converted, target_system = _run_rule_with_filter(
        RuleFilter(field="fuel_type", op="eq", values=["gas"]),
        source_system,
    )
    stations = list(target_system.get_components(StationComponent))
    assert converted == 1
    assert stations and stations[0].name == "plant_alpha"


def test_apply_rules_respects_filter_exclude(source_system):
    """Exclusive filters prevent matching components from converting."""
    from r2x_core import RuleFilter

    converted, target_system = _run_rule_with_filter(
        RuleFilter(field="fuel_type", op="neq", values=["gas"]),
        source_system,
    )
    stations = list(target_system.get_components(StationComponent))
    assert converted == 0
    assert not stations


def test_rule_filter_startswith():
    """Test that 'startswith' operator works for RuleFilter."""
    from r2x_core import RuleFilter
    from r2x_core.rules_utils import _evaluate_rule_filter

    filt = RuleFilter(field="kind", op="startswith", values=["ga"])
    assert _evaluate_rule_filter(filt, _Dummy(kind="gas"))
    assert not _evaluate_rule_filter(filt, _Dummy(kind="coal"))


def test_rule_filter_not_startswith():
    """Test that 'not_startswith' operator works for RuleFilter."""
    from r2x_core import RuleFilter
    from r2x_core.rules_utils import _evaluate_rule_filter

    filt = RuleFilter(field="kind", op="not_startswith", values=["ga"])
    assert _evaluate_rule_filter(filt, _Dummy(kind="coal"))
    assert not _evaluate_rule_filter(filt, _Dummy(kind="gas"))


def test_apply_rules_respects_filter_prefix(source_system):
    """Rule filters with prefixes control conversion in the executor."""
    from r2x_core import RuleFilter

    converted, target_system = _run_rule_with_filter(
        RuleFilter(field="name", op="startswith", prefixes=["plant_"]),
        source_system,
    )
    stations = list(target_system.get_components(StationComponent))
    assert converted == 1
    assert stations and stations[0].name == "plant_alpha"


def test_apply_rules_respects_filter_not_prefix(source_system):
    """Negative prefix filters block matching components."""
    from r2x_core import RuleFilter

    converted, _ = _run_rule_with_filter(
        RuleFilter(field="name", op="not_startswith", prefixes=["plant_"]),
        source_system,
    )
    assert converted == 0
