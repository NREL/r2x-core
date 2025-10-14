"""Test DataUpgrader base class implementation."""

from pathlib import Path

import pytest

from r2x_core import DataUpgrader, PluginManager, UpgradeType
from r2x_core.plugin_config import PluginConfig
from r2x_core.versioning import SemanticVersioningStrategy


class TestUpgrader(DataUpgrader):
    """Test upgrader implementation."""

    strategy = SemanticVersioningStrategy()

    @staticmethod
    def detect_version(folder: Path) -> str | None:
        """Detect version from folder."""
        version_file = folder / "version.txt"
        if version_file.exists():
            return version_file.read_text().strip()
        return None


# Register upgrade steps using decorator
@TestUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
    priority=50,
)
def rename_file(folder: Path) -> Path:
    """Rename a file."""
    old_file = folder / "old.txt"
    new_file = folder / "new.txt"
    if old_file.exists() and not new_file.exists():
        old_file.rename(new_file)
    return folder


@TestUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
    priority=100,
)
def add_metadata(folder: Path) -> Path:
    """Add metadata file."""
    metadata_file = folder / "metadata.txt"
    if not metadata_file.exists():
        metadata_file.write_text("version: 2.0.0\n")
    return folder


def test_upgrader_has_registered_steps():
    """Test that steps are registered to the upgrader class."""
    assert len(TestUpgrader.steps) > 0
    step_names = {step.name for step in TestUpgrader.steps}
    assert "rename_file" in step_names
    assert "add_metadata" in step_names


def test_upgrader_steps_sorted_by_priority():
    """Test that steps are sorted by priority."""
    priorities = [step.priority for step in TestUpgrader.steps]
    assert priorities == sorted(priorities), "Steps should be sorted by priority"


def test_detect_version(tmp_path):
    """Test version detection."""
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.5.0")
    assert TestUpgrader.detect_version(tmp_path) == "1.5.0"


def test_detect_version_missing(tmp_path):
    """Test version detection with missing file."""
    assert TestUpgrader.detect_version(tmp_path) is None


def test_upgrade_applies_all_steps(tmp_path):
    """Test that upgrade applies all registered steps."""
    # Setup v1 data
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.0.0")
    old_file = tmp_path / "old.txt"
    old_file.write_text("content")

    # Run upgrade
    upgraded = TestUpgrader.upgrade(tmp_path)

    # Verify all steps were applied
    assert not (upgraded / "old.txt").exists(), "old.txt should be renamed"
    assert (upgraded / "new.txt").exists(), "new.txt should exist"
    assert (upgraded / "metadata.txt").exists(), "metadata.txt should exist"


def test_upgrade_idempotent(tmp_path):
    """Test that running upgrade twice is safe."""
    # Setup v1 data
    version_file = tmp_path / "version.txt"
    version_file.write_text("1.0.0")
    old_file = tmp_path / "old.txt"
    old_file.write_text("content")

    # Run upgrade twice
    TestUpgrader.upgrade(tmp_path)
    upgraded = TestUpgrader.upgrade(tmp_path)

    # Should still be valid
    assert not (upgraded / "old.txt").exists()
    assert (upgraded / "new.txt").exists()
    assert (upgraded / "metadata.txt").exists()


def test_plugin_manager_get_upgrader():
    """Test PluginManager.get_upgrader() returns upgrader class."""

    class TestConfig(PluginConfig):
        """Test config."""

        name: str = "test"

    # Register plugin with upgrader
    PluginManager.register_model_plugin(
        name="test_upgrader",
        config=TestConfig,
        upgrader=TestUpgrader,
    )

    # Get upgrader via PluginManager
    manager = PluginManager()
    upgrader_class = manager.get_upgrader(TestConfig)

    assert upgrader_class is TestUpgrader, "Should return the TestUpgrader class"
    assert len(upgrader_class.steps) > 0, "Should have registered steps"


def test_plugin_manager_get_upgrader_not_registered():
    """Test PluginManager.get_upgrader() raises for unregistered config."""

    class UnregisteredConfig(PluginConfig):
        """Unregistered config."""

        name: str = "unregistered"

    manager = PluginManager()

    with pytest.raises(KeyError, match="not registered"):
        manager.get_upgrader(UnregisteredConfig)


def test_plugin_manager_get_upgrader_no_upgrader():
    """Test PluginManager.get_upgrader() returns None when plugin has no upgrader."""

    class NoUpgraderConfig(PluginConfig):
        """Config without upgrader."""

        name: str = "no_upgrader"

    # Register plugin WITHOUT upgrader
    PluginManager.register_model_plugin(
        name="no_upgrader",
        config=NoUpgraderConfig,
    )

    manager = PluginManager()

    result = manager.get_upgrader(NoUpgraderConfig)
    assert result is None


def test_upgrader_strategy_required():
    """Test that upgrader without strategy cannot be instantiated."""
    # This test verifies the ABC contract
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):

        class BadUpgrader(DataUpgrader):
            """Upgrader missing strategy."""

            @staticmethod
            def detect_version(folder: Path) -> str | None:
                return None

        # Try to instantiate (should fail)
        BadUpgrader()


def test_upgrader_detect_version_required():
    """Test that upgrader without detect_version cannot be instantiated."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):

        class BadUpgrader2(DataUpgrader):
            """Upgrader missing detect_version."""

            strategy = SemanticVersioningStrategy()

        # Try to instantiate (should fail)
        BadUpgrader2()
