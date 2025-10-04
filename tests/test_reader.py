import pytest

from r2x_core.datafile import DataFile
from r2x_core.reader import DataReader


@pytest.fixture
def data_reader():
    return DataReader(max_cache_size=5)


@pytest.fixture
def sample_csv(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("a,b,c\n1,2,3\n4,5,6\n")
    return csv_file


@pytest.fixture
def sample_json(tmp_path):
    json_file = tmp_path / "data.json"
    json_file.write_text('{"key": "value", "num": 42}')
    return json_file


@pytest.fixture
def optional_missing_file(tmp_path):
    return tmp_path / "nonexistent.csv"


def test_reader_init_default():
    reader = DataReader()

    assert reader.max_cache_size == 100
    assert len(reader._cache) == 0


def test_reader_init_custom_cache_size():
    reader = DataReader(max_cache_size=10)

    assert reader.max_cache_size == 10


def test_read_data_file_basic(data_reader, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv)

    result = data_reader.read_data_file(tmp_path, data_file)

    assert result is not None
    collected = result.collect()
    assert collected.shape == (2, 3)


def test_read_data_file_with_cache(data_reader, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv)

    data_reader.read_data_file(tmp_path, data_file, use_cache=True)
    data_reader.read_data_file(tmp_path, data_file, use_cache=True)

    assert len(data_reader._cache) == 1


def test_read_data_file_without_cache(data_reader, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv)

    data_reader.read_data_file(tmp_path, data_file, use_cache=False)
    data_reader.read_data_file(tmp_path, data_file, use_cache=False)

    assert len(data_reader._cache) == 0


def test_read_optional_missing_file(data_reader, tmp_path):
    # Create a CSV file and then delete it to test optional file handling
    dummy_file = tmp_path / "dummy.csv"
    dummy_file.write_text("col1,col2\n1,2\n")

    data_file = DataFile(name="test", fpath=dummy_file, is_optional=True)

    # Delete the file after DataFile creation
    dummy_file.unlink()

    result = data_reader.read_data_file(tmp_path, data_file)

    # Optional file should return None when missing
    assert result is None


def test_read_required_missing_file(data_reader, tmp_path):
    # Create a CSV file and then delete it to test required file handling
    dummy_file = tmp_path / "dummy.csv"
    dummy_file.write_text("col1,col2\n1,2\n")

    data_file = DataFile(name="test", fpath=dummy_file, is_optional=False)

    # Delete the file after DataFile creation
    dummy_file.unlink()

    with pytest.raises(FileNotFoundError, match="Missing required file"):
        data_reader.read_data_file(tmp_path, data_file)


def test_custom_reader_function(data_reader, tmp_path):
    # Use a supported extension (.csv) with a custom reader
    test_file = tmp_path / "custom.csv"
    test_file.write_text("custom content")

    def custom_reader(path):
        return path.read_text().upper()

    data_file = DataFile(name="custom", fpath=test_file, reader_function=custom_reader)
    result = data_reader.read_data_file(tmp_path, data_file)

    assert result == "CUSTOM CONTENT"


def test_cache_size_limit(tmp_path):
    reader = DataReader(max_cache_size=2)

    for i in range(3):
        csv_file = tmp_path / f"data{i}.csv"
        csv_file.write_text("a,b\n1,2\n")
        data_file = DataFile(name=f"test{i}", fpath=csv_file)
        reader.read_data_file(tmp_path, data_file, use_cache=True)

    assert len(reader._cache) == 2


def test_clear_cache(data_reader, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv)
    data_reader.read_data_file(tmp_path, data_file, use_cache=True)

    assert len(data_reader._cache) == 1
    data_reader.clear_cache()
    assert len(data_reader._cache) == 0


def test_get_cache_info(data_reader, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv)
    data_reader.read_data_file(tmp_path, data_file, use_cache=True)

    cache_info = data_reader.get_cache_info()

    assert cache_info["file_count"] == 1
    assert cache_info["max_size"] == 5
    assert len(cache_info["cache_keys"]) == 1


def test_get_supported_file_types(data_reader):
    file_types = data_reader.get_supported_file_types()

    assert ".csv" in file_types
    assert ".json" in file_types
    assert ".xml" in file_types
    assert ".h5" in file_types


def test_register_custom_transformation(data_reader):
    def custom_transform(data, data_file):
        return data

    data_reader.register_custom_transformation(str, custom_transform)


def test_read_with_reader_kwargs(data_reader, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv, reader_kwargs={"skip_rows": 1})

    result = data_reader.read_data_file(tmp_path, data_file)
    collected = result.collect()

    assert collected.shape == (1, 3)


def test_cache_key_generation(data_reader, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv)

    key1 = data_reader._generate_cache_key(tmp_path, data_file)
    key2 = data_reader._generate_cache_key(tmp_path, data_file)

    assert key1 == key2
    assert isinstance(key1, str)
    assert key1 != ""


def test_read_json_file(data_reader, sample_json, tmp_path):
    data_file = DataFile(name="json_test", fpath=sample_json)

    result = data_reader.read_data_file(tmp_path, data_file)

    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["num"] == 42
