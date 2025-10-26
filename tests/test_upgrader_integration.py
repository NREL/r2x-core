from pathlib import Path
from typing import Any

import pytest

from r2x_core import PluginUpgrader, UpgradeType
from r2x_core.exceptions import UpgradeError
from r2x_core.versioning import GitVersioningStrategy, SemanticVersioningStrategy, VersionDetector


@pytest.fixture
def semantic_strategy():
    return SemanticVersioningStrategy()


@pytest.fixture
def git_strategy():
    commit_history = ["abc123", "def456", "ghi789", "jkl012"]
    return GitVersioningStrategy(commit_history)


@pytest.fixture
def version_detector():
    class FileVersionDetector(VersionDetector):
        @staticmethod
        def detect_version(folder_path: Path) -> str | None:
            version_file = folder_path / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()
            return None

    return FileVersionDetector()


@pytest.fixture
def data_folder(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "data.txt").write_text("original data")
    return folder


@pytest.fixture
def system_data():
    return {
        "version": "1.0.0",
        "name": "test_system",
        "components": ["comp1", "comp2"],
        "metadata": {"created": "2024-01-01"},
    }


def test_multi_version_file_upgrade_chain(data_folder, semantic_strategy):
    class MultiVersionUpgrader(PluginUpgrader): ...

    @MultiVersionUpgrader.register_upgrade_step(
        target_version="1.1.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_to_1_1_0(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v1.1.txt").write_text("upgraded to 1.1.0")
        return folder

    @MultiVersionUpgrader.register_upgrade_step(
        target_version="1.2.0",
        upgrade_type=UpgradeType.FILE,
        priority=2,
    )
    def upgrade_to_1_2_0(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v1.2.txt").write_text("upgraded to 1.2.0")
        return folder

    @MultiVersionUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=3,
    )
    def upgrade_to_2_0_0(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v2.0.txt").write_text("upgraded to 2.0.0")
        return folder

    upgrader = MultiVersionUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_data_files(data_folder)

    assert (data_folder / "v1.1.txt").exists()
    assert (data_folder / "v1.2.txt").exists()
    assert (data_folder / "v2.0.txt").exists()


def test_multi_version_system_upgrade_chain(system_data, semantic_strategy):
    class MultiVersionSystemUpgrader(PluginUpgrader): ...

    @MultiVersionSystemUpgrader.register_upgrade_step(
        target_version="1.5.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=1,
    )
    def upgrade_to_1_5_0(
        data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data["metadata"]["upgraded_to"] = "1.5.0"
        return data

    @MultiVersionSystemUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=2,
    )
    def upgrade_to_2_0_0(
        data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data["version"] = "2.0.0"
        data["components"].append("comp3")
        return data

    upgrader = MultiVersionSystemUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_system_data(system_data)

    assert system_data["metadata"]["upgraded_to"] == "1.5.0"
    assert system_data["version"] == "2.0.0"
    assert "comp3" in system_data["components"]


def test_skip_already_upgraded_versions(data_folder, semantic_strategy):
    class SkipUpgrader(PluginUpgrader): ...

    @SkipUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_to_2_0_0(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "should_not_exist.txt").write_text("should not run")
        return folder

    @SkipUpgrader.register_upgrade_step(
        target_version="1.5.0",
        upgrade_type=UpgradeType.FILE,
        priority=2,
    )
    def upgrade_to_1_5_0(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "should_not_exist_either.txt").write_text("should not run")
        return folder

    @SkipUpgrader.register_upgrade_step(
        target_version="3.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=3,
    )
    def upgrade_to_3_0_0(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "should_exist.txt").write_text("should run")
        return folder

    upgrader = SkipUpgrader(strategy=semantic_strategy, version="2.5.0")
    upgrader.upgrade_data_files(data_folder)

    assert not (data_folder / "should_not_exist.txt").exists()
    assert not (data_folder / "should_not_exist_either.txt").exists()
    assert (data_folder / "should_exist.txt").exists()


def test_mixed_file_and_system_upgrades(data_folder, system_data, semantic_strategy):
    class MixedUpgrader(PluginUpgrader): ...

    @MixedUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_files(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "file_upgrade.txt").write_text("file upgraded")
        return folder

    @MixedUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=1,
    )
    def upgrade_system(
        data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data["system_upgraded"] = True
        return data

    upgrader = MixedUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_data_files(data_folder)
    upgrader.upgrade_system_data(system_data)

    assert (data_folder / "file_upgrade.txt").exists()
    assert system_data["system_upgraded"] is True


def test_version_detector_integration(data_folder, semantic_strategy, version_detector):
    class DetectorUpgrader(PluginUpgrader): ...

    @DetectorUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_detected_version(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "auto_detected.txt").write_text("version auto-detected")
        return folder

    (data_folder / "VERSION").write_text("1.5.0")

    upgrader = DetectorUpgrader(
        strategy=semantic_strategy, version_detector=version_detector, folder_path=data_folder
    )

    assert upgrader.version == "1.5.0"

    upgrader.upgrade_data_files(data_folder)
    assert (data_folder / "auto_detected.txt").exists()


def test_context_propagation_through_multiple_steps(data_folder, semantic_strategy):
    class ContextUpgrader(PluginUpgrader): ...

    execution_log = []

    @ContextUpgrader.register_upgrade_step(
        target_version="1.5.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def first_step(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        prefix = upgrader_context.get("prefix", "") if upgrader_context else ""
        execution_log.append(f"{prefix}step1")
        (folder / "step1.txt").write_text(f"{prefix}step1")
        return folder

    @ContextUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=2,
    )
    def second_step(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        prefix = upgrader_context.get("prefix", "") if upgrader_context else ""
        execution_log.append(f"{prefix}step2")
        (folder / "step2.txt").write_text(f"{prefix}step2")
        return folder

    context = {"prefix": "test_"}
    upgrader = ContextUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_data_files(data_folder, upgrader_context=context)

    assert execution_log == ["test_step1", "test_step2"]
    assert (data_folder / "step1.txt").read_text() == "test_step1"
    assert (data_folder / "step2.txt").read_text() == "test_step2"


def test_git_versioning_upgrade_chain(data_folder, git_strategy):
    class GitUpgrader(PluginUpgrader): ...

    @GitUpgrader.register_upgrade_step(
        target_version="def456",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_to_def456(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "def456.txt").write_text("upgraded to def456")
        return folder

    @GitUpgrader.register_upgrade_step(
        target_version="ghi789",
        upgrade_type=UpgradeType.FILE,
        priority=2,
    )
    def upgrade_to_ghi789(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "ghi789.txt").write_text("upgraded to ghi789")
        return folder

    @GitUpgrader.register_upgrade_step(
        target_version="jkl012",
        upgrade_type=UpgradeType.FILE,
        priority=3,
    )
    def upgrade_to_jkl012(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "jkl012.txt").write_text("upgraded to jkl012")
        return folder

    upgrader = GitUpgrader(strategy=git_strategy, version="abc123")
    upgrader.upgrade_data_files(data_folder)

    assert (data_folder / "def456.txt").exists()
    assert (data_folder / "ghi789.txt").exists()
    assert (data_folder / "jkl012.txt").exists()


def test_complex_file_transformation_chain(data_folder, semantic_strategy):
    class TransformationUpgrader(PluginUpgrader): ...

    @TransformationUpgrader.register_upgrade_step(
        target_version="1.1.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def rename_data_file(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        old_file = folder / "data.txt"
        new_file = folder / "data_v1.txt"
        old_file.rename(new_file)
        return new_file

    @TransformationUpgrader.register_upgrade_step(
        target_version="1.2.0",
        upgrade_type=UpgradeType.FILE,
        priority=2,
    )
    def modify_content(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        data_file = folder / "data_v1.txt"
        content = data_file.read_text()
        data_file.write_text(content.upper())
        return data_file

    @TransformationUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=3,
    )
    def add_metadata(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "metadata.txt").write_text("version=2.0.0")
        return folder

    upgrader = TransformationUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_data_files(data_folder)

    assert not (data_folder / "data.txt").exists()
    assert (data_folder / "data_v1.txt").exists()
    assert (data_folder / "data_v1.txt").read_text() == "ORIGINAL DATA"
    assert (data_folder / "metadata.txt").exists()


def test_complex_system_data_transformation(system_data, semantic_strategy):
    class ComplexSystemUpgrader(PluginUpgrader): ...

    @ComplexSystemUpgrader.register_upgrade_step(
        target_version="1.5.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=1,
    )
    def restructure_metadata(
        data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data["metadata"]["modified"] = "2024-01-15"
        data["metadata"]["upgraded"] = True
        return data

    @ComplexSystemUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=2,
    )
    def add_new_section(
        data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data["configuration"] = {"enabled": True, "features": ["feature1", "feature2"]}
        return data

    @ComplexSystemUpgrader.register_upgrade_step(
        target_version="2.1.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=3,
    )
    def migrate_components(
        data: dict[str, Any], upgrader_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data["components"] = [{"name": c, "type": "legacy"} for c in data["components"]]
        return data

    upgrader = ComplexSystemUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_system_data(system_data)

    assert system_data["metadata"]["upgraded"] is True
    assert "configuration" in system_data
    assert system_data["configuration"]["enabled"] is True
    assert isinstance(system_data["components"][0], dict)
    assert system_data["components"][0]["type"] == "legacy"


def test_no_upgrades_when_version_none(data_folder, semantic_strategy):
    class NoVersionUpgrader(PluginUpgrader): ...

    @NoVersionUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def should_not_run(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "should_not_exist.txt").write_text("error")
        return folder

    upgrader = NoVersionUpgrader(strategy=semantic_strategy, version=None)
    upgrader.upgrade_data_files(data_folder)

    assert not (data_folder / "should_not_exist.txt").exists()


def test_no_upgrades_when_strategy_none(data_folder):
    class NoStrategyUpgrader(PluginUpgrader): ...

    @NoStrategyUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def should_not_run(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "should_not_exist.txt").write_text("error")
        return folder

    upgrader = NoStrategyUpgrader(strategy=None, version="1.0.0")
    upgrader.upgrade_data_files(data_folder)

    assert not (data_folder / "should_not_exist.txt").exists()


def test_upgrade_error_propagation(data_folder, semantic_strategy):
    class ErrorUpgrader(PluginUpgrader): ...

    @ErrorUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def failing_upgrade(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        raise ValueError("Intentional failure")

    upgrader = ErrorUpgrader(strategy=semantic_strategy, version="1.0.0")

    with pytest.raises(UpgradeError):
        upgrader.upgrade_data_files(data_folder)


def test_partial_upgrade_from_intermediate_version(data_folder, semantic_strategy):
    class PartialUpgrader(PluginUpgrader): ...

    @PartialUpgrader.register_upgrade_step(
        target_version="1.5.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_to_1_5(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v1.5.txt").write_text("1.5")
        return folder

    @PartialUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=2,
    )
    def upgrade_to_2_0(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v2.0.txt").write_text("2.0")
        return folder

    @PartialUpgrader.register_upgrade_step(
        target_version="2.5.0",
        upgrade_type=UpgradeType.FILE,
        priority=3,
    )
    def upgrade_to_2_5(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v2.5.txt").write_text("2.5")
        return folder

    upgrader = PartialUpgrader(strategy=semantic_strategy, version="1.8.0")
    upgrader.upgrade_data_files(data_folder)

    assert not (data_folder / "v1.5.txt").exists()
    assert (data_folder / "v2.0.txt").exists()
    assert (data_folder / "v2.5.txt").exists()


def test_double_digit_version_upgrades(data_folder, semantic_strategy):
    class DoubleDigitUpgrader(PluginUpgrader): ...

    @DoubleDigitUpgrader.register_upgrade_step(
        target_version="1.9.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_to_1_9(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v1.9.txt").write_text("1.9")
        return folder

    @DoubleDigitUpgrader.register_upgrade_step(
        target_version="1.10.0",
        upgrade_type=UpgradeType.FILE,
        priority=2,
    )
    def upgrade_to_1_10(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v1.10.txt").write_text("1.10")
        return folder

    @DoubleDigitUpgrader.register_upgrade_step(
        target_version="1.11.0",
        upgrade_type=UpgradeType.FILE,
        priority=3,
    )
    def upgrade_to_1_11(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "v1.11.txt").write_text("1.11")
        return folder

    upgrader = DoubleDigitUpgrader(strategy=semantic_strategy, version="1.8.0")
    upgrader.upgrade_data_files(data_folder)

    assert (data_folder / "v1.9.txt").exists()
    assert (data_folder / "v1.10.txt").exists()
    assert (data_folder / "v1.11.txt").exists()


def test_empty_steps_list_handles_gracefully(data_folder, semantic_strategy):
    class EmptyUpgrader(PluginUpgrader): ...

    upgrader = EmptyUpgrader(strategy=semantic_strategy, version="1.0.0")
    result = upgrader.upgrade_data_files(data_folder)

    assert result


def test_multiple_upgraders_independent_registries(data_folder, semantic_strategy):
    class FirstUpgrader(PluginUpgrader): ...

    class SecondUpgrader(PluginUpgrader): ...

    @FirstUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def first_upgrade(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "first.txt").write_text("first")
        return folder

    @SecondUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def second_upgrade(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "second.txt").write_text("second")
        return folder

    first = FirstUpgrader(strategy=semantic_strategy, version="1.0.0")
    second = SecondUpgrader(strategy=semantic_strategy, version="1.0.0")

    first.upgrade_data_files(data_folder)
    assert (data_folder / "first.txt").exists()
    assert not (data_folder / "second.txt").exists()

    second.upgrade_data_files(data_folder)
    assert (data_folder / "second.txt").exists()


def test_context_with_nested_data_structures(data_folder, semantic_strategy):
    class NestedContextUpgrader(PluginUpgrader): ...

    @NestedContextUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def use_nested_context(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        if upgrader_context:
            config = upgrader_context.get("config", {})
            setting = config.get("nested", {}).get("value", "default")
            (folder / "config.txt").write_text(setting)
        return folder

    context = {"config": {"nested": {"value": "complex_setting"}}}
    upgrader = NestedContextUpgrader(strategy=semantic_strategy, version="1.0.0")
    upgrader.upgrade_data_files(data_folder, upgrader_context=context)

    assert (data_folder / "config.txt").exists()
    assert (data_folder / "config.txt").read_text() == "complex_setting"
