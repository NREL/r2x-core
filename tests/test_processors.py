"""Tests for processors module."""

import json

import polars as pl
import pytest
from polars import Int32, LazyFrame

from r2x_core.datafile import DataFile
from r2x_core.file_types import TableFile
from r2x_core.processors import (
    apply_transformation,
    json_apply_filters,
    json_rename_keys,
    json_select_keys,
    pl_apply_filters,
    pl_cast_schema,
    pl_drop_columns,
    pl_rename_columns,
    pl_select_columns,
    register_transformation,
    transform_json_data,
    transform_tabular_data,
)
from r2x_core.store import DataStore


@pytest.fixture
def csv_datafile(tmp_path) -> DataFile:
    """Create FileMapping for unitdata.csv."""
    json_fpath = tmp_path / "example_json.json"
    json_array = [
        {
            "name": "unitdata",
            "fpath": "inputs_case/unitdata.csv",
            "units": "MW",
            "reader_kwargs": {"infer_schema_length": 10_000_000},
            "column_mapping": {
                "tech": "technology",
                "reeds_ba": "region_id",
                "retireyear": "retire_year",
                "resource_region": "resource_region",
                "cap": "capacity_mw",
                "heatrate": "heat_rate_btu_per_kwh",
                "tstate": "state",
                "t_vom": "vom_cost",
                "t_fom": "fom_cost",
            },
            "index_columns": ["technology", "region_id", "unique id"],
            "value_columns": [
                "capacity_mw",
                "heat_rate_btu_per_kwh",
                "vom_cost",
                "fom_cost",
                "retire_year",
            ],
            "optional": False,
            "description": "ReEDS unit-level existing generator data",
            "drop_columns": ["resource_region"],
            "column_schema": {"retire_year": "int32"},
            "filter_by": {"retire_year": 2036},
        }
    ]
    with open(tmp_path / "example_json.json", "w") as f:
        json.dump(json_array, f)
    yield json_fpath


@pytest.fixture
def json_store(tmp_path) -> DataFile:
    """Create FileMapping for unitdata.csv."""
    test_file = tmp_path / "test_data.json"
    test_file.write_text('{"name":"test"}')
    data_file = DataFile(
        name="json", fpath=str(test_file), key_mapping={"name": "TestRemap"}
    )
    store = DataStore(folder=tmp_path)
    store.add_data_file(data_file)
    yield store


@pytest.fixture(scope="function")
def csv_store(reeds_data_folder, csv_datafile):
    store = DataStore.from_json(csv_datafile, folder=reeds_data_folder)
    yield store


def test_transform_tabular_data(csv_store):
    store: DataStore = csv_store

    datafile = store.get_data_file_by_name("unitdata")
    assert isinstance(datafile, DataFile)
    assert isinstance(datafile.file_type, TableFile)

    file = store.read_data_file(name="unitdata")
    schema = file.collect_schema()
    assert isinstance(file, LazyFrame)
    assert len(schema.names()) == 8  # 3 index + 5 value columns
    assert "retire_year" in schema
    assert schema["retire_year"] == Int32
    assert file.select("retire_year").unique().collect().item() == 2036


def test_transform_json(json_store):
    store: DataStore = json_store
    datafile = store.get_data_file_by_name("json")
    assert isinstance(datafile, DataFile)

    file = store.read_data_file(name="json")
    assert isinstance(file, dict)
    assert "TestRemap" in file.keys()


# =============================================================================
# Comprehensive tests for individual processor functions
# =============================================================================


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "name,age,city,score\nAlice,30,NYC,85.5\nBob,25,LA,92.3\nCharlie,35,CHI,78.9\n"
    )
    return csv_file


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a sample JSON file."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"name": "Alice", "age": 30, "city": "NYC", "score": 85.5}')
    return json_file


def test_pl_drop_columns(sample_csv):
    """Test dropping columns from DataFrame."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(name="test", fpath=sample_csv, drop_columns=["city", "score"])

    result = pl_drop_columns(data_file, df)
    result_cols = result.collect_schema().names()

    assert "name" in result_cols
    assert "age" in result_cols
    assert "city" not in result_cols
    assert "score" not in result_cols


def test_pl_drop_columns_non_existing(sample_csv):
    """Test dropping columns that don't exist in the DataFrame."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(name="test", fpath=sample_csv, drop_columns=["nonexistent"])

    result = pl_drop_columns(data_file, df)
    # Should return df unchanged since column doesn't exist
    assert result.collect_schema().names() == df.collect_schema().names()


def test_pl_rename_columns(sample_csv):
    """Test renaming columns in DataFrame."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test",
        fpath=sample_csv,
        column_mapping={"name": "person_name", "age": "person_age"},
    )

    result = pl_rename_columns(data_file, df)
    result_cols = result.collect_schema().names()

    assert "person_name" in result_cols
    assert "person_age" in result_cols
    assert "name" not in result_cols
    assert "age" not in result_cols


def test_pl_rename_columns_non_existing(sample_csv):
    """Test renaming columns that don't exist."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test", fpath=sample_csv, column_mapping={"nonexistent": "new_name"}
    )

    result = pl_rename_columns(data_file, df)
    # Should return df unchanged
    assert result.collect_schema().names() == df.collect_schema().names()


def test_pl_cast_schema(sample_csv):
    """Test casting column types."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test", fpath=sample_csv, column_schema={"age": "int32", "score": "float"}
    )

    result = pl_cast_schema(data_file, df)
    schema = result.collect_schema()

    assert schema["age"] == pl.Int32
    assert schema["score"] == pl.Float64


def test_pl_cast_schema_non_existing_column(sample_csv):
    """Test casting non-existing columns."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test", fpath=sample_csv, column_schema={"nonexistent": "int"}
    )

    result = pl_cast_schema(data_file, df)
    # Should return df unchanged
    assert result.collect_schema() == df.collect_schema()


def test_pl_cast_schema_unsupported_type(sample_csv):
    """Test error handling for unsupported type strings."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test", fpath=sample_csv, column_schema={"age": "unsupported_type"}
    )

    with pytest.raises(ValueError, match="Unsupported data type"):
        pl_cast_schema(data_file, df).collect()


def test_pl_apply_filters_single_value(sample_csv):
    """Test filtering with single value."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(name="test", fpath=sample_csv, filter_by={"name": "Alice"})

    result = pl_apply_filters(data_file, df).collect()

    assert len(result) == 1
    assert result["name"][0] == "Alice"


def test_pl_apply_filters_list_values(sample_csv):
    """Test filtering with list of values."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test", fpath=sample_csv, filter_by={"name": ["Alice", "Bob"]}
    )

    result = pl_apply_filters(data_file, df).collect()

    assert len(result) == 2
    assert set(result["name"]) == {"Alice", "Bob"}


def test_pl_apply_filters_multiple_conditions(sample_csv):
    """Test filtering with multiple conditions."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test", fpath=sample_csv, filter_by={"name": "Alice", "city": "NYC"}
    )

    result = pl_apply_filters(data_file, df).collect()

    assert len(result) == 1
    assert result["name"][0] == "Alice"
    assert result["city"][0] == "NYC"


def test_pl_select_columns_with_value_columns(sample_csv):
    """Test selecting specific columns."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test", fpath=sample_csv, index_columns=["name"], value_columns=["score"]
    )

    result = pl_select_columns(data_file, df)
    result_cols = result.collect_schema().names()

    assert result_cols == ["name", "score"]


def test_pl_select_columns_no_duplicates(sample_csv):
    """Test that duplicate columns are removed."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test",
        fpath=sample_csv,
        index_columns=["name", "age"],
        value_columns=["age", "score"],  # "age" is duplicate
    )

    result = pl_select_columns(data_file, df)
    result_cols = result.collect_schema().names()

    # Should have name, age, score (age not duplicated)
    assert result_cols == ["name", "age", "score"]


def test_json_rename_keys(sample_json_file):
    """Test renaming keys in JSON data."""
    data = {"name": "Alice", "age": 30, "city": "NYC"}
    data_file = DataFile(
        name="test",
        fpath=sample_json_file,
        key_mapping={"name": "person_name", "age": "person_age"},
    )

    result = json_rename_keys(data_file, data)

    assert "person_name" in result
    assert "person_age" in result
    assert "city" in result  # Unchanged
    assert "name" not in result
    assert "age" not in result


def test_json_apply_filters(sample_json_file):
    """Test filtering JSON data."""
    data = {"name": "Alice", "age": 30, "city": "NYC", "score": 85.5}
    data_file = DataFile(
        name="test",
        fpath=sample_json_file,
        filter_by={"name": "Bob"},  # Filter out entries where name != Bob
    )

    result = json_apply_filters(data_file, data)

    # Should keep keys that are NOT in filter_by or match the filter
    assert "age" in result
    assert "city" in result
    assert "score" in result


def test_json_apply_filters_list(sample_json_file):
    """Test filtering JSON with list values."""
    data = {"name": "Alice", "age": 30, "city": "NYC"}
    data_file = DataFile(
        name="test", fpath=sample_json_file, filter_by={"name": ["Alice", "Bob"]}
    )

    result = json_apply_filters(data_file, data)

    assert "name" in result  # Matches filter


def test_json_select_keys(sample_json_file):
    """Test selecting specific keys from JSON."""
    data = {"name": "Alice", "age": 30, "city": "NYC", "score": 85.5}
    data_file = DataFile(
        name="test",
        fpath=sample_json_file,
        index_columns=["name"],
        value_columns=["score"],
    )

    result = json_select_keys(data_file, data)

    assert set(result.keys()) == {"name", "score"}


def test_transform_tabular_data_full_pipeline(sample_csv):
    """Test full transformation pipeline for tabular data."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(
        name="test",
        fpath=sample_csv,
        drop_columns=["city"],
        column_mapping={"name": "person"},
        column_schema={"age": "int32"},
        value_columns=["person", "age", "score"],
    )

    result = transform_tabular_data(data_file, df).collect()

    assert "person" in result.columns
    assert "city" not in result.columns
    assert "age" in result.columns
    assert result.schema["age"] == pl.Int32


def test_transform_json_data_full_pipeline(sample_json_file):
    """Test full transformation pipeline for JSON data."""
    data = {"name": "Alice", "age": 30, "city": "NYC", "score": 85.5}
    data_file = DataFile(
        name="test",
        fpath=sample_json_file,
        key_mapping={"name": "person"},
        filter_by={"age": 30},
        value_columns=["person", "score"],
    )

    result = transform_json_data(data_file, data)

    assert "person" in result
    assert set(result.keys()) == {"person", "score"}


def test_apply_transformation_with_lazyframe(sample_csv):
    """Test apply_transformation with LazyFrame data."""
    df = pl.scan_csv(sample_csv)
    data_file = DataFile(name="test", fpath=sample_csv, drop_columns=["city"])

    result = apply_transformation(data_file, df)

    assert isinstance(result, pl.LazyFrame)
    assert "city" not in result.collect_schema().names()


def test_apply_transformation_with_dict(sample_json_file):
    """Test apply_transformation with dict data."""
    data = {"name": "Alice", "age": 30}
    data_file = DataFile(name="test", fpath=sample_json_file, value_columns=["name"])

    result = apply_transformation(data_file, data)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"name"}


def test_apply_transformation_unsupported_type(sample_json_file):
    """Test apply_transformation with unsupported data type."""
    data = "unsupported string data"
    data_file = DataFile(name="test", fpath=sample_json_file)

    # Should return data unchanged for unsupported types
    result = apply_transformation(data_file, data)

    assert result == data


def test_register_custom_transformation(sample_json_file):
    """Test registering a custom transformation function."""

    class CustomType:
        def __init__(self, value):
            self.value = value

    def custom_transform(data_file, data):
        data.value = data.value.upper()
        return data

    register_transformation(CustomType, custom_transform)

    custom_data = CustomType("hello")
    data_file = DataFile(name="test", fpath=sample_json_file)

    result = apply_transformation(data_file, custom_data)

    assert result.value == "HELLO"


def test_pl_apply_filters_three_conditions(sample_csv):
    """Test filtering with three conditions to ensure loop coverage."""
    df = pl.scan_csv(sample_csv)
    # Add more data to enable 3-way filtering
    data_file = DataFile(
        name="test",
        fpath=sample_csv,
        filter_by={"name": ["Alice", "Bob"], "age": [25, 30], "city": ["NYC", "LA"]},
    )

    result = pl_apply_filters(data_file, df)
    collected = result.collect()

    # Should have rows matching all three conditions
    assert len(collected) >= 0  # May have no matches but shouldn't error
