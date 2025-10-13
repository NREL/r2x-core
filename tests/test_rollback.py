"""Tests for upgrade rollback functionality."""

from r2x_core.upgrader import (
    UpgradeResult,
    UpgradeStep,
    apply_upgrades_with_rollback,
)
from r2x_core.versioning import SemanticVersioningStrategy


def test_upgrade_result_initialization():
    """Test UpgradeResult initialization."""
    data = {"version": "1.0.0", "value": 10}
    result = UpgradeResult(data)

    assert result.original_data == {"version": "1.0.0", "value": 10}
    assert result.current_data == {"version": "1.0.0", "value": 10}
    assert result.applied_steps == []


def test_upgrade_result_add_step():
    """Test adding upgrade steps to result."""
    data = {"version": "1.0.0", "value": 10}
    result = UpgradeResult(data)

    # Add first step
    new_data = {"version": "2.0.0", "value": 20}
    result.add_step("upgrade_v2", new_data)

    assert result.current_data == {"version": "2.0.0", "value": 20}
    assert result.applied_steps == ["upgrade_v2"]

    # Add second step
    newer_data = {"version": "3.0.0", "value": 30}
    result.add_step("upgrade_v3", newer_data)

    assert result.current_data == {"version": "3.0.0", "value": 30}
    assert result.applied_steps == ["upgrade_v2", "upgrade_v3"]


def test_upgrade_result_rollback_all():
    """Test rolling back all upgrades."""
    data = {"version": "1.0.0", "value": 10}
    result = UpgradeResult(data)

    result.add_step("upgrade_v2", {"version": "2.0.0", "value": 20})
    result.add_step("upgrade_v3", {"version": "3.0.0", "value": 30})

    # Rollback all
    rolled_back = result.rollback()

    assert rolled_back == {"version": "1.0.0", "value": 10}
    assert result.current_data == {"version": "1.0.0", "value": 10}
    assert result.applied_steps == []


def test_upgrade_result_with_multiple_steps():
    """Test adding multiple steps."""
    data = {"version": "1.0.0", "value": 10}
    result = UpgradeResult(data)

    result.add_step("upgrade_v2", {"version": "2.0.0", "value": 20})
    result.add_step("upgrade_v3", {"version": "3.0.0", "value": 30})

    assert result.current_data == {"version": "3.0.0", "value": 30}
    assert result.applied_steps == ["upgrade_v2", "upgrade_v3"]

    # Rollback all
    rolled_back = result.rollback()

    assert rolled_back == {"version": "1.0.0", "value": 10}
    assert result.current_data == {"version": "1.0.0", "value": 10}
    assert result.applied_steps == []


def test_apply_upgrades_with_rollback_basic():
    """Test apply_upgrades_with_rollback returns UpgradeResult."""

    def upgrade_v2(data):
        data["version"] = "2.0.0"
        data["upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()
    steps = [
        UpgradeStep(
            name="upgrade_to_v2",
            func=upgrade_v2,
            target_version="2.0.0",
            versioning_strategy=strategy,
        )
    ]

    data = {"version": "1.0.0"}
    result = apply_upgrades_with_rollback(data, steps)

    assert isinstance(result, UpgradeResult)
    assert result.current_data["version"] == "2.0.0"
    assert result.current_data["upgraded"] is True
    assert result.applied_steps == ["upgrade_to_v2"]


def test_apply_upgrades_with_rollback_multiple_steps():
    """Test multiple upgrades with all-or-nothing rollback."""

    def upgrade_v2(data):
        data["version"] = "2.0.0"
        data["field_v2"] = "added_in_v2"
        return data

    def upgrade_v3(data):
        data["version"] = "3.0.0"
        data["field_v3"] = "added_in_v3"
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
            name="upgrade_to_v3",
            func=upgrade_v3,
            target_version="3.0.0",
            versioning_strategy=strategy,
            priority=20,
        ),
    ]

    data = {"version": "1.0.0"}
    result = apply_upgrades_with_rollback(data, steps)

    assert result.current_data["version"] == "3.0.0"
    assert result.applied_steps == ["upgrade_to_v2", "upgrade_to_v3"]

    # Rollback all upgrades
    result.rollback()
    assert result.current_data["version"] == "1.0.0"
    assert "field_v2" not in result.current_data
    assert "field_v3" not in result.current_data
    assert result.applied_steps == []


def test_apply_upgrades_with_rollback_error_continue():
    """Test continuing on error without rollback."""

    def upgrade_v2(data):
        data["version"] = "2.0.0"
        return data

    def upgrade_v3_fails(data):
        raise RuntimeError("Upgrade failed")

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
            name="upgrade_to_v3",
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
    result = apply_upgrades_with_rollback(data, steps, stop_on_error=False)

    # v2 and v4 should be applied, v3 skipped due to error
    assert result.current_data["version"] == "4.0.0"
    assert result.applied_steps == ["upgrade_to_v2", "upgrade_to_v4"]


def test_apply_upgrades_with_rollback_error_stop():
    """Test stopping on error with automatic rollback."""

    def upgrade_v2(data):
        data["version"] = "2.0.0"
        return data

    def upgrade_v3_fails(data):
        raise RuntimeError("Upgrade failed")

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
            name="upgrade_to_v3",
            func=upgrade_v3_fails,
            target_version="3.0.0",
            versioning_strategy=strategy,
            priority=20,
        ),
    ]

    data = {"version": "1.0.0"}
    result = apply_upgrades_with_rollback(data, steps, stop_on_error=True)

    # Should rollback to original due to error
    assert result.current_data["version"] == "1.0.0"
    assert result.applied_steps == []


def test_apply_upgrades_with_rollback_context_filter():
    """Test context filtering with rollback."""

    def upgrade_data(data):
        data["data_upgraded"] = True
        return data

    def upgrade_system(data):
        data["system_upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()
    steps = [
        UpgradeStep(
            name="data_upgrade",
            func=upgrade_data,
            target_version="2.0.0",
            versioning_strategy=strategy,
            context="data",
        ),
        UpgradeStep(
            name="system_upgrade",
            func=upgrade_system,
            target_version="2.0.0",
            versioning_strategy=strategy,
            context="system",
        ),
    ]

    data = {"version": "1.0.0"}
    result = apply_upgrades_with_rollback(data, steps, context="data")

    assert result.applied_steps == ["data_upgrade"]
    assert "data_upgraded" in result.current_data
    assert "system_upgraded" not in result.current_data


def test_upgrade_result_preserves_original():
    """Test that original data is never modified."""
    data = {"version": "1.0.0", "nested": {"value": 10}}
    result = UpgradeResult(data)

    # Modify current data
    result.add_step("step1", {"version": "2.0.0", "nested": {"value": 20}})

    # Original should be unchanged
    assert data == {"version": "1.0.0", "nested": {"value": 10}}
    assert result.original_data == {"version": "1.0.0", "nested": {"value": 10}}
    assert result.current_data == {"version": "2.0.0", "nested": {"value": 20}}
