"""Functional tests for processors module.

These tests focus on realistic processor behavior using TabularProcessing and JSONProcessing
models. Each test exercises a specific processor function with real data to ensure filtering,
renaming, dropping, casting, and pivoting work as expected.
"""

import json
from pathlib import Path

import polars as pl
import pytest

from r2x_core.datafile import DataFile, JSONProcessing, TabularProcessing
from r2x_core.processors import (
    json_apply_filters,
    json_rename_keys,
    json_select_keys,
    pl_apply_filters,
    pl_cast_schema,
    pl_drop_columns,
    pl_pivot_on,
    pl_rename_columns,
)


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Create a small CSV with realistic data for testing."""
    csv = tmp_path / "people.csv"
    csv.write_text(
        "name,age,city,score,retire_year\n"
        "Alice,30,NYC,85.5,2036\n"
        "Bob,25,LA,92.3,2036\n"
        "Charlie,35,CHI,78.9,2040\n"
        "Dana,40,NYC,88.0,2036\n"
    )
    return csv


@pytest.fixture
def sample_json_file(tmp_path: Path) -> Path:
    """Create a small JSON file for testing."""
    jf = tmp_path / "sample.json"
    jf.write_text(json.dumps({"name": "Alice", "age": 30, "city": "NYC", "score": 85.5}))
    return jf


def test_pl_apply_filters_single_value(sample_csv: Path):
    """Test filtering with a single value."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(filter_by={"name": "Alice"})
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_apply_filters(df_file, lf, proc_spec).collect()

    assert len(result) == 1
    assert result["name"][0] == "Alice"


def test_pl_apply_filters_list_values(sample_csv: Path):
    """Test filtering with a list of values."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(filter_by={"name": ["Alice", "Bob"]})
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_apply_filters(df_file, lf, proc_spec).collect()

    assert len(result) == 2
    names = set(result["name"].to_list())
    assert names == {"Alice", "Bob"}


def test_pl_apply_filters_multiple_conditions(sample_csv: Path):
    """Test filtering with multiple conditions (AND logic)."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(filter_by={"retire_year": 2036, "age": 30})
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_apply_filters(df_file, lf, proc_spec).collect()

    assert len(result) == 1
    assert result["name"][0] == "Alice"


def test_pl_drop_columns_removes_existing(sample_csv: Path):
    """Test that drop_columns removes specified columns."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(drop_columns=["city", "score"])
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_drop_columns(df_file, lf, proc_spec).collect()

    assert "city" not in result.columns
    assert "score" not in result.columns
    assert "name" in result.columns
    assert "age" in result.columns


def test_pl_drop_columns_noop_on_missing(sample_csv: Path):
    """Test that drop_columns is a no-op for non-existent columns."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(drop_columns=["nonexistent"])
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_drop_columns(df_file, lf, proc_spec).collect()

    assert set(result.columns) == set(pl.scan_csv(sample_csv).collect().columns)


def test_pl_rename_columns_renames_existing(sample_csv: Path):
    """Test that column_mapping renames columns correctly."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(column_mapping={"name": "person_name", "age": "person_age"})
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_rename_columns(df_file, lf, proc_spec).collect()

    assert "person_name" in result.columns
    assert "person_age" in result.columns
    assert "name" not in result.columns
    assert "age" not in result.columns


def test_pl_rename_columns_noop_on_missing(sample_csv: Path):
    """Test that column_mapping is a no-op for non-existent columns."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(column_mapping={"nonexistent": "new_name"})
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_rename_columns(df_file, lf, proc_spec).collect()

    assert set(result.columns) == set(pl.scan_csv(sample_csv).collect().columns)


def test_pl_cast_schema_casts_columns(sample_csv: Path):
    """Test that column_schema casts columns to correct types."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(column_schema={"age": "int32", "retire_year": "int32"})
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_cast_schema(df_file, lf, proc_spec).collect()

    assert result.schema["age"] == pl.Int32
    assert result.schema["retire_year"] == pl.Int32


def test_pl_cast_schema_unsupported_type_raises(sample_csv: Path):
    """Test that unsupported type strings raise ValueError."""
    lf = pl.scan_csv(sample_csv)
    proc_spec = TabularProcessing(column_schema={"age": "invalid_type"})
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    with pytest.raises(ValueError, match="Unsupported data type"):
        pl_cast_schema(df_file, lf, proc_spec).collect()


def test_pl_pivot_on_unpivots_columns(sample_csv: Path):
    """Test that pivot_on unpivots columns into rows."""
    lf = pl.LazyFrame({"2020": [100], "2025": [200], "2030": [300]})
    proc_spec = TabularProcessing(pivot_on="year")
    df_file = DataFile(name="test", fpath=sample_csv, proc_spec=proc_spec)

    result = pl_pivot_on(df_file, lf, proc_spec).collect()

    assert result.columns == ["year"]
    assert result.height == 3
    assert result["year"].to_list() == [100, 200, 300]


def test_json_rename_keys_renames_keys(sample_json_file: Path):
    """Test that key_mapping renames JSON keys."""
    data = {"name": "Alice", "age": 30, "city": "NYC"}
    proc_spec = JSONProcessing(key_mapping={"name": "person_name", "age": "person_age"})
    df_file = DataFile(name="test", fpath=sample_json_file, proc_spec=proc_spec)

    result = json_rename_keys(df_file, data, proc_spec)

    assert "person_name" in result
    assert "person_age" in result
    assert "name" not in result
    assert "age" not in result
    assert result["person_name"] == "Alice"


def test_json_apply_filters_filters_by_value(sample_json_file: Path):
    """Test that JSON filtering works correctly."""
    data = {"name": "Alice", "age": 30, "city": "NYC", "score": 85.5}
    proc_spec = JSONProcessing(filter_by={"age": 30})
    df_file = DataFile(name="test", fpath=sample_json_file, proc_spec=proc_spec)

    result = json_apply_filters(df_file, data, proc_spec)

    assert "age" in result


def test_json_apply_filters_filters_list_values(sample_json_file: Path):
    """Test that JSON filtering works with lists."""
    data = {"name": "Alice", "age": 30, "city": "NYC"}
    proc_spec = JSONProcessing(filter_by={"name": ["Alice", "Bob"]})
    df_file = DataFile(name="test", fpath=sample_json_file, proc_spec=proc_spec)

    result = json_apply_filters(df_file, data, proc_spec)

    assert "name" in result


def test_json_select_keys_keeps_specified_keys(sample_json_file: Path):
    """Test that select_keys keeps only specified keys."""
    data = {"name": "Alice", "age": 30, "city": "NYC", "score": 85.5}
    proc_spec = JSONProcessing(select_keys=["name", "score"])
    df_file = DataFile(name="test", fpath=sample_json_file, proc_spec=proc_spec)

    result = json_select_keys(df_file, data, proc_spec)

    assert set(result.keys()) == {"name", "score"}
