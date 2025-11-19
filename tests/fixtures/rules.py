import pytest

from r2x_core import Rule


@pytest.fixture
def rules_simple() -> Rule:
    """Single-field transformation rules."""
    from r2x_core import Rule

    rules = [
        {
            "source_type": "ACBus",
            "target_type": "PLEXOSNode",
            "version": 1,
            "field_map": {"name": "name", "uuid": "uuid", "units": "available"},
            "defaults": {"load": 0.0, "units": 0.0},
        },
        {
            "source_type": "Line",
            "target_type": "PLEXOSLine",
            "version": 1,
            "field_map": {
                "name": "name",
                "uuid": "uuid",
                "resistance": "r",
                "reactance": "x",
            },
            "defaults": {"min_flow": 0.0, "category": "line"},
        },
    ]
    return Rule.from_records(rules)
