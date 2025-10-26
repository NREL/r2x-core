"""Tests for DataStore class."""

import json
from pathlib import Path
from typing import Any

import pytest

from r2x_core import DataFile, DataReader, DataStore, PluginUpgrader, UpgradeType
from r2x_core.exceptions import UpgradeError
from r2x_core.versioning import SemanticVersioningStrategy


@pytest.fixture
def test_folder(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "file1.csv").write_text("col1,col2\n1,2\n3,4")
    (folder / "file2.csv").write_text("a,b\nx,y\nz,w")
    return folder


@pytest.fixture
def data_file_1(test_folder):
    return DataFile(name="test1", fpath=test_folder / "file1.csv")


@pytest.fixture
def data_file_2(test_folder):
    return DataFile(name="test2", fpath=test_folder / "file2.csv")


@pytest.fixture
def data_files(data_file_1, data_file_2):
    return [data_file_1, data_file_2]


def test_datastore_instance():
    store = DataStore()
    assert isinstance(store, DataStore)


def test_datastore_with_folder(test_folder):
    store = DataStore(test_folder)
    assert store.folder == test_folder.resolve()


def test_datastore_with_string_folder(test_folder):
    store = DataStore(str(test_folder))
    assert store.folder == test_folder.resolve()


def test_datastore_with_nonexistent_folder():
    with pytest.raises(FileNotFoundError):
        DataStore("/nonexistent/path")


def test_datastore_folder_property(test_folder):
    store = DataStore(test_folder)
    assert isinstance(store.folder, Path)
    assert store.folder.exists()


def test_datastore_reader_property():
    store = DataStore()
    assert isinstance(store.reader, DataReader)


def test_datastore_upgrader_property():
    store = DataStore()
    assert store.upgrader is None


def test_add_data_single_file(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    assert "test1" in store


def test_add_data_multiple_files(test_folder, data_files):
    store = DataStore(test_folder)
    store.add_data(*data_files)
    assert "test1" in store
    assert "test2" in store


def test_add_data_overwrite_false(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    with pytest.raises(KeyError):
        store.add_data(data_file_1, overwrite=False)


def test_add_data_overwrite_true(test_folder, data_file_1, data_file_2):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    new_file = DataFile(name="test1", fpath=test_folder / "file2.csv")
    store.add_data(new_file, overwrite=True)
    assert store["test1"].fpath == test_folder / "file2.csv"


def test_add_data_invalid_type(test_folder):
    store = DataStore(test_folder)
    with pytest.raises(TypeError):
        store.add_data("not a datafile")


def test_contains(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    assert "test1" in store
    assert "nonexistent" not in store


def test_getitem(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    retrieved = store["test1"]
    assert retrieved.name == "test1"


def test_getitem_missing(test_folder):
    store = DataStore(test_folder)
    with pytest.raises(KeyError):
        store["nonexistent"]


def test_list_data_empty(test_folder):
    store = DataStore(test_folder)
    assert store.list_data() == []


def test_list_data_sorted(test_folder, data_files):
    store = DataStore(test_folder)
    store.add_data(*data_files)
    assert store.list_data() == ["test1", "test2"]


def test_remove_data_single(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    store.remove_data("test1")
    assert "test1" not in store


def test_remove_data_multiple(test_folder, data_files):
    store = DataStore(test_folder)
    store.add_data(*data_files)
    store.remove_data("test1", "test2")
    assert "test1" not in store
    assert "test2" not in store


def test_remove_data_missing(test_folder):
    store = DataStore(test_folder)
    with pytest.raises(KeyError):
        store.remove_data("nonexistent")


def test_clear_cache(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    store.clear_cache()
    assert store.list_data() == []


def test_read_data(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    data = store.read_data("test1")
    assert data is not None


def test_read_data_missing(test_folder):
    store = DataStore(test_folder)
    with pytest.raises(KeyError):
        store.read_data("nonexistent")


def test_read_data_use_cache_true(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    data1 = store.read_data("test1", use_cache=True)
    data2 = store.read_data("test1", use_cache=True)
    assert data1 is not None
    assert data2 is not None


def test_read_data_use_cache_false(test_folder, data_file_1):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    data = store.read_data("test1", use_cache=False)
    assert data is not None


def test_to_json(test_folder, data_files, tmp_path):
    store = DataStore(test_folder)
    store.add_data(*data_files)
    json_path = tmp_path / "config.json"
    store.to_json(json_path)
    assert json_path.exists()


def test_to_json_content(test_folder, data_file_1, tmp_path):
    store = DataStore(test_folder)
    store.add_data(data_file_1)
    json_path = tmp_path / "config.json"
    store.to_json(json_path)
    with open(json_path) as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "test1"


def test_from_data_files(test_folder, data_files):
    store = DataStore.from_data_files(data_files, test_folder)
    assert "test1" in store
    assert "test2" in store


def test_from_data_files_no_folder(data_files):
    store = DataStore.from_data_files(data_files)
    assert "test1" in store
    assert "test2" in store


def test_from_json(test_folder, data_files, tmp_path):
    json_path = tmp_path / "config.json"
    json_data = [
        {"name": "test1", "fpath": str(test_folder / "file1.csv")},
        {"name": "test2", "fpath": str(test_folder / "file2.csv")},
    ]
    with open(json_path, "w") as f:
        json.dump(json_data, f)
    new_store = DataStore.from_json(json_path, test_folder)
    assert "test1" in new_store
    assert "test2" in new_store


def test_from_json_missing_folder(tmp_path):
    json_path = tmp_path / "config.json"
    json_path.write_text("[]")
    with pytest.raises(FileNotFoundError):
        DataStore.from_json(json_path, "/nonexistent/path")


def test_from_json_missing_file(test_folder):
    with pytest.raises(FileNotFoundError):
        DataStore.from_json("/nonexistent/config.json", test_folder)


def test_from_json_not_array(test_folder, tmp_path):
    json_path = tmp_path / "config.json"
    json_path.write_text('{"not": "array"}')
    with pytest.raises(TypeError):
        DataStore.from_json(json_path, test_folder)


def test_upgrade_data_no_upgrader(test_folder):
    store = DataStore(test_folder)
    with pytest.raises(UpgradeError):
        store.upgrade_data()


def test_from_json_validation_error(tmp_path):
    from pydantic import ValidationError

    (tmp_path / "test.csv").write_text("test")
    json_file = tmp_path / "invalid.json"
    json_file.write_text('[{"name": 123, "fpath": "test.csv"}]')
    with pytest.raises(ValidationError):
        DataStore.from_json(json_fpath=json_file, folder_path=tmp_path)


def test_upgrade_data_no_steps(test_folder):
    class EmptyUpgrader(PluginUpgrader): ...

    (test_folder / "VERSION").write_text("1.0.0")
    strategy = SemanticVersioningStrategy()
    upgrader = EmptyUpgrader(strategy=strategy, version="1.0.0")
    store = DataStore(test_folder, upgrader=upgrader)
    result = store.upgrade_data()
    assert result is None


def test_upgrade_data_backup_failure(test_folder, monkeypatch):
    from r2x_core.result import Err

    class TestUpgrader(PluginUpgrader): ...

    @TestUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_files(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        return folder

    def mock_backup_folder(folder_path):
        return Err("Backup failed")

    monkeypatch.setattr("r2x_core.store.backup_folder", mock_backup_folder)

    (test_folder / "VERSION").write_text("1.0.0")
    strategy = SemanticVersioningStrategy()
    upgrader = TestUpgrader(strategy=strategy, version="1.0.0")
    store = DataStore(test_folder, upgrader=upgrader)

    with pytest.raises(UpgradeError):
        store.upgrade_data(backup=True)


def test_upgrade_data_execution_failure(test_folder, monkeypatch):
    from r2x_core.result import Err

    class TestUpgrader(PluginUpgrader): ...

    @TestUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_files(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        return folder

    def mock_run_datafile_upgrades(*args, **kwargs):
        return Err("Upgrade execution failed")

    monkeypatch.setattr("r2x_core.store.run_datafile_upgrades", mock_run_datafile_upgrades)

    (test_folder / "VERSION").write_text("1.0.0")
    strategy = SemanticVersioningStrategy()
    upgrader = TestUpgrader(strategy=strategy, version="1.0.0")
    store = DataStore(test_folder, upgrader=upgrader)

    with pytest.raises(UpgradeError):
        store.upgrade_data(backup=False)


def test_upgrade_data_with_upgrader(test_folder):
    class TestUpgrader(PluginUpgrader): ...

    @TestUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_files(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "upgraded.txt").write_text("upgraded")
        return folder

    (test_folder / "VERSION").write_text("1.0.0")
    strategy = SemanticVersioningStrategy()
    upgrader = TestUpgrader(strategy=strategy, version="1.0.0")
    store = DataStore(test_folder, upgrader=upgrader)
    store.upgrade_data()
    assert (test_folder / "upgraded.txt").exists()


def test_upgrade_data_with_backup(test_folder):
    class TestUpgrader(PluginUpgrader): ...

    @TestUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_files(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        (folder / "upgraded.txt").write_text("upgraded")
        return folder

    (test_folder / "VERSION").write_text("1.0.0")
    strategy = SemanticVersioningStrategy()
    upgrader = TestUpgrader(strategy=strategy, version="1.0.0")
    store = DataStore(test_folder, upgrader=upgrader)
    store.upgrade_data(backup=True)
    assert (test_folder / "upgraded.txt").exists()


def test_upgrade_data_with_context(test_folder):
    class TestUpgrader(PluginUpgrader): ...

    @TestUpgrader.register_upgrade_step(
        target_version="2.0.0",
        upgrade_type=UpgradeType.FILE,
        priority=1,
    )
    def upgrade_files(folder: Path, upgrader_context: dict[str, Any] | None = None) -> Path:
        value = upgrader_context.get("key", "default") if upgrader_context else "default"
        (folder / "context.txt").write_text(value)
        return folder

    (test_folder / "VERSION").write_text("1.0.0")
    strategy = SemanticVersioningStrategy()
    upgrader = TestUpgrader(strategy=strategy, version="1.0.0")
    store = DataStore(test_folder, upgrader=upgrader)
    store.upgrade_data(upgrader_context={"key": "custom_value"})
    assert (test_folder / "context.txt").read_text() == "custom_value"


def test_read_data_with_placeholders(test_folder):
    store = DataStore(test_folder)
    data_file = DataFile(name="test1", fpath=test_folder / "file1.csv")
    store.add_data(data_file)
    data = store.read_data("test1", placeholders={"year": 2030})
    assert data is not None


def test_datastore_with_custom_reader(test_folder):
    reader = DataReader()
    store = DataStore(test_folder, reader=reader)
    assert store.reader is reader


def test_datastore_with_upgrader(test_folder):
    class TestUpgrader(PluginUpgrader): ...

    strategy = SemanticVersioningStrategy()
    upgrader = TestUpgrader(strategy=strategy)
    store = DataStore(test_folder, upgrader=upgrader)
    assert store.upgrader is upgrader
