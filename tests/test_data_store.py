"""Tests for DataStore class."""

import json
from pathlib import Path

import pytest

from r2x_core import DataFile, DataReader, DataStore


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


def test_data_container_add_data_file(data_container_empty: DataStore, empty_file: Path) -> None:
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


def test_data_container_add_data_files_multiple(data_container_empty: DataStore, tmp_path: Path) -> None:
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


def test_data_container_to_json(data_container_with_files: DataStore, tmp_path: Path) -> None:
    store: DataStore = data_container_with_files

    output_file = tmp_path / "output.json"
    store.to_json(output_file)

    assert output_file.exists()

    # Verify the content is valid JSON
    with open(output_file) as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 3


def test_from_json_missing_files_in_folder(tmp_path: Path) -> None:
    """Test from_json when files don't exist in the specified folder."""
    # Create JSON config with files that don't exist
    json_file = tmp_path / "config.json"
    config = [
        {"name": "missing1", "fpath": "missing1.csv"},
        {"name": "missing2", "fpath": "missing2.csv"},
    ]
    json_file.write_text(json.dumps(config))

    with pytest.raises(FileNotFoundError, match="were not found"):
        DataStore.from_json(json_file, folder=tmp_path)


def test_from_json_partial_missing_files(tmp_path: Path) -> None:
    """Test from_json when some files are missing."""
    # Create one file but not the other
    existing_file = tmp_path / "exists.csv"
    existing_file.write_text("col1,col2\n1,2\n")

    json_file = tmp_path / "config.json"
    config = [
        {"name": "exists", "fpath": "exists.csv"},
        {"name": "missing", "fpath": "missing.csv"},
    ]
    json_file.write_text(json.dumps(config))

    with pytest.raises(FileNotFoundError, match=r"missing.*were not found"):
        DataStore.from_json(json_file, folder=tmp_path)


def test_read_data_file_missing_name(tmp_path: Path) -> None:
    """Test reading a file that doesn't exist in the store."""
    store = DataStore(folder=tmp_path)

    with pytest.raises(KeyError, match="not present in store"):
        store.read_data_file(name="nonexistent")


def test_reader_property_setter_invalid_type(tmp_path: Path) -> None:
    """Test setting reader property with invalid type."""
    store = DataStore(folder=tmp_path)

    with pytest.raises(TypeError, match="must be a valid DataReader"):
        store.reader = "not a reader"  # type: ignore[assignment]


def test_reader_property_setter_valid(tmp_path: Path) -> None:
    """Test setting reader property with valid DataReader."""
    store = DataStore(folder=tmp_path)
    new_reader = DataReader(max_cache_size=50)

    store.reader = new_reader

    assert store.reader is new_reader
    assert store.reader.max_cache_size == 50


def test_from_plugin_config(tmp_path: Path) -> None:
    """Test creating DataStore from PluginConfig."""
    from r2x_core import PluginConfig

    # Create config directory and file_mapping.json
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_file = config_dir / "file_mapping.json"

    # Create actual data files
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    gen_file = data_dir / "generators.csv"
    gen_file.write_text("name,capacity\ngen1,100\n")
    bus_file = data_dir / "buses.csv"
    bus_file.write_text("name,voltage\nbus1,230\n")

    # Create file mapping
    mapping = [
        {"name": "generators", "fpath": str(gen_file)},
        {"name": "buses", "fpath": str(bus_file)},
    ]
    mapping_file.write_text(json.dumps(mapping))

    # Create a config class
    class TestConfig(PluginConfig):
        model_year: int

    # Mock inspect.getfile to point to our tmp directory
    import inspect

    original_getfile = inspect.getfile

    def mock_getfile(cls):
        if cls == TestConfig:
            return str(tmp_path / "config.py")
        return original_getfile(cls)

    inspect.getfile = mock_getfile
    try:
        config = TestConfig(model_year=2030)
        store = DataStore.from_plugin_config(config, folder=data_dir)

        assert isinstance(store, DataStore)
        assert len(store.list_data_files()) == 2
        assert "generators" in store
        assert "buses" in store
    finally:
        inspect.getfile = original_getfile


def test_read_data_file_success(tmp_path: Path) -> None:
    """Test successfully reading a data file from the store."""
    store = DataStore(folder=tmp_path)

    # Create test file
    test_file = tmp_path / "test_data.csv"
    test_file.write_text("col1,col2\n1,2\n3,4\n")

    # Add to store
    store.add_data_file(DataFile(name="test_data", fpath=test_file))

    # Read the file
    df = store.read_data_file(name="test_data")

    assert df is not None
    # Collect LazyFrame to check data
    collected = df.collect()
    assert len(collected) == 2
    assert list(collected.columns) == ["col1", "col2"]


def test_read_data_file_with_cache_control(tmp_path: Path) -> None:
    """Test reading a data file with cache control."""
    store = DataStore(folder=tmp_path)

    # Create test file
    test_file = tmp_path / "test_data.csv"
    test_file.write_text("col1,col2\n1,2\n")

    # Add to store
    store.add_data_file(DataFile(name="test_data", fpath=test_file))

    # Read with cache
    df1 = store.read_data_file(name="test_data", use_cache=True)
    # Read again (should use cache)
    df2 = store.read_data_file(name="test_data", use_cache=True)

    assert df1 is not None
    assert df2 is not None

    # Read without cache
    df3 = store.read_data_file(name="test_data", use_cache=False)
    assert df3 is not None
