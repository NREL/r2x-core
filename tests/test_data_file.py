"""Test associated to the `FileMapping` data model."""

import pytest
from pydantic import ValidationError

from r2x_core import DataFile
from r2x_core.file_types import EXTENSION_MAPPING


@pytest.mark.parametrize(
    "extension,expected_file_type",
    [(k, v) for k, v in EXTENSION_MAPPING.items()],
)
def test_file_mapping_extension_inference(tmp_path, extension, expected_file_type) -> None:
    """Test that FileMapping correctly infers file type from extension."""
    test_file = tmp_path / f"test_data{extension}"
    test_file.write_text("")
    mapping = DataFile(name="test", fpath=str(test_file))
    assert mapping is not None
    assert isinstance(mapping.file_type, expected_file_type)


def test_file_mapping_non_existing_file() -> None:
    with pytest.raises(ValidationError):
        _ = DataFile(name="test", fpath="test_data.gas")


def test_file_mapping_bad_extension(tmp_path) -> None:
    test_file = tmp_path / "test_data.gas"
    test_file.write_text("")
    with pytest.raises(KeyError, match="List of supported"):
        _ = DataFile(name="test", fpath=str(tmp_path / "test_data.gas"))


def test_file_mapping_timeseries_parquet(tmp_path) -> None:
    """Test that parquet files can be marked as time series."""
    test_file = tmp_path / "test_data.parquet"
    test_file.write_text("")
    mapping = DataFile(name="test", fpath=str(test_file), is_timeseries=True)
    assert mapping.is_timeseries is True


def test_file_mapping_timeseries_json_fails(tmp_path) -> None:
    """Test that JSON files cannot be marked as time series."""
    test_file = tmp_path / "test_data.json"
    test_file.write_text("")
    mapping = DataFile(name="test", fpath=str(test_file), is_timeseries=True)
    with pytest.raises(ValueError, match="does not support time series"):
        _ = mapping.file_type


def test_file_type_without_fpath_or_glob() -> None:
    """Test that file_type raises error when neither fpath nor glob is set.

    This is defensive code that should never be reached in normal usage
    due to model_validator, but we test it by bypassing validation.
    """
    # Use model_construct to bypass validators
    # NOTE: This is the only way to bypass the Pydantic validation.
    mapping = DataFile.model_construct(name="test", fpath=None, glob=None)

    with pytest.raises(
        ValueError, match="Either fpath, relative_fpath, or glob must be set to determine file type"
    ):
        _ = mapping.file_type
