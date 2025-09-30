import json
from pathlib import Path

import pytest

from r2x_core import DataFile, DataStore


def test_data_container_instance() -> None:
    data = DataStore()
    assert isinstance(data, DataStore)


@pytest.fixture(scope="function")
def data_container_empty(tmp_path) -> DataStore:
    return DataStore(folder=tmp_path)


@pytest.fixture(scope="function")
def data_container_with_files(tmp_path) -> DataStore:
    store = DataStore(folder=tmp_path)

    # Create test files
    file1 = tmp_path / "file1.csv"
    file1.write_text("col1,col2\n1,2\n")
    file2 = tmp_path / "file2.csv"
    file2.write_text("col3,col4\n3,4\n")
    file3 = tmp_path / "file3.csv"
    file3.write_text("col5,col6\n5,6\n")

    store.add_data_file(DataFile(name="generators", fpath=file1))
    store.add_data_file(DataFile(name="load", fpath=file2))
    store.add_data_file(DataFile(name="transmission", fpath=file3))

    yield store


def test_data_container_add_data_file(
    data_container_empty: DataStore, empty_file: Path
) -> None:
    store: DataStore = data_container_empty

    example_file: DataFile = DataFile(name="generators", fpath=empty_file)
    store.add_data_file(example_file)
    assert store.get_data_file_by_name(name="generators") == example_file


def test_data_container_add_data_file_overwrite_false_raises_error(
    data_container_empty: DataStore, empty_file: Path
) -> None:
    store: DataStore = data_container_empty

    example_file: DataFile = DataFile(name="generators", fpath=empty_file)
    store.add_data_file(example_file)

    with pytest.raises(KeyError, match="already exists"):
        store.add_data_file(example_file, overwrite=False)


def test_data_container_add_data_file_overwrite_true_succeeds(
    data_container_empty: DataStore, empty_file: Path, tmp_path: Path
) -> None:
    store: DataStore = data_container_empty

    # Create two different files
    file2 = tmp_path / "file2.csv"
    file2.write_text("different content")

    example_file1: DataFile = DataFile(name="generators", fpath=empty_file)
    example_file2: DataFile = DataFile(name="generators", fpath=file2)

    store.add_data_file(example_file1)
    store.add_data_file(example_file2, overwrite=True)

    assert store.get_data_file_by_name(name="generators") == example_file2


def test_data_container_add_data_files_multiple(
    data_container_empty: DataStore, tmp_path: Path
) -> None:
    store: DataStore = data_container_empty

    # Create test files
    file1 = tmp_path / "file1.csv"
    file1.write_text("")
    file2 = tmp_path / "file2.csv"
    file2.write_text("")

    files = [
        DataFile(name="generators", fpath=file1),
        DataFile(name="load", fpath=file2),
    ]

    store.add_data_files(files)

    assert len(store.list_data_files()) == 2


def test_data_container_add_data_files_duplicate_raises_error(
    data_container_empty: DataStore, tmp_path: Path
) -> None:
    store: DataStore = data_container_empty

    file1 = tmp_path / "file1.csv"
    file1.write_text("")

    # Add first file
    store.add_data_file(DataFile(name="generators", fpath=file1))

    # Try to add duplicate
    files = [DataFile(name="generators", fpath=file1)]

    with pytest.raises(KeyError):
        store.add_data_files(files, overwrite=False)


def test_data_container_add_data_files_overwrite_true_succeeds(
    data_container_empty: DataStore, tmp_path: Path
) -> None:
    store: DataStore = data_container_empty

    file1 = tmp_path / "file1.csv"
    file1.write_text("")
    file2 = tmp_path / "file2.csv"
    file2.write_text("different")

    # Add first file
    store.add_data_file(DataFile(name="generators", fpath=file1))

    # Overwrite with different file
    files = [DataFile(name="generators", fpath=file2)]
    store.add_data_files(files, overwrite=True)

    assert store.get_data_file_by_name("generators").fpath == file2


def test_data_container_clear_cache(data_container_with_files: DataStore) -> None:
    store: DataStore = data_container_with_files

    # Verify files exist before clearing
    assert len(store.list_data_files()) == 3

    store.clear_cache()

    assert len(store.list_data_files()) == 0


def test_data_container_get_data_file_by_name_existing(
    data_container_with_files: DataStore,
) -> None:
    store: DataStore = data_container_with_files

    data_file = store.get_data_file_by_name("generators")

    assert data_file.name == "generators"


def test_data_container_get_data_file_by_name_missing_raises_error(
    data_container_empty: DataStore,
) -> None:
    store: DataStore = data_container_empty

    with pytest.raises(KeyError, match="not present in store"):
        store.get_data_file_by_name("nonexistent")


def test_data_container_list_data_files_empty(data_container_empty: DataStore) -> None:
    store: DataStore = data_container_empty

    files = store.list_data_files()

    assert files == []


def test_data_container_list_data_files_with_files(
    data_container_with_files: DataStore,
) -> None:
    store: DataStore = data_container_with_files

    files = store.list_data_files()

    assert set(files) == {"generators", "load", "transmission"}


def test_data_container_remove_data_file_existing(
    data_container_with_files: DataStore,
) -> None:
    store: DataStore = data_container_with_files

    initial_count = len(store.list_data_files())
    store.remove_data_file("generators")

    assert len(store.list_data_files()) == initial_count - 1


def test_data_container_remove_data_file_missing_raises_error(
    data_container_empty: DataStore,
) -> None:
    store: DataStore = data_container_empty

    with pytest.raises(KeyError):
        store.remove_data_file("nonexistent")


def test_data_container_remove_data_files_multiple(
    data_container_with_files: DataStore,
) -> None:
    store: DataStore = data_container_with_files

    store.remove_data_files(["generators", "load"])

    assert store.list_data_files() == ["transmission"]


def test_data_container_from_json_valid_file(tmp_path: Path) -> None:
    # Create test data files
    file1 = tmp_path / "file1.csv"
    file1.write_text("")
    file2 = tmp_path / "file2.csv"
    file2.write_text("")

    # Create JSON config
    config_data = [
        {"name": "generators", "fpath": str(file1), "description": "Generator data"},
        {"name": "load", "fpath": str(file2), "description": "Load data"},
    ]

    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f)

    store = DataStore.from_json(config_file, tmp_path)

    assert len(store.list_data_files()) == 2


def test_data_container_from_json_missing_file_raises_error(tmp_path: Path) -> None:
    nonexistent_file = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        DataStore.from_json(nonexistent_file, tmp_path)


def test_data_container_from_json_invalid_format_raises_error(tmp_path: Path) -> None:
    # Create invalid JSON (not an array)
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump({"not": "array"}, f)

    with pytest.raises(TypeError, match="is not a JSON array"):
        DataStore.from_json(config_file, tmp_path)


def test_data_container_folder_property_is_resolved_path(tmp_path: Path) -> None:
    store = DataStore(folder=tmp_path)

    assert store.folder == tmp_path.resolve()


def test_data_container_folder_default_is_cwd() -> None:
    store = DataStore()

    assert store.folder == Path.cwd().resolve()


def test_data_container_folder_nonexistent_raises_assertion_error() -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        DataStore(folder="/nonexistent/path")


def test_data_container_to_json(
    data_container_with_files: DataStore, tmp_path: Path
) -> None:
    store: DataStore = data_container_with_files

    output_file = tmp_path / "output.json"
    store.to_json(output_file)

    assert output_file.exists()

    # Verify the content is valid JSON
    with open(output_file) as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 3
