"""Additional tests for upgrader module to improve coverage.

Tests for edge cases and missing coverage areas.
"""

from r2x_core.upgrader import (
    UpgradeContext,
    UpgradeResult,
    UpgradeStep,
    apply_upgrade,
    apply_upgrades,
    apply_upgrades_with_rollback,
)
from r2x_core.versioning import SemanticVersioningStrategy


def test_lazy_initialization_no_upgrades():
    """Test that snapshot is NOT created when no upgrades are applied."""
    data = {"version": "2.0.0"}
    result = UpgradeResult(data)

    assert result._original_snapshot is None
    assert result.current_data == data
    assert result.applied_steps == []
    assert result.original_data is data


def test_lazy_initialization_with_ensure_snapshot():
    """Test explicit snapshot creation via ensure_snapshot()."""
    data = {"version": "1.0.0", "value": 42}
    result = UpgradeResult(data)

    assert result._original_snapshot is None

    result.ensure_snapshot()
    assert result._original_snapshot is not None
    assert result._original_snapshot == data
    assert result._original_snapshot is not data

    old_snapshot = result._original_snapshot
    result.ensure_snapshot()
    assert result._original_snapshot is old_snapshot


def test_lazy_initialization_snapshot_created_on_first_upgrade():
    """Test that snapshot is created when first upgrade is applied via apply_upgrades_with_rollback."""

    def upgrade_func(data):
        data["version"] = "2.0.0"
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="upgrade_to_v2",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
    )

    data = {"version": "1.0.0"}
    result = apply_upgrades_with_rollback(data, [step])

    assert result._original_snapshot is not None
    assert result._original_snapshot["version"] == "1.0.0"
    assert result.current_data["version"] == "2.0.0"


def test_lazy_initialization_no_snapshot_when_no_steps():
    """Test that no snapshot is created when no applicable steps exist."""
    data = {"version": "2.0.0"}
    result = apply_upgrades_with_rollback(data, [])

    assert result._original_snapshot is None
    assert result.applied_steps == []


def test_rollback_without_snapshot():
    """Test rollback when no snapshot was created (no upgrades applied)."""
    data = {"version": "2.0.0"}
    result = UpgradeResult(data)

    assert result._original_snapshot is None

    rolled_back = result.rollback()
    assert rolled_back is data
    assert rolled_back["version"] == "2.0.0"


def test_original_data_property_with_snapshot():
    """Test original_data property returns snapshot when available."""
    data = {"version": "1.0.0"}
    result = UpgradeResult(data)

    result.ensure_snapshot()

    assert result.original_data is result._original_snapshot
    assert result.original_data is not data


def test_apply_upgrade_max_version_constraint():
    """Test apply_upgrade with max_version constraint violation."""

    def upgrade_func(data):
        data["upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="upgrade_constrained",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        min_version="1.0.0",
        max_version="1.5.0",
    )

    data = {"version": "1.8.0"}
    result, applied = apply_upgrade(data, step)

    assert applied is False
    assert result["version"] == "1.8.0"
    assert "upgraded" not in result


def test_apply_upgrades_exception_handling():
    """Test exception handling in apply_upgrades (continues on error)."""

    def upgrade_v2(data):
        data["version"] = "2.0.0"
        return data

    def upgrade_v3_fails(data):
        raise RuntimeError("Intentional failure")

    def upgrade_v4(data):
        data["version"] = "4.0.0"
        return data

    strategy = SemanticVersioningStrategy()
    steps = [
        UpgradeStep(
            name="upgrade_to_v2",
            func=upgrade_v2,
            target_version="2.0.0",
            versioning_strategy=strategy,
            priority=10,
        ),
        UpgradeStep(
            name="upgrade_to_v3_fails",
            func=upgrade_v3_fails,
            target_version="3.0.0",
            versioning_strategy=strategy,
            priority=20,
        ),
        UpgradeStep(
            name="upgrade_to_v4",
            func=upgrade_v4,
            target_version="4.0.0",
            versioning_strategy=strategy,
            priority=30,
        ),
    ]

    data = {"version": "1.0.0"}
    result, applied = apply_upgrades(data, steps)

    assert result["version"] == "4.0.0"
    assert applied == ["upgrade_to_v2", "upgrade_to_v4"]
    assert "upgrade_to_v3_fails" not in applied


def test_apply_upgrades_all_fail():
    """Test apply_upgrades when all steps fail."""

    def failing_upgrade(data):
        raise RuntimeError("All upgrades fail")

    strategy = SemanticVersioningStrategy()
    steps = [
        UpgradeStep(
            name="upgrade_fails",
            func=failing_upgrade,
            target_version="2.0.0",
            versioning_strategy=strategy,
        ),
    ]

    data = {"version": "1.0.0"}
    result, applied = apply_upgrades(data, steps)

    assert result["version"] == "1.0.0"
    assert applied == []


def test_upgrade_context_enum_values():
    """Test UpgradeContext enum values."""
    assert UpgradeContext.DATA.value == "DATA"
    assert UpgradeContext.SYSTEM.value == "SYSTEM"
    assert UpgradeContext.BOTH.value == "BOTH"


def test_upgrade_step_with_upgrade_type():
    """Test UpgradeStep with different upgrade_type values."""

    def upgrade_func(data):
        return data

    strategy = SemanticVersioningStrategy()

    # Data upgrade
    data_step = UpgradeStep(
        name="data_upgrade",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        upgrade_type="data",
    )
    assert data_step.upgrade_type == "data"

    # System upgrade
    system_step = UpgradeStep(
        name="system_upgrade",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        upgrade_type="system",
    )
    assert system_step.upgrade_type == "system"


def test_apply_upgrades_with_string_context():
    """Test apply_upgrades with string context (backward compatibility)."""

    def upgrade_func(data):
        data["version"] = "2.0.0"
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="upgrade_to_v2",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        context="DATA",
    )

    data = {"version": "1.0.0"}
    result, applied = apply_upgrades(data, [step], context="DATA")

    assert result["version"] == "2.0.0"
    assert applied == ["upgrade_to_v2"]


def test_apply_upgrades_with_rollback_no_applicable_steps():
    """Test apply_upgrades_with_rollback when no steps are applicable."""

    def upgrade_func(data):
        data["version"] = "2.0.0"
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="system_upgrade",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        context=UpgradeContext.SYSTEM,
        upgrade_type="system",
    )

    data = {"version": "1.0.0"}
    result = apply_upgrades_with_rollback(data, [step], context=UpgradeContext.DATA, upgrade_type="data")

    assert result.applied_steps == []
    assert result._original_snapshot is None


def test_multiple_rollbacks():
    """Test calling rollback multiple times."""

    def upgrade_func(data):
        data["version"] = "2.0.0"
        data["field"] = "added"
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="upgrade_to_v2",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
    )

    data = {"version": "1.0.0"}
    result = apply_upgrades_with_rollback(data, [step])

    assert result.current_data["version"] == "2.0.0"
    assert "field" in result.current_data

    rolled_back = result.rollback()
    assert rolled_back["version"] == "1.0.0"
    assert "field" not in rolled_back
    assert result.applied_steps == []

    rolled_back_again = result.rollback()
    assert rolled_back_again["version"] == "1.0.0"
    assert result.applied_steps == []


def test_upgrade_result_data_mutation_isolation():
    """Test that original data is protected from mutations after snapshot."""
    data = {"version": "1.0.0", "nested": {"value": 42}}
    result = UpgradeResult(data)
    result.ensure_snapshot()

    result.current_data["nested"]["value"] = 999
    result.current_data["version"] = "2.0.0"

    assert result.original_data["nested"]["value"] == 42
    assert result.original_data["version"] == "1.0.0"

    rolled_back = result.rollback()
    assert rolled_back["nested"]["value"] == 42
    assert rolled_back["version"] == "1.0.0"


def test_upgrade_with_both_context_string():
    """Test upgrade with BOTH context using string value."""

    def upgrade_func(data):
        data["version"] = "2.0.0"
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="upgrade_both",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        context="BOTH",
    )

    data = {"version": "1.0.0"}
    _result, applied = apply_upgrades(data, [step], context="DATA")
    assert applied == ["upgrade_both"]

    data = {"version": "1.0.0"}
    _result, applied = apply_upgrades(data, [step], context="SYSTEM")
    assert applied == ["upgrade_both"]
