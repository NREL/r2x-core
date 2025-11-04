"""Utilities for data file operations."""

from pathlib import Path
from typing import cast

from loguru import logger

from .datafile import DataFile, FileInfo
from .result import Err, Ok, Result


def get_file_path(
    data_file: DataFile, folder_path: Path, info: FileInfo | None
) -> Result[Path | None, FileNotFoundError]:
    """Get the resolved file path (absolute, relative, or glob), validated with audit."""
    if data_file.glob is not None:
        resolved = resolve_glob_pattern(data_file, folder_path, info)
    elif data_file.relative_fpath is not None:
        fpath = folder_path / Path(data_file.relative_fpath)
        logger.trace("Resolved relative_fpath={} for file={}", fpath, data_file.name)
        resolved = Ok(fpath)
    elif data_file.fpath is not None:
        fpath = Path(data_file.fpath)
        logger.trace("Resolved absolute fpath={} for file={}", fpath, data_file.name)
        resolved = Ok(fpath)
    else:
        return Err(FileNotFoundError("DataFile must have fpath, relative_fpath, or glob"))

    return resolved.and_then(lambda p: _audit_path(p, info))


def _audit_path(fpath: Path | None, info: FileInfo | None) -> Result[Path | None, FileNotFoundError]:
    """Audit a file path, returning it if valid or None if optional and missing."""
    if fpath is None:
        return cast(Result[Path | None, FileNotFoundError], Ok(None))

    is_optional = info.is_optional if info else False

    if fpath.exists():
        return Ok(fpath)

    if is_optional:
        logger.debug("Optional file {} not found.", fpath)
        return cast(Result[Path | None, FileNotFoundError], Ok(None))

    return Err(FileNotFoundError(f"Missing required file: {fpath}"))


def resolve_glob_pattern(
    data_file: DataFile, folder_path: Path, info: FileInfo | None
) -> Result[Path | None, FileNotFoundError]:
    """Resolve a glob pattern to a single file path."""
    pattern = data_file.glob
    if pattern is None:
        return Err(FileNotFoundError("DataFile must have a glob pattern"))

    matches = [p for p in folder_path.glob(pattern) if p.is_file()]
    is_optional = info.is_optional if info else False

    if not matches:
        if is_optional:
            logger.debug("Optional glob pattern {} matched no files, returning None", pattern)
            return cast(Result[Path | None, FileNotFoundError], Ok(None))
        msg = f"No files found matching pattern '{pattern}' in {folder_path}"
        return Err(FileNotFoundError(msg))

    if len(matches) > 1:
        file_list = "\n".join(f"  - {m.name}" for m in sorted(matches))
        msg = f"Multiple files matched pattern '{pattern}' in {folder_path}:\n{file_list}"
        return Err(FileNotFoundError(msg))

    logger.debug("Glob pattern '%s' resolved to: %s", pattern, matches[0])
    return Ok(matches[0])
