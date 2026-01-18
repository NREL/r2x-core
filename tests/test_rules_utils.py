"""Unit tests for helpers in r2x_core.rules_utils."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest
from fixtures.source_system import BusComponent
from fixtures.target_system import NodeComponent
from rust_ok import Err, Ok

from r2x_core import Rule
from r2x_core.rules_utils import (
    _build_target_fields,
    _create_target_component,
    _make_attr_getter,
    _resolve_component_type,
    build_component_kwargs,
)


def test_resolve_component_type_success(context_example):
    """Component types configured on the context can be resolved."""
    result = _resolve_component_type("BusComponent", context_example)

    assert result.is_ok()
    assert result.unwrap() is BusComponent


def test_resolve_component_type_missing_returns_error(context_example):
    """Unknown component types return an error result."""
    result = _resolve_component_type("NotAComponent", context_example)

    assert result.is_err()
    assert "NotAComponent" in str(result.err())


def test_make_attr_getter_traverses_chain():
    """Attr getter walks nested attributes and returns Ok result."""

    class Inner:
        value = 99

    class Outer:
        inner = Inner()

    getter = _make_attr_getter(["inner", "value"])
    result = getter(cast(Any, None), Outer())

    assert result.is_ok()
    assert result.unwrap() == 99


def test_build_target_fields_applies_defaults_and_getters(context_example):
    """Missing attributes fall back to defaults and getters override values."""

    class Source:
        name = "comp_a"
        demand = None

    rule = Rule(
        source_type="SourceType",
        target_type="TargetType",
        version=1,
        field_map={"name": "name", "demand_mw": "demand"},
        getters={"area": lambda _ctx, _src: Ok("north")},
        defaults={"demand_mw": 0.0},
    )

    result = _build_target_fields(rule, Source(), context_example)

    assert result.is_ok()
    fields = result.unwrap()
    assert fields["name"] == "comp_a"
    assert fields["demand_mw"] == 0.0
    assert fields["area"] == "north"


def test_build_target_fields_missing_attribute_without_default(context_example):
    """Missing attributes without defaults produce an error."""

    class Source:
        pass

    rule = Rule(
        source_type="SourceType",
        target_type="TargetType",
        version=1,
        field_map={"required": "missing_attr"},
    )

    result = _build_target_fields(rule, Source(), context_example)
    assert result.is_err()
    assert "missing_attr" in str(result.err())


def test_build_target_fields_getter_error_without_default(context_example):
    """Getter failures propagate when no default is defined."""

    class Source:
        value = "x"

    def faulty_getter(_ctx, _src):
        return Err(ValueError("boom"))

    rule = Rule(
        source_type="SourceType",
        target_type="TargetType",
        version=1,
        field_map={"value": "value"},
        getters={"computed": faulty_getter},
    )

    result = _build_target_fields(rule, Source(), context_example)
    assert result.is_err()
    assert "failed" in str(result.err()).lower()


def test_build_target_fields_non_callable_getter_rejected(context_example):
    """Non-callable getter entries raise an error."""

    class Source:
        value = 1

    rule = Rule(
        source_type="SourceType",
        target_type="TargetType",
        version=1,
        field_map={"value": "value"},
        getters={"computed": "not_callable"},
    )

    result = _build_target_fields(rule, Source(), context_example)
    assert result.is_err()
    assert "not callable" in str(result.err())


def test_create_target_component_instantiates_class():
    """_create_target_component simply instantiates the provided class."""

    class Dummy(NodeComponent):
        """Subclass to ensure kwargs are forwarded."""

    dummy = _create_target_component(Dummy, {"name": "node_x"})

    assert isinstance(dummy, Dummy)
    assert dummy.name == "node_x"


def test_build_component_kwargs_from_parser_record(context_example):
    """Parsers should be able to reuse rules helpers with raw records."""
    record = {
        "name": "parser_component",
        "region_code": "north-zone",
        "ramp_rate_mw_per_min": 12.0,
    }

    @dataclass
    class RampLimits:
        up: float
        down: float

    def resolve_region(ctx, src):
        for node in ctx.target_system.get_components(NodeComponent):
            if node.area == src.region_code:
                return Ok(node)
        return Err(ValueError(f"Unknown region code {src.region_code}"))

    def convert_ramp_rate(ctx, src):
        system_base = ctx.target_system.base_power or 1.0
        per_unit_value = src.ramp_rate_mw_per_min / system_base
        return Ok(RampLimits(up=per_unit_value, down=per_unit_value))

    rule = Rule(
        source_type="ParserRecord",
        target_type="StationComponent",
        version=1,
        field_map={"component_name": "name"},
        getters={
            "region_component": resolve_region,
            "ramp_limits": convert_ramp_rate,
        },
    )

    result = build_component_kwargs(record, rule=rule, context=context_example)

    assert result.is_ok()
    kwargs = result.unwrap()
    assert kwargs["component_name"] == "parser_component"
    assert kwargs["region_component"].area == "north-zone"
    assert kwargs["ramp_limits"].up == pytest.approx(0.12)
    assert kwargs["ramp_limits"].down == pytest.approx(0.12)
