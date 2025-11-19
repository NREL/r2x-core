import pytest

from r2x_core import Rule


@pytest.fixture
def rules_simple() -> Rule:
    """Translation rules between source and target fixture components."""
    from r2x_core import Rule

    rules = [
        {
            "source_type": "BusComponent",
            "target_type": "NodeComponent",
            "version": 1,
            "field_map": {
                "name": "name",
                "uuid": "uuid",
                "kv_rating": "voltage_kv",
                "demand_mw": "load_mw",
                "area": "zone",
            },
            "defaults": {"area": "unspecified"},
        },
        {
            "source_type": "LineComponent",
            "target_type": "CircuitComponent",
            "version": 1,
            "field_map": {
                "name": "name",
                "uuid": "uuid",
                "r_pu": "resistance_ohm",
                "x_pu": "reactance_ohm",
                "capacity_mw": "thermal_limit_mw",
            },
            "defaults": {"capacity_mw": 0.0},
        },
        {
            "source_type": "PlantComponent",
            "target_type": "StationComponent",
            "version": 1,
            "field_map": {
                "name": "name",
                "uuid": "uuid",
                "max_output_mw": "capacity_mw",
                "min_output_mw": "min_stable_level_mw",
                "resource": "fuel_type",
            },
            "defaults": {"resource": "unknown"},
        },
    ]
    return Rule.from_records(rules)
