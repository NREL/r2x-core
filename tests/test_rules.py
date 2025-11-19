import pytest


def test_simple_rule_creation(rules_simple):
    """Create and verify simple rule with single-field mapping."""
    rule_simple = rules_simple[0]
    assert rule_simple.source_type == "ACBus"
    assert rule_simple.target_type == "PLEXOSNode"
    assert rule_simple.version == 1
    assert rule_simple.field_map == {"name": "name", "uuid": "uuid", "units": "available"}
    assert rule_simple.getters == {}
    assert rule_simple.defaults == {"load": 0.0, "units": 0.0}


def test_multifield_rule_requires_getter():
    """Multi-field mapping without getter raises ValueError."""
    from r2x_core import Rule

    with pytest.raises(ValueError, match=r"Multi-field mapping .* requires a getter"):
        Rule(
            source_type="Gen",
            target_type="PGen",
            version=1,
            field_map={
                "rating": ["power_a", "power_b"],  # Multi-field without getter
            },
            getters={},  # Missing getter for rating
        )


def test_validation_with_multiple_multifield_mappings():
    """Validation checks all multi-field mappings."""
    from r2x_core import Rule

    with pytest.raises(ValueError, match=r"Multi-field mapping .* requires a getter"):
        Rule(
            source_type="Multi",
            target_type="PMulti",
            version=1,
            field_map={
                "field1": ["src_a", "src_b"],
                "field2": ["src_c", "src_d"],
            },
            getters={
                "field1": lambda c: 0,  # Only field1 has getter
            },
        )


def test_rule_is_frozen(rules_simple):
    """Verify rule is frozen (immutable)."""
    from dataclasses import FrozenInstanceError

    rule_simple = rules_simple[0]
    with pytest.raises(FrozenInstanceError):
        rule_simple.version = 2
