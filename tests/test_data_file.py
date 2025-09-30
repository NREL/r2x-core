"""Test associated to the `FileMapping` data model."""

import pytest
from pydantic import ValidationError

from r2x_core import DataFile
from r2x_core.utils import H5File, JSONFile, TableFile, XMLFile


@pytest.mark.parametrize(
    "extension,expected_file_type",
    [
        (".csv", TableFile),
        (".h5", H5File),
        (".xml", XMLFile),
        (".json", JSONFile),
    ],
)
def test_file_mapping_extension_inference(
    tmp_path, extension, expected_file_type
) -> None:
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
