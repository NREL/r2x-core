"""Flexible, configuration-driven HDF5 reader.

This module provides a generic H5 reader that adapts to any file structure
through configuration parameters, without hardcoded model-specific logic.
"""

from datetime import UTC, datetime
from typing import Any

import numpy as np


def configurable_h5_reader(h5_file: Any, **reader_kwargs: Any) -> dict[str, Any]:
    """H5 reader that adapts to any file structure via configuration.

    Parameters
    ----------
    h5_file : h5py.File
        Open HDF5 file handle.
    **reader_kwargs : dict
        Configuration: data_key, columns_key, index_key, datetime_key,
        datetime_column_name (default: "datetime"), additional_keys,
        decode_bytes (default: True), strip_timezone (default: True),
        column_name_mapping (optional: dict mapping dataset keys to column names),
        index_names_key (default: "index_names").

    Returns
    -------
    dict[str, Any]
        Dictionary mapping column names to data arrays.

    Notes
    -----
    The reader supports automatic column name resolution from an index_names
    dataset (e.g., for newer ReEDS format files where indices are named
    index_0, index_1, etc.). The index_names dataset should contain the
    actual names for these generic indices.

    If column_name_mapping is provided, it takes precedence over index_names.
    """
    if not reader_kwargs or not reader_kwargs.get("data_key"):
        return _read_first_dataset(h5_file)

    file_data = {}
    for key in h5_file:
        if key == "index_names":
            # If index names are stored in a dataset in the H5 file, use them to
            # rename relevant index data when attaching to the file_data dictionary
            index_names = [f"index_{name.decode()}" for name in h5_file["index_names"]]
            for index_num, index_name in enumerate(index_names):
                file_data[index_name] = h5_file[f"index_{index_num}"]
        else:
            file_data[key] = h5_file[key]

    data_key = reader_kwargs["data_key"]
    columns_key = reader_kwargs.get("columns_key")
    decode_bytes = reader_kwargs.get("decode_bytes", True)

    data = file_data[data_key][:]
    result: dict[str, Any] = {}

    if columns_key and columns_key in file_data:
        columns = file_data[columns_key][:]
        if decode_bytes and columns.dtype.kind == "S":
            columns = columns.astype(str)
        if data.ndim == 2:
            result = {col: data[:, i] for i, col in enumerate(columns)}
        else:
            result[columns[0]] = data
    else:
        if data.ndim == 1:
            result[data_key] = data
        else:
            result = {f"{data_key}_col_{i}": data[:, i] for i in range(data.shape[1])}

    # Build column name mapping from index_names dataset if present
    column_mapping = reader_kwargs.get("column_name_mapping", {})
    if not column_mapping:
        index_names_key = reader_kwargs.get("index_names_key", "index_names")
        if index_names_key in h5_file:
            index_names = h5_file[index_names_key][:]
            if decode_bytes and index_names.dtype.kind == "S":
                index_names = index_names.astype(str)
            # Map index_0, index_1, etc. to their actual names
            for i, name in enumerate(index_names):
                column_mapping[f"index_{i}"] = name

    datetime_key = reader_kwargs.get("datetime_key")
    if datetime_key and datetime_key in file_data:
        dt_data = file_data[datetime_key][:]
        if decode_bytes and dt_data.dtype.kind == "S":
            dt_data = dt_data.astype(str)

        if len(dt_data) > 0 and isinstance(dt_data[0], str):
            dt_parsed = _parse_datetime_array(dt_data, reader_kwargs.get("strip_timezone", True))
            result[reader_kwargs.get("datetime_column_name", "datetime")] = dt_parsed
        else:
            result[reader_kwargs.get("datetime_column_name", "datetime")] = dt_data

    index_key = reader_kwargs.get("index_key")
    if index_key and index_key in file_data and index_key != datetime_key:
        result[index_key] = file_data[index_key][:]

    for key in reader_kwargs.get("additional_keys", []):
        if key in h5_file:
            # Use mapped name if available, otherwise format the key
            if key in column_mapping:
                col_name = _format_column_name(column_mapping[key])
            else:
                col_name = _format_column_name(key)
            result[col_name] = h5_file[key][:]

    return result


def _read_first_dataset(h5_file: Any) -> dict[str, Any]:
    """Read first dataset in file as default behavior."""
    key = next(iter(h5_file.keys()))
    dataset = h5_file[key]

    try:
        data = dataset[:]
    except (TypeError, AttributeError):
        return {key: [str(dataset)]}

    if data.ndim == 1:
        return {key: data}
    return {f"{key}_col_{i}": data[:, i] for i in range(data.shape[1])}


def _parse_datetime_array(dt_strings: Any, strip_timezone: bool) -> Any:
    """Parse array of datetime strings using standard library.

    Parameters
    ----------
    dt_strings : array-like
        Array of datetime strings in ISO 8601 format.
    strip_timezone : bool
        Whether to convert timezone-aware datetimes to timezone-naive.
        If False, converts to UTC before making naive.

    Returns
    -------
    np.ndarray
        Array of datetime64[us] values (always timezone-naive).

    Raises
    ------
    ValueError
        If datetime strings cannot be parsed.
    """
    parsed: list[datetime] = []
    for i, dt_str in enumerate(dt_strings):
        try:
            dt_obj = datetime.fromisoformat(dt_str)

            if dt_obj.tzinfo is not None:
                if strip_timezone:
                    # Strip timezone info (keep local time)
                    dt_obj = dt_obj.replace(tzinfo=None)
                else:
                    # Convert to UTC then make naive
                    dt_obj = dt_obj.astimezone(UTC).replace(tzinfo=None)

            parsed.append(dt_obj)
        except (ValueError, AttributeError) as e:
            msg = f"Failed to parse datetime string at index {i}: '{dt_str}'. Expected ISO 8601 format. Error: {e}"
            raise ValueError(msg) from e

    return np.array(parsed, dtype="datetime64[us]")


def _format_column_name(key: str) -> str:
    """Format H5 dataset key into clean column name."""
    key_lower = key.lower()
    if "index_year" in key_lower or key_lower == "solve_year":
        return "solve_year"
    if "year" in key_lower:
        return "year"
    return key.replace("index_", "")
