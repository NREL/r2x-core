"""Utilities for data file operations."""

from pathlib import Path

from loguru import logger

from .datafile import DataFile, FileInfo
from .exceptions import MultipleFileError
from .result import Err, Ok, Result


def get_file_path(
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

    Notes
    -----
    This function does NOT handle optional files. The caller is responsible for
    checking if a file is optional and handling FileNotFoundError accordingly.
    """
    if data_file.glob is not None:
        return resolve_glob_pattern(data_file, folder_path)
    elif data_file.relative_fpath is not None:
        fpath = folder_path / Path(data_file.relative_fpath)
        logger.trace("Resolved relative_fpath={} for file={}", fpath, data_file.name)
        return audit_file(fpath)
    elif data_file.fpath is not None:
        fpath = Path(data_file.fpath)
        logger.trace("Resolved absolute fpath={} for file={}", fpath, data_file.name)
        return audit_file(fpath)
    else:
        return Err(ValueError("DataFile must have fpath, relative_fpath, or glob"))


def audit_file(fpath: Path) -> Result[Path, ValueError | FileNotFoundError]:
    """Check if a path exists and return it, or return FileNotFoundError.

    Parameters
    ----------
    fpath : Path
        The file path to check.

    Returns
    -------
    Result[Path, ValueError | FileNotFoundError]
        Ok(Path) if the file exists.
        Err(FileNotFoundError) if the file does not exist.
    """
    if fpath.exists():
        return Ok(fpath)
    return Err(FileNotFoundError(f"Missing required file: {fpath}"))


def resolve_glob_pattern(
    data_file: DataFile, folder_path: Path
) -> Result[Path, ValueError | FileNotFoundError]:
    """Resolve a glob pattern to a single file path.

    Parameters
    ----------
    data_file : DataFile
        The data file configuration containing the glob pattern.
    folder_path : Path
        The base folder path to search within.

    Returns
    -------
    Result[Path, ValueError | FileNotFoundError]
        Ok(Path) if exactly one file matches the pattern.
        Err(ValueError) if the pattern is malformed.
        Err(MultipleFileError) if multiple files match (subclass of ValueError).
        Err(FileNotFoundError) if no files match the pattern.
    """
    pattern = data_file.glob
    if pattern is None:
        return Err(ValueError("DataFile must have a glob pattern"))

    # Validate that the pattern contains wildcards
    if not any(wildcard in pattern for wildcard in ["*", "?", "[", "]"]):
        msg = f"Pattern '{pattern}' does not contain glob wildcards (*, ?, [, ]). Use 'fpath' or 'relative_fpath' for exact filenames."
        return Err(ValueError(msg))

    matches = [p for p in folder_path.glob(pattern) if p.is_file()]

    if not matches:
        msg = f"No files found matching pattern '{pattern}' in {folder_path}"
        return Err(FileNotFoundError(msg))

    if len(matches) > 1:
        file_list = "\n".join(f"  - {m.name}" for m in sorted(matches))
        msg = f"Multiple files matched pattern '{pattern}' in {folder_path}:\n{file_list}"
        return Err(MultipleFileError(msg))

    logger.debug("Glob pattern {} resolved to: {}", pattern, matches[0])
    return Ok(matches[0])
