"""Integration tests for upgrader functionality with DataStore and System."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from r2x_core import DataStore, System, UpgradeType
from r2x_core.upgrader import DataUpgrader
from r2x_core.versioning import SemanticVersioningStrategy

if TYPE_CHECKING:
    pass


class IntegrationTestUpgrader(DataUpgrader):
    """Test upgrader for integration tests."""

    strategy: SemanticVersioningStrategy = SemanticVersioningStrategy()

    @staticmethod
    def detect_version(folder: Path) -> str | None:
        """Detect version from VERSION file."""
        version_file = folder / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return None


@IntegrationTestUpgrader.upgrade_step(
    target_version="2.0.0",
    upgrade_type=UpgradeType.FILE,
    priority=100,
)
def upgrade_config_to_v2(folder: Path) -> Path:
    """Upgrade configuration file to v2."""

    marker_file = folder / "upgraded_marker.txt"
    marker_file.write_text("upgraded to v2.0.0")
    return folder


def test_datastore_from_json_with_upgrader(tmp_path):
    """Test DataStore.from_json with upgrader applies FILE upgrades."""

    data_folder = tmp_path / "data"
    data_folder.mkdir()

    version_file = data_folder / "VERSION"
    version_file.write_text("1.0.0")

    config_file = data_folder / "config.json"
    config_data = [{"name": "test_file", "fpath": "test.csv"}]
    config_file.write_text(json.dumps(config_data, indent=2))

    test_csv = data_folder / "test.csv"
    test_csv.write_text("col1,col2\n1,2\n")

    _ = DataStore.from_json(str(config_file), folder=str(data_folder), upgrader=IntegrationTestUpgrader)

    marker_file = data_folder / "upgraded_marker.txt"
    assert marker_file.exists()
    assert marker_file.read_text() == "upgraded to v2.0.0"

    backup_folder = tmp_path / "data_backup"
    assert backup_folder.exists()


def test_datastore_from_json_without_upgrader(tmp_path):
    """Test DataStore.from_json without upgrader works normally."""
    data_folder = tmp_path / "data"
    data_folder.mkdir()

    config_file = data_folder / "config.json"
    config_data = [{"name": "test_file", "fpath": "test.csv"}]
    config_file.write_text(json.dumps(config_data, indent=2))

    test_csv = data_folder / "test.csv"
    test_csv.write_text("col1,col2\n1,2\n")

    store = DataStore.from_json(str(config_file), folder=str(data_folder), upgrader=None)

    assert store is not None
    assert "test_file" in store.list_data_files()


def test_datastore_from_json_no_file_upgrades(tmp_path):
    """Test DataStore.from_json when upgrader has no FILE steps."""

    class SystemOnlyUpgrader(DataUpgrader):
        strategy = SemanticVersioningStrategy()

        @staticmethod
        def detect_version(folder: Path) -> str | None:
            return "1.0.0"

    @SystemOnlyUpgrader.upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.SYSTEM,
        priority=100,
    )
    def system_only_upgrade(system: System) -> System:
        system.metadata["version"] = "2.0.0"
        return system

    data_folder = tmp_path / "data"
    data_folder.mkdir()

    config_file = data_folder / "config.json"
    config_data = [{"name": "test_file", "fpath": "test.csv"}]
    config_file.write_text(json.dumps(config_data, indent=2))

    test_csv = data_folder / "test.csv"
    test_csv.write_text("col1,col2\n1,2\n")

    store = DataStore.from_json(str(config_file), folder=str(data_folder), upgrader=SystemOnlyUpgrader)

    assert store is not None


def test_datastore_upgrader_with_existing_backup(tmp_path):
    """Test DataStore.from_json when backup folder already exists."""

    data_folder = tmp_path / "data"
    data_folder.mkdir()

    backup_folder = tmp_path / "data_backup"
    backup_folder.mkdir()
    (backup_folder / "old_backup.txt").write_text("old")

    version_file = data_folder / "VERSION"
    version_file.write_text("1.0.0")

    config_file = data_folder / "config.json"
    config_data = [{"name": "test_file", "fpath": "test.csv"}]
    config_file.write_text(json.dumps(config_data, indent=2))

    test_csv = data_folder / "test.csv"
    test_csv.write_text("col1,col2\n1,2\n")

    _ = DataStore.from_json(str(config_file), folder=str(data_folder), upgrader=IntegrationTestUpgrader)

    assert not (backup_folder / "old_backup.txt").exists()

    assert backup_folder.exists()


def test_datastore_upgrader_folder_not_found(tmp_path):
    """Test DataStore.from_json raises error when folder doesn't exist."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"files": []}')

    nonexistent_folder = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError, match="Data folder not found"):
        DataStore.from_json(
            str(config_file), folder=str(nonexistent_folder), upgrader=IntegrationTestUpgrader
        )


def test_datastore_config_file_not_found(tmp_path):
    """Test DataStore.from_json raises error when config file doesn't exist."""
    data_folder = tmp_path / "data"
    data_folder.mkdir()

    nonexistent_config = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        DataStore.from_json(str(nonexistent_config), folder=str(data_folder), upgrader=None)
