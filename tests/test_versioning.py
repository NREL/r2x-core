"""Tests for the versioning system."""

from r2x_core.upgrader import UpgradeStep, apply_upgrade, apply_upgrades
from r2x_core.versioning import (
    FileModTimeStrategy,
    GitVersioningStrategy,
    SemanticVersioningStrategy,
)


def test_semantic_versioning_strategy_get_version_from_dict():
    """Test getting version from dictionary."""
    strategy = SemanticVersioningStrategy()
    data = {"version": "1.2.3", "other": "data"}
    version = strategy.get_version(data)
    assert version == "1.2.3"


def test_semantic_versioning_strategy_get_version_missing():
    """Test getting missing version returns None."""
    strategy = SemanticVersioningStrategy()
    data = {"other": "data"}
    version = strategy.get_version(data)
    assert version is None


def test_semantic_versioning_strategy_get_version_custom_field():
    """Test getting version from custom field."""
    strategy = SemanticVersioningStrategy(version_field="schema_version")
    data = {"schema_version": "2.0.0"}
    version = strategy.get_version(data)
    assert version == "2.0.0"


def test_semantic_versioning_strategy_set_version():
    """Test setting version in dictionary."""
    strategy = SemanticVersioningStrategy()
    data = {"other": "data"}
    updated = strategy.set_version(data, "1.0.0")
    assert updated["version"] == "1.0.0"
    assert updated["other"] == "data"


def test_semantic_versioning_strategy_compare_less():
    """Test version comparison: current < target."""
    strategy = SemanticVersioningStrategy()
    result = strategy.compare("1.0.0", "2.0.0")
    assert result == -1


def test_semantic_versioning_strategy_compare_equal():
    """Test version comparison: current == target."""
    strategy = SemanticVersioningStrategy()
    result = strategy.compare("1.0.0", "1.0.0")
    assert result == 0


def test_semantic_versioning_strategy_compare_greater():
    """Test version comparison: current > target."""
    strategy = SemanticVersioningStrategy()
    result = strategy.compare("2.0.0", "1.0.0")
    assert result == 1


def test_semantic_versioning_strategy_compare_none_current():
    """Test version comparison with None current version."""
    strategy = SemanticVersioningStrategy()
    result = strategy.compare(None, "1.0.0")
    assert result == -1


def test_git_versioning_strategy_get_version():
    """Test getting git version from data."""
    strategy = GitVersioningStrategy()
    data = {"git_version": "abc123", "other": "data"}
    version = strategy.get_version(data)
    assert version == "abc123"


def test_git_versioning_strategy_set_version():
    """Test setting git version in data."""
    strategy = GitVersioningStrategy()
    data = {"other": "data"}
    updated = strategy.set_version(data, "def456")
    assert updated["git_version"] == "def456"


def test_git_versioning_strategy_compare_hashes():
    """Test comparing git commit hashes."""
    strategy = GitVersioningStrategy()
    result = strategy.compare("abc123", "def456")
    assert result == -1  # "abc123" < "def456" lexically


def test_git_versioning_strategy_compare_timestamps():
    """Test comparing git timestamps."""
    strategy = GitVersioningStrategy(use_timestamps=True)
    current = "2023-01-01T10:00:00Z"
    target = "2023-01-01T11:00:00Z"
    result = strategy.compare(current, target)
    assert result == -1


def test_file_mod_time_strategy_get_version(tmp_path):
    """Test getting file modification time as version."""
    strategy = FileModTimeStrategy()
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    version = strategy.get_version(test_file)
    assert version is not None
    assert float(version) > 0


def test_file_mod_time_strategy_get_version_missing():
    """Test getting version for non-existent file."""
    strategy = FileModTimeStrategy()
    version = strategy.get_version("nonexistent.txt")
    assert version is None


def test_file_mod_time_strategy_compare():
    """Test comparing file modification times."""
    strategy = FileModTimeStrategy()
    earlier = "1640995200.0"  # 2022-01-01 00:00:00
    later = "1672531200.0"  # 2023-01-01 00:00:00

    result = strategy.compare(earlier, later)
    assert result == -1


def test_upgrade_step_creation():
    """Test creating an UpgradeStep."""

    def upgrade_func(data):
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_upgrade",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        priority=100,
    )

    assert step.name == "test_upgrade"
    assert step.func == upgrade_func
    assert step.target_version == "2.0.0"
    assert step.priority == 100


def test_apply_upgrade_needed():
    """Test applying upgrade when version is outdated."""

    def upgrade_func(data):
        data["upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_upgrade", func=upgrade_func, target_version="2.0.0", versioning_strategy=strategy
    )

    data = {"version": "1.0.0", "content": "test"}
    result, applied = apply_upgrade(data, step)

    assert applied is True
    assert result["upgraded"] is True
    assert result["version"] == "2.0.0"
    assert result["content"] == "test"


def test_apply_upgrade_not_needed():
    """Test skipping upgrade when version is current."""

    def upgrade_func(data):
        data["upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_upgrade", func=upgrade_func, target_version="2.0.0", versioning_strategy=strategy
    )

    data = {"version": "2.0.0", "content": "test"}
    result, applied = apply_upgrade(data, step)

    assert applied is False
    assert "upgraded" not in result
    assert result["version"] == "2.0.0"


def test_apply_upgrade_version_too_new():
    """Test skipping upgrade when current version is newer."""

    def upgrade_func(data):
        data["upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_upgrade", func=upgrade_func, target_version="2.0.0", versioning_strategy=strategy
    )

    data = {"version": "3.0.0", "content": "test"}
    result, applied = apply_upgrade(data, step)

    assert applied is False
    assert "upgraded" not in result
    assert result["version"] == "3.0.0"


def test_apply_upgrades_multiple():
    """Test applying multiple upgrades in priority order."""

    def upgrade_v2(data):
        data["v2_applied"] = True
        return data

    def upgrade_v3(data):
        data["v3_applied"] = True
        return data

    strategy = SemanticVersioningStrategy()

    steps = [
        UpgradeStep(
            name="upgrade_v3",
            func=upgrade_v3,
            target_version="3.0.0",
            versioning_strategy=strategy,
            priority=200,  # Higher priority (runs second)
        ),
        UpgradeStep(
            name="upgrade_v2",
            func=upgrade_v2,
            target_version="2.0.0",
            versioning_strategy=strategy,
            priority=100,  # Lower priority (runs first)
        ),
    ]

    data = {"version": "1.0.0"}
    result, applied = apply_upgrades(data, steps)

    assert len(applied) == 2
    assert "upgrade_v2" in applied
    assert "upgrade_v3" in applied
    assert result["v2_applied"] is True
    assert result["v3_applied"] is True
    assert result["version"] == "3.0.0"  # Final version


def test_apply_upgrades_context_filter():
    """Test filtering upgrades by context."""

    def upgrade_func(data):
        data["upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()

    steps = [
        UpgradeStep(
            name="data_upgrade",
            func=upgrade_func,
            target_version="2.0.0",
            versioning_strategy=strategy,
            context="data",
        ),
        UpgradeStep(
            name="system_upgrade",
            func=upgrade_func,
            target_version="3.0.0",
            versioning_strategy=strategy,
            context="system",
        ),
    ]

    data = {"version": "1.0.0"}
    _result, applied = apply_upgrades(data, steps, context="data")

    assert len(applied) == 1
    assert "data_upgrade" in applied
    assert "system_upgrade" not in applied


def test_upgrade_step_version_constraints():
    """Test upgrade step with version constraints."""

    def upgrade_func(data):
        data["upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="constrained_upgrade",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        min_version="1.5.0",
        max_version="1.9.0",
    )

    # Test with version too low
    data = {"version": "1.0.0"}
    _result, applied = apply_upgrade(data, step)
    assert applied is False

    # Test with version in range
    data = {"version": "1.7.0"}
    _result, applied = apply_upgrade(data, step)
    assert applied is True

    # Test with version too high
    data = {"version": "2.5.0"}
    _result, applied = apply_upgrade(data, step)
    assert applied is False


def test_semantic_versioning_requires_packaging():
    """Test that SemanticVersioningStrategy requires packaging library."""
    # This test would need to mock the import to test the error case
    # For now, just test that it works when packaging is available
    strategy = SemanticVersioningStrategy()
    assert strategy.default_version == "0.0.0"


def test_versioning_strategy_with_object():
    """Test versioning strategy with object that has version attribute."""

    class MockObject:
        def __init__(self, version):
            self.version = version

    strategy = SemanticVersioningStrategy()
    obj = MockObject("1.5.0")

    version = strategy.get_version(obj)
    assert version == "1.5.0"

    strategy.set_version(obj, "2.0.0")
    assert obj.version == "2.0.0"


def test_git_strategy_invalid_timestamp():
    """Test git strategy with invalid timestamp format."""
    strategy = GitVersioningStrategy(use_timestamps=True)
    # Should handle invalid format gracefully
    result = strategy.compare("invalid-time", "2023-01-01T10:00:00Z")
    assert result == -1  # Defaults to -1 on error
