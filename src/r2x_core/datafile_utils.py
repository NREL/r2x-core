"""Utilities for data file operations."""

from pathlib import Path

from loguru import logger
from rust_ok import Result

from .datafile import DataFile, FileInfo
from .utils import audit_file, resolve_glob_pattern


def get_fpath(
    data_file: DataFile, folder_path: Path, info: FileInfo | None
) -> Result[Path, ValueError | FileNotFoundError]:
    """Get the resolved file path (absolute, relative, or glob), validated with audit.

    Parameters
    ----------
    data_file : DataFile
        The data file configuration.
    folder_path : Path
        The base folder path to resolve relative paths against.
    info : FileInfo | None
        Optional file metadata (not used here, but available for future extensions).

    Returns
    -------
    Result[Path, ValueError | FileNotFoundError]
        Ok(Path) if file is found.
        Err(ValueError) if configuration is invalid or multiple files match.
        Err(FileNotFoundError) if file is not found.
    """
    assert any((data_file.glob, data_file.relative_fpath, data_file.fpath)), (
        "DataFile must have fpath, relative_fpath, or glob"
    )

    if data_file.glob is not None:
        return resolve_glob_pattern(folder_path, data_file.glob)
    if data_file.relative_fpath is not None:
        fpath = folder_path / Path(data_file.relative_fpath)
        logger.trace("Resolved relative_fpath={} for file={}", fpath, data_file.name)
        return audit_file(fpath)

    # NOTE: DataFile needs to have at least one of the above defined. At this
    # point, the only possible branch is that fpath is defined. Asserting is
    # just a guard for mypy
    assert data_file.fpath
    fpath = Path(data_file.fpath)
    logger.trace("Resolved absolute fpath={} for file={}", fpath, data_file.name)
    return audit_file(fpath)
