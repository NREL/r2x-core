"""Tests for H5 readers module."""

import tempfile
from pathlib import Path

import h5py
import numpy as np
import pytest

from r2x_core.h5_readers import configurable_h5_reader


def test_configurable_h5_reader_default_1d():
    """Test configurable H5 reader with no config (default) and 1D data."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create a simple H5 file with 1D data
        with h5py.File(str(tmp_path), "w") as f:
            f.create_dataset("test_data", data=np.array([1.0, 2.0, 3.0, 4.0, 5.0]))

        # Read it with no config (uses default)
        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(f)

        assert "test_data" in result
        assert len(result["test_data"]) == 5
        assert result["test_data"][0] == 1.0
    finally:
        tmp_path.unlink()


def test_configurable_h5_reader_default_2d():
    """Test configurable H5 reader with no config (default) and 2D data."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create a simple H5 file with 2D data
        with h5py.File(str(tmp_path), "w") as f:
            data = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
            f.create_dataset("test_data", data=data)

        # Read it with no config (uses default)
        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(f)

        assert "test_data_col_0" in result
        assert "test_data_col_1" in result
        assert len(result["test_data_col_0"]) == 3
        assert result["test_data_col_0"][0] == 1.0
        assert result["test_data_col_1"][1] == 4.0
    finally:
        tmp_path.unlink()


def test_configurable_h5_reader_with_columns_and_datetime():
    """Test configurable H5 reader with columns and datetime parsing."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create an H5 file with columns, data, and datetime
        with h5py.File(str(tmp_path), "w") as f:
            columns = np.array(["region1", "region2"], dtype="S")
            data = np.array([[100.0, 150.0], [120.0, 160.0], [110.0, 155.0]])
            dt_strings = np.array(
                [
                    "2007-01-01T00:00:00-06:00",
                    "2007-01-01T01:00:00-06:00",
                    "2007-01-01T02:00:00-06:00",
                ],
                dtype="S",
            )
            solve_years = np.array([2030, 2030, 2030])

            f.create_dataset("columns", data=columns)
            f.create_dataset("data", data=data)
            f.create_dataset("index_datetime", data=dt_strings)
            f.create_dataset("index_year", data=solve_years)

        # Read it with configuration (ReEDS-style via config)
        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="data",
                columns_key="columns",
                datetime_key="index_datetime",
                additional_keys=["index_year"],
            )

        assert "region1" in result
        assert "region2" in result
        assert "datetime" in result
        assert "solve_year" in result
        assert len(result["region1"]) == 3
        assert result["region1"][0] == 100.0
        assert result["solve_year"][0] == 2030
    finally:
        tmp_path.unlink()


def test_configurable_h5_reader_without_solve_year():
    """Test configurable H5 reader without solve_year."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create an H5 file without solve_year
        with h5py.File(str(tmp_path), "w") as f:
            columns = np.array(["cf1", "cf2"], dtype="S")
            data = np.array([[0.5, 0.6], [0.7, 0.8]])
            dt_strings = np.array(["2007-01-01T00:00:00-06:00", "2007-01-01T01:00:00-06:00"], dtype="S")

            f.create_dataset("columns", data=columns)
            f.create_dataset("data", data=data)
            f.create_dataset("index_datetime", data=dt_strings)

        # Read it with configuration
        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="data",
                columns_key="columns",
                datetime_key="index_datetime",
            )

        assert "cf1" in result
        assert "cf2" in result
        assert "datetime" in result
        assert "solve_year" not in result
    finally:
        tmp_path.unlink()


def test_configurable_h5_reader_custom_keys():
    """Test configurable H5 reader with custom dataset keys."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create a custom H5 file structure
        with h5py.File(str(tmp_path), "w") as f:
            col_names = np.array(["col_a", "col_b"], dtype="S")
            values = np.array([[1.0, 2.0], [3.0, 4.0]])
            timestamps = np.array([0, 1])
            metadata = np.array([100])

            f.create_dataset("column_names", data=col_names)
            f.create_dataset("values", data=values)
            f.create_dataset("timestamps", data=timestamps)
            f.create_dataset("extra_info", data=metadata)

        # Read it with custom configuration
        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="values",
                columns_key="column_names",
                index_key="timestamps",
                additional_keys=["extra_info"],
            )

        assert "col_a" in result
        assert "col_b" in result
        assert "timestamps" in result
        assert "extra_info" in result
        assert result["col_a"][0] == 1.0
        assert result["timestamps"][1] == 1
    finally:
        tmp_path.unlink()


def test_configurable_h5_reader_no_config_defaults():
    """Test that omitting all config parameters uses default behavior."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create a simple H5 file
        with h5py.File(str(tmp_path), "w") as f:
            f.create_dataset("data", data=np.array([1, 2, 3]))

        # Read it without any config
        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(f)

        assert "data" in result
        assert len(result["data"]) == 3
    finally:
        tmp_path.unlink()


def test_1d_data_with_columns():
    """Test 1D data when columns_key is provided (line 47)."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with h5py.File(str(tmp_path), "w") as f:
            columns = np.array(["single_col"], dtype="S")
            data = np.array([1.0, 2.0, 3.0])
            f.create_dataset("columns", data=columns)
            f.create_dataset("data", data=data)

        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="data",
                columns_key="columns",
            )

        assert "single_col" in result
        assert len(result["single_col"]) == 3
    finally:
        tmp_path.unlink()


def test_1d_data_without_columns_key():
    """Test 1D data without columns_key (lines 50-51)."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with h5py.File(str(tmp_path), "w") as f:
            data = np.array([10.0, 20.0, 30.0])
            f.create_dataset("my_data", data=data)

        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="my_data",
            )

        assert "my_data" in result
        assert len(result["my_data"]) == 3
    finally:
        tmp_path.unlink()


def test_2d_data_without_columns_key():
    """Test 2D data without columns_key (line 52)."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with h5py.File(str(tmp_path), "w") as f:
            data = np.array([[1.0, 2.0], [3.0, 4.0]])
            f.create_dataset("values", data=data)

        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="values",
            )

        assert "values_col_0" in result
        assert "values_col_1" in result
        assert result["values_col_0"][0] == 1.0
    finally:
        tmp_path.unlink()


def test_non_string_datetime():
    """Test datetime data that's not strings (line 64)."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with h5py.File(str(tmp_path), "w") as f:
            data = np.array([1.0, 2.0])
            dt_numeric = np.array([1609459200, 1609545600])
            f.create_dataset("data", data=data)
            f.create_dataset("time", data=dt_numeric)

        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="data",
                datetime_key="time",
            )

        assert "datetime" in result
        assert len(result["datetime"]) == 2
    finally:
        tmp_path.unlink()


def test_datetime_with_timezone_kept():
    """Test datetime parsing with timezone kept (lines 118-119)."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with h5py.File(str(tmp_path), "w") as f:
            data = np.array([1.0, 2.0])
            dt_strings = np.array(
                ["2007-01-01T00:00:00-06:00", "2007-01-01T01:00:00-06:00"],
                dtype="S",
            )
            f.create_dataset("data", data=data)
            f.create_dataset("time", data=dt_strings)

        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="data",
                datetime_key="time",
                strip_timezone=False,
            )

        assert "datetime" in result
    finally:
        tmp_path.unlink()


def test_datetime_parsing_error():
    """Test datetime parsing error handling (lines 121-123)."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with h5py.File(str(tmp_path), "w") as f:
            data = np.array([1.0, 2.0])
            dt_strings = np.array(["invalid-datetime", "also-invalid"], dtype="S")
            f.create_dataset("data", data=data)
            f.create_dataset("time", data=dt_strings)

        with (
            h5py.File(str(tmp_path), "r") as f,
            pytest.raises(ValueError, match="Failed to parse datetime string"),
        ):
            configurable_h5_reader(
                f,
                data_key="data",
                datetime_key="time",
            )
    finally:
        tmp_path.unlink()


def test_format_column_name_year():
    """Test _format_column_name for year variations (line 134)."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with h5py.File(str(tmp_path), "w") as f:
            data = np.array([1.0, 2.0])
            f.create_dataset("data", data=data)
            f.create_dataset("model_year", data=np.array([2030, 2035]))

        with h5py.File(str(tmp_path), "r") as f:
            result = configurable_h5_reader(
                f,
                data_key="data",
                additional_keys=["model_year"],
            )

        assert "year" in result
    finally:
        tmp_path.unlink()
