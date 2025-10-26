"""Test DataUpgrader base class implementation."""

from pathlib import Path
from typing import Any

import pytest

from r2x_core import PluginUpgrader, UpgradeType
from r2x_core.versioning import GitVersioningStrategy, SemanticVersioningStrategy, VersionDetector


@pytest.fixture
def upgrader_class():
    class TestUpgrader(PluginUpgrader): ...

    return TestUpgrader


@pytest.fixture
def data_folder(tmp_path):
    (tmp_path / "old.txt").write_text("content")
    return tmp_path


@pytest.fixture
def system_data():
    return {"version": "1.0", "name": "test"}


@pytest.fixture
def semantic_strategy():
    return SemanticVersioningStrategy()


@pytest.fixture
def version_detector(tmp_path):
    class SimpleVersionDetector(VersionDetector):
        def detect_version(self, folder_path: Path) -> str | None:
            version_file = folder_path / "version.txt"
            if version_file.exists():
                return version_file.read_text().strip()
            return None

    return SimpleVersionDetector()


def test_register_upgrade_step(upgrader_class):
    @upgrader_class.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=50,
    )
    def upgrade_func(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        return folder

    assert len(upgrader_class.registered_steps()) == 1
    assert upgrader_class.registered_steps()[0].name == "upgrade_func"


def test_upgrade_step_attributes(upgrader_class):
    @upgrader_class.register_upgrade_step(
        target_version="3.0.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=10,
    )
    def my_upgrade(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        return folder

    step = upgrader_class.registered_steps()[0]
    assert step.target_version == "3.0.0"
    assert step.upgrade_type == UpgradeType.SYSTEM
    assert step.priority == 10


def test_subclass_has_independent_registry():
    class FirstUpgrader(PluginUpgrader): ...

    class SecondUpgrader(PluginUpgrader): ...

    @FirstUpgrader.register_upgrade_step(
        target_version="1.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def first_func(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        return folder

    @SecondUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=2,
    )
    def second_func(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        return folder

    assert len(FirstUpgrader.registered_steps()) == 1
    assert len(SecondUpgrader.registered_steps()) == 1
    assert FirstUpgrader.registered_steps()[0].name == "first_func"
    assert SecondUpgrader.registered_steps()[0].name == "second_func"


def test_upgrade_data_files_rename(data_folder, semantic_strategy):
    class RenameUpgrader(PluginUpgrader): ...

    @RenameUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def rename_file(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        old_file = folder / "old.txt"
        new_file = folder / "new.txt"
        old_file.rename(new_file)
        return new_file

    upgrader = RenameUpgrader(strategy=semantic_strategy, version="1.0.0")
    result = upgrader.upgrade_data_files(data_folder)

    assert result
    assert not (data_folder / "old.txt").exists()
    assert (data_folder / "new.txt").exists()


def test_upgrade_data_files_create(data_folder, semantic_strategy):
    class CreateUpgrader(PluginUpgrader): ...

    @CreateUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def create_file(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        new_file = folder / "metadata.txt"
        new_file.write_text("metadata")
        return new_file

    upgrader = CreateUpgrader(strategy=semantic_strategy, version="1.0.0")
    result = upgrader.upgrade_data_files(data_folder)

    assert result
    assert (data_folder / "metadata.txt").exists()
    assert (data_folder / "metadata.txt").read_text() == "metadata"


def test_upgrade_system_data_add_key(system_data, semantic_strategy):
    class AddKeyUpgrader(PluginUpgrader): ...

    @AddKeyUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=1,
    )
    def add_key(data: dict[str, Any], upgrader_context: dict[str, Any] | None = None) -> dict[str, Any]:
        data["new_field"] = "new_value"
        return data

    upgrader = AddKeyUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_system_data(system_data)

    assert "new_field" in system_data
    assert system_data["new_field"] == "new_value"
    assert system_data["name"] == "test"


def test_upgrade_system_data_modify_key(system_data, semantic_strategy):
    class ModifyKeyUpgrader(PluginUpgrader): ...

    @ModifyKeyUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=1,
    )
    def modify_version(
        data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data["version"] = "2.0"
        return data

    upgrader = ModifyKeyUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_system_data(system_data)

    assert system_data["version"] == "2.0"
    assert system_data["name"] == "test"


def test_upgrade_data_files_with_context(data_folder, semantic_strategy):
    class ContextUpgrader(PluginUpgrader): ...

    @ContextUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def create_with_context(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        suffix = upgrader_context.get("suffix", "default") if upgrader_context else "default"
        new_file = folder / f"file_{suffix}.txt"
        new_file.write_text(f"content_{suffix}")
        return new_file

    context = {"suffix": "custom"}
    upgrader = ContextUpgrader(strategy=semantic_strategy, version="1.0.0")
    result = upgrader.upgrade_data_files(data_folder, upgrader_context=context)

    assert result
    assert (data_folder / "file_custom.txt").exists()
    assert (data_folder / "file_custom.txt").read_text() == "content_custom"


def test_upgrade_system_data_with_context(system_data, semantic_strategy):
    class ContextSystemUpgrader(PluginUpgrader): ...

    @ContextSystemUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=1,
    )
    def add_from_context(
        data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if upgrader_context:
            data["author"] = upgrader_context.get("author", "unknown")
            data["timestamp"] = upgrader_context.get("timestamp", 0)
        return data

    context = {"author": "alice", "timestamp": 123456}
    upgrader = ContextSystemUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_system_data(system_data, upgrader_context=context)

    assert system_data["author"] == "alice"
    assert system_data["timestamp"] == 123456
    assert system_data["version"] == "1.0"


def test_upgrade_context_none_is_safe(data_folder, semantic_strategy):
    class SafeUpgrader(PluginUpgrader): ...

    @SafeUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def handle_none_context(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        value = upgrader_context.get("key", "fallback") if upgrader_context else "fallback"
        new_file = folder / f"{value}.txt"
        new_file.write_text(value)
        return new_file

    upgrader = SafeUpgrader(strategy=semantic_strategy, version="1.0.0")
    result = upgrader.upgrade_data_files(data_folder)

    assert result
    assert (data_folder / "fallback.txt").exists()
    assert (data_folder / "fallback.txt").read_text() == "fallback"


def test_upgrade_steps_run_in_priority_order(data_folder, semantic_strategy):
    class OrderedUpgrader(PluginUpgrader): ...

    @OrderedUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=30,
    )
    def second_step(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        log_file = folder / "execution.log"
        log_file.write_text(log_file.read_text() + "second\n")
        return log_file

    @OrderedUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=10,
    )
    def first_step(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        log_file = folder / "execution.log"
        log_file.write_text("first\n")
        return log_file

    @OrderedUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=50,
    )
    def third_step(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        log_file = folder / "execution.log"
        log_file.write_text(log_file.read_text() + "third\n")
        return log_file

    upgrader = OrderedUpgrader(strategy=semantic_strategy, version="1.0.0")
    result = upgrader.upgrade_data_files(data_folder)

    assert result
    log_content = (data_folder / "execution.log").read_text()
    assert log_content == "first\nsecond\nthird\n"


def test_upgrade_with_semantic_versioning(data_folder, semantic_strategy):
    class SemanticUpgrader(PluginUpgrader): ...

    @SemanticUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_to_v2(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v2.txt").write_text("upgraded to v2")
        return folder

    upgrader = SemanticUpgrader(strategy=semantic_strategy, version="1.5.0")
    result = upgrader.upgrade_data_files(data_folder)

    assert result
    assert (data_folder / "v2.txt").exists()


def test_upgrade_with_git_versioning(data_folder):
    class GitUpgrader(PluginUpgrader): ...

    @GitUpgrader.register_upgrade_step(
        target_version="def5678",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_to_def(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "git.txt").write_text("upgraded to def5678")
        return folder

    commit_history = ["abc1234", "def5678", "ghi9012"]
    git_strategy = GitVersioningStrategy(commit_history)
    upgrader = GitUpgrader(strategy=git_strategy, version="abc1234")
    result = upgrader.upgrade_data_files(data_folder)

    assert result
    assert (data_folder / "git.txt").exists()


def test_upgrade_with_version_detector(data_folder, semantic_strategy, version_detector):
    class DetectorUpgrader(PluginUpgrader): ...

    @DetectorUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_detected(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "detected.txt").write_text("auto-detected version")
        return folder

    (data_folder / "version.txt").write_text("1.0.0")

    upgrader = DetectorUpgrader(
        strategy=semantic_strategy, version_detector=version_detector, folder_path=data_folder
    )
    result = upgrader.upgrade_data_files(data_folder)

    assert result
    assert upgrader.version == "1.0.0"
    assert (data_folder / "detected.txt").exists()
