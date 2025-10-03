"""File readers by file type."""

import json
from functools import singledispatch
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree

from h5py import File as h5pyFile
from loguru import logger
from polars import DataFrame, LazyFrame, scan_csv

from .file_types import H5File, JSONFile, TableFile, XMLFile


@singledispatch
def read_file_by_type(file_type_instance: Any, file_path: Path) -> Any:
    """Read file based on FileType instance using single dispatch.

    This is the main dispatch function that routes to specific readers
    based on the file type instance.

    Parameters
    ----------
    file_type_instance : FileType
        FileType instance to dispatch on (TableFile(), H5File(), etc.).
    file_path : Path
        Path to the file to read.

    Returns
    -------
    Any
        Raw file data in the appropriate format.

    Raises
    ------
    NotImplementedError
        If no reader is implemented for the given file type.
    """
    msg = f"No reader implemented for file type: {type(file_type_instance)}"
    raise NotImplementedError(msg)


@read_file_by_type.register
def _(file_type_class: TableFile, file_path: Path) -> LazyFrame:
    """Read CSV/TSV files as LazyFrame.

    Parameters
    ----------
    file_type_class : TableFile
        TableFile class (not used, but required for dispatch).
    file_path : Path
        Path to the CSV/TSV file.

    Returns
    -------
    pl.LazyFrame
        Lazy DataFrame containing the tabular data.
    """
    logger.debug("Reading table file: {}", file_path)
    if file_path.suffix.lower() == ".tsv":
        return scan_csv(file_path, separator="\t")
    return scan_csv(file_path)


@read_file_by_type.register
def _(file_type_class: H5File, file_path: Path) -> LazyFrame:
    """Read HDF5 files as LazyFrame.

    Parameters
    ----------
    file_type_class : H5File
        H5File class (not used, but required for dispatch).
    file_path : Path
        Path to the HDF5 file.

    Returns
    -------
    pl.LazyFrame
        Lazy DataFrame containing the HDF5 data.

    Notes
    -----
    This implementation reads the first dataset found in the HDF5 file.
    For more complex HDF5 structures, customize this method based on your needs.
    """
    logger.debug("Reading H5 file: {}", file_path)
    with h5pyFile(str(file_path), "r") as f:
        # Get the first dataset key
        dataset_key = next(iter(f.keys()))
        dataset = f[dataset_key]

        # Read dataset data
        if hasattr(dataset, "shape") and hasattr(dataset, "__getitem__"):
            data_array = dataset[:]
            # Convert to DataFrame - adjust based on your data structure
            # Cast to Any to simplify type handling - we know this is numpy-like at runtime
            array_data = cast(Any, data_array)
            if array_data.ndim == 1:
                df = DataFrame({dataset_key: array_data})
            else:
                # For multi-dimensional arrays, flatten or handle appropriately
                df = DataFrame(
                    {
                        f"{dataset_key}_col_{i}": array_data[:, i]
                        for i in range(array_data.shape[1])
                    }
                )
            return df.lazy()
        else:
            # Fallback for non-array datasets
            df = DataFrame({dataset_key: [str(dataset)]})
            return df.lazy()


@read_file_by_type.register
def _(file_type_class: JSONFile, file_path: Path) -> dict[str, Any]:
    """Read JSON files as dictionary.

    Parameters
    ----------
    file_type_class : JSONFile
        JSONFile class (not used, but required for dispatch).
    file_path : Path
        Path to the JSON file.

    Returns
    -------
    dict[str, Any]
        Dictionary containing the JSON data.
    """
    logger.debug("Reading JSON file: {}", file_path)
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


@read_file_by_type.register
def _(file_type_class: XMLFile, file_path: Path) -> ElementTree.Element:
    """Read XML files and return the root element.

    Parameters
    ----------
    file_type_class : XMLFile
        XMLFile class (not used, but required for dispatch).
    file_path : Path
        Path to the XML file.

    Returns
    -------
    ElementTree.Element
        Root element of the XML document.
    """
    logger.debug("Reading XML file: {}", file_path)
    tree = ElementTree.parse(str(file_path))
    return tree.getroot()
