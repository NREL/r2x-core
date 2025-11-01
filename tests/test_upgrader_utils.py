"""Comprehensive tests for upgrader_utils module with example upgrade steps."""

from r2x_core.upgrader_utils import UpgradeStep, UpgradeType, run_upgrade_step, shall_we_upgrade
from r2x_core.versioning import SemanticVersioningStrategy


def upgrade_v1_to_v2(data: dict) -> dict:
    """Example upgrade function: add new field."""
    data["version"] = "2.0"
    data["upgraded"] = True
    return data


def upgrade_v2_to_v3(data: dict) -> dict:
    """Example upgrade function: transform existing field."""
    if "old_field" in data:
        data["new_field"] = data.pop("old_field").upper()
    data["version"] = "3.0"
    return data


def upgrade_with_context(data: dict, upgrader_context=None) -> dict:
    """Example upgrade function that accepts upgrader_context."""
    if upgrader_context:
        data["context_applied"] = upgrader_context.get("name", "unknown")
    data["version"] = "1.5"
    return data


def upgrade_failing_step(data: dict) -> dict:
    """Example upgrade function that raises an exception."""
    raise ValueError("This upgrade intentionally fails")


def upgrade_with_validation(data: dict) -> dict:
    """Example upgrade function with validation."""
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")
    if "required_field" not in data:
        raise KeyError("Missing required_field")
    data["validated"] = True
    return data


def upgrade_data_transformation(data: dict) -> dict:
    """Example upgrade that transforms data structure."""
    return {
        "version": "2.5",
        "original_data": data,
        "timestamp": "2024-10-31",
    }


def test_shall_we_upgrade_no_strategy():
    """Test with no strategy returns False."""
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    result = shall_we_upgrade(step, "1.0", strategy=None)
    assert result.is_ok()
    assert result.unwrap() is False


def test_shall_we_upgrade_current_less_than_target():
    """Test when current version is less than target."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    result = shall_we_upgrade(step, "1.0", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is True


def test_shall_we_upgrade_current_equal_to_target():
    """Test when current version equals target version."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    result = shall_we_upgrade(step, "2.0", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is False


def test_shall_we_upgrade_current_greater_than_target():
    """Test when current version is greater than target."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    result = shall_we_upgrade(step, "3.0", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is False


def test_shall_we_upgrade_with_min_version_below():
    """Test when current version is below minimum."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
        min_version="1.5",
    )
    result = shall_we_upgrade(step, "1.0", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is False


def test_shall_we_upgrade_with_min_version_met():
    """Test when current version meets minimum."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
        min_version="1.0",
    )
    result = shall_we_upgrade(step, "1.5", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is True


def test_shall_we_upgrade_with_max_version_exceeded():
    """Test when current version exceeds maximum."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
        max_version="2.5",
    )
    result = shall_we_upgrade(step, "3.0", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is False


def test_shall_we_upgrade_with_max_version_met():
    """Test when current version within maximum."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
        max_version="2.5",
    )
    result = shall_we_upgrade(step, "1.5", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is True


def test_shall_we_upgrade_with_both_min_and_max():
    """Test with both min and max constraints."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
        min_version="1.0",
        max_version="2.5",
    )
    result = shall_we_upgrade(step, "1.5", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is True


def test_shall_we_upgrade_outside_range_below():
    """Test when version is below valid range."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
        min_version="1.5",
        max_version="2.5",
    )
    result = shall_we_upgrade(step, "1.0", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is False


def test_shall_we_upgrade_outside_range_above():
    """Test when version is above valid range."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
        min_version="1.5",
        max_version="2.5",
    )
    result = shall_we_upgrade(step, "3.0", strategy=strategy)
    assert result.is_ok()
    assert result.unwrap() is False


def test_run_upgrade_step_successful():
    """Test successful upgrade step execution."""
    step = UpgradeStep(
        name="upgrade_v1_to_v2",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    data = {"version": "1.0", "value": 42}
    result = run_upgrade_step(step, data)

    assert result.is_ok()
    upgraded_data = result.unwrap()
    assert upgraded_data["version"] == "2.0"
    assert upgraded_data["upgraded"] is True
    assert upgraded_data["value"] == 42


def test_run_upgrade_step_with_context():
    """Test upgrade step with upgrader context."""
    step = UpgradeStep(
        name="upgrade_with_context",
        func=upgrade_with_context,
        target_version="1.5",
        upgrade_type=UpgradeType.SYSTEM,
    )
    data = {"original": "data"}
    context = {"name": "test_upgrader"}
    result = run_upgrade_step(step, data, upgrader_context=context)

    assert result.is_ok()
    upgraded_data = result.unwrap()
    assert upgraded_data["context_applied"] == "test_upgrader"
    assert upgraded_data["version"] == "1.5"


def test_run_upgrade_step_without_context_required():
    """Test upgrade step that doesn't require context."""
    step = UpgradeStep(
        name="upgrade_v2_to_v3",
        func=upgrade_v2_to_v3,
        target_version="3.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    data = {"version": "2.0", "old_field": "lower_case"}
    result = run_upgrade_step(step, data)

    assert result.is_ok()
    upgraded_data = result.unwrap()
    assert upgraded_data["version"] == "3.0"
    assert upgraded_data["new_field"] == "LOWER_CASE"
    assert "old_field" not in upgraded_data


def test_run_upgrade_step_failure():
    """Test upgrade step that fails."""
    step = UpgradeStep(
        name="failing_upgrade",
        func=upgrade_failing_step,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    data = {"version": "1.0"}
    result = run_upgrade_step(step, data)

    assert result.is_err()
    error = result.unwrap_err()
    assert "Failed failing_upgrade" in error
    assert "intentionally fails" in error


def test_run_upgrade_step_type_error():
    """Test upgrade step that raises TypeError."""
    step = UpgradeStep(
        name="validation_upgrade",
        func=upgrade_with_validation,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    data = "not a dict"
    result = run_upgrade_step(step, data)

    assert result.is_err()
    error = result.unwrap_err()
    assert "Failed validation_upgrade" in error


def test_run_upgrade_step_key_error():
    """Test upgrade step that raises KeyError."""
    step = UpgradeStep(
        name="validation_upgrade",
        func=upgrade_with_validation,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    data = {"other_field": "value"}
    result = run_upgrade_step(step, data)

    assert result.is_err()
    error = result.unwrap_err()
    assert "Failed validation_upgrade" in error


def test_run_upgrade_step_complex_transformation():
    """Test upgrade step with complex data transformation."""
    step = UpgradeStep(
        name="data_transformation",
        func=upgrade_data_transformation,
        target_version="2.5",
        upgrade_type=UpgradeType.SYSTEM,
    )
    data = {"old_format": {"nested": "data"}}
    result = run_upgrade_step(step, data)

    assert result.is_ok()
    upgraded_data = result.unwrap()
    assert upgraded_data["version"] == "2.5"
    assert upgraded_data["original_data"] == data
    assert "timestamp" in upgraded_data


def test_run_upgrade_step_preserves_data():
    """Test that upgrade preserves unmodified data."""
    step = UpgradeStep(
        name="passthrough",
        func=lambda x: x,
        target_version="1.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    data = {"keep": "this", "nested": {"also": "keep"}}
    result = run_upgrade_step(step, data)

    assert result.is_ok()
    assert result.unwrap() == data


def test_upgrade_step_basic_creation():
    """Test basic UpgradeStep creation."""
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.FILE,
    )
    assert step.name == "test_step"
    assert step.target_version == "2.0"
    assert step.upgrade_type == UpgradeType.FILE
    assert step.priority == 100  # default


def test_upgrade_step_with_version_constraints():
    """Test UpgradeStep with version constraints."""
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
        min_version="1.5",
        max_version="2.5",
    )
    assert step.min_version == "1.5"
    assert step.max_version == "2.5"


def test_upgrade_step_with_custom_priority():
    """Test UpgradeStep with custom priority."""
    step = UpgradeStep(
        name="test_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.FILE,
        priority=10,
    )
    assert step.priority == 10


def test_upgrade_step_file_type():
    """Test UpgradeStep with FILE upgrade type."""
    step = UpgradeStep(
        name="file_upgrade",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.FILE,
    )
    assert step.upgrade_type == UpgradeType.FILE


def test_upgrade_step_system_type():
    """Test UpgradeStep with SYSTEM upgrade type."""
    step = UpgradeStep(
        name="system_upgrade",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    assert step.upgrade_type == UpgradeType.SYSTEM


def test_upgrade_type_file():
    """Test FILE upgrade type value."""
    assert UpgradeType.FILE.value == "FILE"


def test_upgrade_type_system():
    """Test SYSTEM upgrade type value."""
    assert UpgradeType.SYSTEM.value == "SYSTEM"


def test_upgrade_type_is_string_enum():
    """Test UpgradeType is a string enum."""
    assert isinstance(UpgradeType.FILE, str)
    assert isinstance(UpgradeType.SYSTEM, str)


def test_upgrade_type_comparison():
    """Test UpgradeType value comparison."""
    assert UpgradeType.FILE == "FILE"
    assert UpgradeType.SYSTEM == "SYSTEM"


def test_multi_step_upgrade_chain():
    """Test chaining multiple upgrade steps."""
    # Create steps
    step1 = UpgradeStep(
        name="step1",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    step2 = UpgradeStep(
        name="step2",
        func=upgrade_v2_to_v3,
        target_version="3.0",
        upgrade_type=UpgradeType.SYSTEM,
    )

    # Execute chain
    data = {"version": "1.0", "old_field": "test_value"}

    result1 = run_upgrade_step(step1, data)
    assert result1.is_ok()
    data = result1.unwrap()

    result2 = run_upgrade_step(step2, data)
    assert result2.is_ok()
    data = result2.unwrap()

    assert data["version"] == "3.0"
    assert data["new_field"] == "TEST_VALUE"
    assert data["upgraded"] is True


def test_upgrade_with_version_check_and_execution():
    """Test complete workflow: check version then execute."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="upgrade_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )

    # Check if upgrade should run
    should_upgrade = shall_we_upgrade(step, "1.0", strategy=strategy)
    assert should_upgrade.is_ok()
    assert should_upgrade.unwrap() is True

    # Execute upgrade
    data = {"version": "1.0"}
    result = run_upgrade_step(step, data)
    assert result.is_ok()
    assert result.unwrap()["version"] == "2.0"


def test_upgrade_skip_when_version_too_high():
    """Test upgrade is skipped when version is already high."""
    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="upgrade_step",
        func=upgrade_v1_to_v2,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )

    # Check if upgrade should run (should be false)
    should_upgrade = shall_we_upgrade(step, "3.0", strategy=strategy)
    assert should_upgrade.is_ok()
    assert should_upgrade.unwrap() is False


def test_upgrade_with_context_parameter_detection():
    """Test that context parameter is correctly detected and passed."""
    step = UpgradeStep(
        name="context_step",
        func=upgrade_with_context,
        target_version="1.5",
        upgrade_type=UpgradeType.SYSTEM,
    )

    # Execute with context
    data = {"version": "1.0"}
    context = {"name": "my_upgrader"}
    result = run_upgrade_step(step, data, upgrader_context=context)

    assert result.is_ok()
    upgraded = result.unwrap()
    assert upgraded["context_applied"] == "my_upgrader"


def test_upgrade_error_includes_step_name():
    """Test that errors include the step name."""
    step = UpgradeStep(
        name="my_failing_step",
        func=upgrade_failing_step,
        target_version="2.0",
        upgrade_type=UpgradeType.SYSTEM,
    )

    result = run_upgrade_step(step, {})
    assert result.is_err()
    error = result.unwrap_err()
    assert "my_failing_step" in error


def test_upgrade_with_none_data():
    """Test upgrade step with None as data."""
    step = UpgradeStep(
        name="none_test",
        func=lambda x: {"wrapped": x},
        target_version="1.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    result = run_upgrade_step(step, None)
    assert result.is_ok()
    assert result.unwrap() == {"wrapped": None}


def test_upgrade_with_empty_dict():
    """Test upgrade step with empty dictionary."""
    step = UpgradeStep(
        name="empty_dict_test",
        func=lambda x: {**x, "added": True},
        target_version="1.0",
        upgrade_type=UpgradeType.SYSTEM,
    )
    result = run_upgrade_step(step, {})
    assert result.is_ok()
    assert result.unwrap() == {"added": True}


def test_upgrade_preserves_data_types():
    """Test that upgrade preserves various data types."""
    step = UpgradeStep(
        name="type_preservation",
        func=lambda x: x,
        target_version="1.0",
        upgrade_type=UpgradeType.SYSTEM,
    )

    test_data = {
        "string": "value",
        "integer": 42,
        "float": 3.14,
        "boolean": True,
        "list": [1, 2, 3],
        "nested": {"key": "value"},
    }

    result = run_upgrade_step(step, test_data)
    assert result.is_ok()
    assert result.unwrap() == test_data


def test_upgrade_with_large_data():
    """Test upgrade step with large data structure."""
    large_data = {"items": [{"id": i, "value": i * 2} for i in range(1000)]}

    step = UpgradeStep(
        name="large_data_test",
        func=lambda x: {**x, "processed": True},
        target_version="1.0",
        upgrade_type=UpgradeType.SYSTEM,
    )

    result = run_upgrade_step(step, large_data)
    assert result.is_ok()
    upgraded = result.unwrap()
    assert upgraded["processed"] is True
    assert len(upgraded["items"]) == 1000
