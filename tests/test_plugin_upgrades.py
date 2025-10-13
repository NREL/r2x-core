"""Tests for plugin manager upgrade step functionality."""

from r2x_core.plugins import PluginManager
from r2x_core.upgrader import UpgradeStep
from r2x_core.versioning import SemanticVersioningStrategy


def test_register_upgrade_step():
    """Test registering an upgrade step for a plugin."""

    def upgrade_func(data):
        data["upgraded"] = True
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="test_upgrade", func=upgrade_func, target_version="2.0.0", versioning_strategy=strategy
    )

    PluginManager.register_upgrade_step("test_plugin", step)

    steps = PluginManager.get_upgrade_steps("test_plugin")
    assert len(steps) == 1
    assert steps[0].name == "test_upgrade"


def test_get_upgrade_steps_empty():
    """Test getting upgrade steps for plugin with no steps."""
    steps = PluginManager.get_upgrade_steps("nonexistent_plugin")
    assert len(steps) == 0


def test_get_upgrade_steps_sorted_by_priority():
    """Test that upgrade steps are returned sorted by priority."""

    def upgrade_func(data):
        return data

    strategy = SemanticVersioningStrategy()

    step1 = UpgradeStep(
        name="high_priority",
        func=upgrade_func,
        target_version="2.0.0",
        versioning_strategy=strategy,
        priority=50,
    )

    step2 = UpgradeStep(
        name="low_priority",
        func=upgrade_func,
        target_version="3.0.0",
        versioning_strategy=strategy,
        priority=200,
    )

    PluginManager.register_upgrade_step("priority_test", step1)
    PluginManager.register_upgrade_step("priority_test", step2)

    steps = PluginManager.get_upgrade_steps("priority_test")
    assert len(steps) == 2
    assert steps[0].name == "high_priority"  # Lower priority number comes first
    assert steps[1].name == "low_priority"


def test_registered_upgrade_steps_property():
    """Test the registered_upgrade_steps property."""

    def upgrade_func(data):
        return data

    strategy = SemanticVersioningStrategy()
    step = UpgradeStep(
        name="property_test", func=upgrade_func, target_version="1.0.0", versioning_strategy=strategy
    )

    PluginManager.register_upgrade_step("property_plugin", step)

    manager = PluginManager()
    all_steps = manager.registered_upgrade_steps

    assert "property_plugin" in all_steps
    assert len(all_steps["property_plugin"]) == 1
    assert all_steps["property_plugin"][0].name == "property_test"


def test_multiple_plugins_upgrade_steps():
    """Test that upgrade steps are properly isolated between plugins."""

    def upgrade_func(data):
        return data

    strategy = SemanticVersioningStrategy()

    step1 = UpgradeStep(
        name="plugin1_upgrade", func=upgrade_func, target_version="1.0.0", versioning_strategy=strategy
    )

    step2 = UpgradeStep(
        name="plugin2_upgrade", func=upgrade_func, target_version="2.0.0", versioning_strategy=strategy
    )

    PluginManager.register_upgrade_step("plugin1", step1)
    PluginManager.register_upgrade_step("plugin2", step2)

    plugin1_steps = PluginManager.get_upgrade_steps("plugin1")
    plugin2_steps = PluginManager.get_upgrade_steps("plugin2")

    assert len(plugin1_steps) == 1
    assert len(plugin2_steps) == 1
    assert plugin1_steps[0].name == "plugin1_upgrade"
    assert plugin2_steps[0].name == "plugin2_upgrade"
