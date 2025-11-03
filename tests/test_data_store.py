"""Tests for DataStore class."""

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from r2x_core import DataStore


@pytest.fixture
def folder_with_data(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / "file1.csv").write_text("col1,col2\n1,2\n3,4")
    (folder / "file2.csv").write_text("a,b\nx,y\nz,w")
    return folder


@pytest.fixture
def data_store_example(folder_with_data) -> "DataStore":
    from r2x_core import DataFile, DataStore

    df_01 = DataFile(name="test1", fpath=folder_with_data / "file1.csv")
    df_02 = DataFile(name="test2", fpath=folder_with_data / "file2.csv")

    store = DataStore(folder_with_data)
    store.add_data(df_01, df_02)
    return store


def test_datastore_folder_operations(data_store_example, folder_with_data):
    store = data_store_example
    assert store.folder == folder_with_data.resolve()
    assert store.folder.exists()


def test_instance_fails_with_nonexistent_folder():
    from r2x_core import DataStore

    with pytest.raises(FileNotFoundError):
        DataStore("/nonexistent/path")


def test_add_data_overwrite_datafile(data_store_example, folder_with_data):
    from r2x_core import DataFile

    store = data_store_example

    new_file = DataFile(name="test1", fpath=folder_with_data / "file2.csv")
    store.add_data(new_file, overwrite=True)
    assert store["test1"].fpath == folder_with_data / "file2.csv"

    with pytest.raises(KeyError):
        store.add_data(new_file)


def test_store_accessing_data(data_store_example):
    store = data_store_example
    assert "test1" in store
    retrieved = store["test1"]
    assert retrieved.name == "test1"

    assert "nonexistent" not in store
    with pytest.raises(KeyError):
        store["nonexistent"]


def test_list_data_sorted(data_store_example):
    store = data_store_example
    assert store.list_data() == ["test1", "test2"]


def test_remove_data_files(data_store_example, folder_with_data):
    from r2x_core import DataFile

    store = data_store_example
    file_to_remove = DataFile(name="file_to_remove", fpath=folder_with_data / "file2.csv")
    store.add_data(file_to_remove)

    assert "file_to_remove" in store
    store.remove_data("file_to_remove")
    assert "file_to_remove" not in store

    with pytest.raises(KeyError):
        store.remove_data("nonexistent")


def test_clear_cache(folder_with_data):
    from r2x_core import DataFile, DataStore

    store = DataStore(folder_with_data)
    df_01 = DataFile(name="test_1", fpath=folder_with_data / "file1.csv")
    store.add_data(df_01)
    assert store.list_data() == ["test_1"]


def test_reader_operations(data_store_example):
    from r2x_core import DataReader

    store = data_store_example
    assert isinstance(store.reader, DataReader)


def test_read_data(data_store_example):
    store = data_store_example
    data = store.read_data("test1")
    assert data is not None
    with pytest.raises(KeyError):
        store.read_data("nonexistent")


def test_read_data_cache(data_store_example, folder_with_data):
    """Test that reading files always returns fresh data.

    Since most file formats return lazy frames (e.g., polars.LazyFrame),
    actual I/O happens at collection time. There is no caching, so each
    read always gets the current file content.
    """
    store = data_store_example

    # First read
    data1 = store.read_data("test1").collect()
    assert data1 is not None
    assert len(data1) == 2

    # Modify the file
    (folder_with_data / "file1.csv").write_text("col1,col2\n10,20")

    # Read again - should get modified content (no caching)
    data2 = store.read_data("test1").collect()
    assert len(data2) == 1, "Should read modified file content"


def test_to_json_serialization(data_store_example, tmp_path, folder_with_data):
    from r2x_core import DataStore

    store = data_store_example
    json_path = tmp_path / "config.json"
    store.to_json(json_path)
    assert json_path.exists()

    with open(json_path) as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] == "test1"

    new_store = DataStore.from_json(json_path, folder_with_data)
    assert "test1" in new_store
    assert "test2" in new_store


def test_from_data_files_constructor(data_store_example, folder_with_data):
    from r2x_core import DataFile, DataStore

    df_01 = DataFile(name="test1", fpath=folder_with_data / "file1.csv")
    df_02 = DataFile(name="test2", fpath=folder_with_data / "file2.csv")
    store = DataStore.from_data_files(data_files=[df_01, df_02])
    assert "test1" in store
    assert "test2" in store

    data = store.read_data("test1")
    assert data is not None


def test_from_data_files_constructor_with_relative_paths(data_store_example, folder_with_data, caplog):
    from pathlib import Path

    import polars as pl

    from r2x_core import DataFile, DataStore

    (Path.cwd() / "local_file.csv").write_text("col1,col2\n1,2\n3,4")
    df_01 = DataFile(name="test1", relative_fpath="file1.csv")
    df_02 = DataFile(name="test2", relative_fpath="file2.csv")
    df_03 = DataFile(name="test3", fpath="local_file.csv")
    store = DataStore.from_data_files(data_files=[df_01, df_02, df_03], folder_path=folder_with_data)
    assert "test1" in store
    assert "test2" in store
    assert "test3" in store

    for data in [df_01, df_02, df_03]:
        d = store.read_data(data.name)
        assert d is not None
        assert isinstance(d, pl.LazyFrame)
        assert not d.collect().is_empty()


def test_load_data_file(tmp_path):
    from r2x_core import DataStore

    (tmp_path / "file1.csv").write_text("col1,col2\n1,2\n3,4")

    result = DataStore.load_file(tmp_path / "file1.csv").collect()
    assert result.shape == (2, 2)

    with pytest.raises(FileNotFoundError):
        DataStore.load_file(tmp_path / "nota file")
