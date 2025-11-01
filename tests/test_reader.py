import pytest

from r2x_core.datafile import DataFile
from r2x_core.reader import DataReader


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
def reader_example():
    return DataReader()


def test_read_data_file_basic(reader_example, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv)

    result = reader_example.read_data_file(data_file, tmp_path)

    assert result is not None
    collected = result.collect()
    assert collected.shape == (2, 3)


def test_read_optional_missing_file(reader_example, tmp_path):
    dummy_file = tmp_path / "dummy.csv"
    dummy_file.write_text("col1,col2\n1,2\n")

    data_file = DataFile(name="test", fpath=dummy_file, is_optional=True)

    dummy_file.unlink()

    result = reader_example.read_data_file(data_file, tmp_path)

    assert result is None


def test_read_required_missing_file(reader_example, tmp_path):
    dummy_file = tmp_path / "dummy.csv"
    dummy_file.write_text("col1,col2\n1,2\n")

    data_file = DataFile(name="test", fpath=dummy_file, is_optional=False)

    dummy_file.unlink()

    with pytest.raises(FileNotFoundError, match="Missing required file"):
        reader_example.read_data_file(data_file, tmp_path)


def test_custom_reader_function(reader_example, tmp_path):
    test_file = tmp_path / "custom.csv"
    test_file.write_text("custom content")

    def custom_reader(path):
        return path.read_text().upper()

    data_file = DataFile(name="custom", fpath=test_file, reader_function=custom_reader)
    result = reader_example.read_data_file(data_file, tmp_path)

    assert result == "CUSTOM CONTENT"


def test_get_supported_file_types(reader_example):
    file_types = reader_example.get_supported_file_types()

    assert ".csv" in file_types
    assert ".json" in file_types
    assert ".xml" in file_types
    assert ".h5" in file_types


def test_register_custom_transformation(reader_example):
    def custom_transform(data_file, data):
        return data

    reader_example.register_custom_transformation(str, custom_transform)


def test_read_with_reader_kwargs(reader_example, sample_csv, tmp_path):
    data_file = DataFile(name="test", fpath=sample_csv, reader_kwargs={"skip_rows": 1})

    result = reader_example.read_data_file(data_file, tmp_path)
    collected = result.collect()

    assert collected.shape == (1, 3)


def test_read_json_file(reader_example, sample_json, tmp_path):
    data_file = DataFile(name="json_test", fpath=sample_json)

    result = reader_example.read_data_file(data_file, tmp_path)

    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["num"] == 42
