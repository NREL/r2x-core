"""Utility functions script."""

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationInfo

from .file_types import EXTENSION_MAPPING


def filter_valid_kwargs(
    func: Callable[..., Any], kwargs: dict[str, Any]
) -> dict[str, Any]:
    """Filter kwargs to only include valid parameters for the given function."""
    sig = inspect.signature(func)
    valid_params = set(sig.parameters.keys())
    return {k: v for k, v in kwargs.items() if k in valid_params}


def validate_file_extension(path: Path, info: ValidationInfo) -> Path:
    """Validate that the file path has a supported extension.

    This is a Pydantic validator that checks if the file extension from the
    provided path exists as a key in the module-level `EXTENSION_MAPPING`.

    Parameters
    ----------
    value : str
        The file path string to validate, provided by Pydantic.
    info : pydantic.ValidationInfo
        Pydantic's validation context. Required by the validator signature
        but not used in this function.

    Returns
    -------
    Path
        The original file path string if its extension is valid.

    Raises
    ------
    AssertionError
        If the input `value` is not a string.
    ValueError
        If the file path has no extension.
    KeyError
        If the file's extension is not found in `EXTENSION_MAPPING`.

    Notes
    -----
    This function is intended for use as a Pydantic model validator (e.g.,
    with `@field_validator` or `AfterValidator`) and should not be called directly.
    """
    assert info is not None, "Pydantic validation context is missing."
    assert isinstance(path, Path)
    ext = path.suffix.lower()
    if ext not in EXTENSION_MAPPING:
        msg = f"{ext=} not found on `EXTENSION_MAPPING`. "
        msg += "Check spelling of file type or verify it is a supported `FileType`."
        msg += f"List of supported `FileType`: {EXTENSION_MAPPING.keys()}"
        raise KeyError(msg)
    return path
