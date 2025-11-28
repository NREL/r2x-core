"""Utility functions script."""

import os
import platform
from pathlib import Path

from loguru import logger
from rust_ok import Err, Ok, Result


def backup_folder(folder_path: Path | str) -> Result[None, str]:
    """Backup a folder."""
    if isinstance(folder_path, str):
        folder_path = Path(folder_path)

    if not folder_path.exists():
        return Err(error="Folder does not exist")

    import shutil

    backup_folder = folder_path.with_name(f"{folder_path.name}_backup")
    if backup_folder.exists():
        logger.warning("Backup folder already exists, removing: {}", backup_folder)
        shutil.rmtree(backup_folder)

    # It turns out that moving all the files probably faster than one by one.
    shutil.move(str(folder_path), str(backup_folder))
    logger.info("Created backup at: {}", backup_folder)
    shutil.copytree(backup_folder, folder_path)
    return Ok()


def get_r2x_cache_path() -> Path:
    """Return the cache path."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".config"
    return base / "r2x" / "cache"


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


def resolve_path(
    raw_path: Path | str,
    folder_path: Path,
    *,
    must_exist: bool = True,
) -> Result[Path, ValueError | FileNotFoundError]:
    """Resolve raw path relative to the given folder, optionally checking existence."""
    path = Path(raw_path)
    resolved = path if path.is_absolute() else folder_path / path

    if must_exist:
        return audit_file(resolved)
    return Ok(resolved)


def resolve_glob_pattern(path: Path, pattern: str) -> Result[Path, ValueError | FileNotFoundError]:
    """Resolve a glob pattern to a single file path."""
    if not any(wildcard in pattern for wildcard in ["*", "?", "[", "]"]):
        msg = f"Pattern '{pattern}' does not contain glob wildcards (*, ?, [, ]). Use 'fpath' or 'relative_fpath' for exact filenames."
        return Err(ValueError(msg))

    matches = [p for p in path.glob(pattern) if p.is_file()]

    if not matches:
        msg = f"No files found matching pattern '{pattern}' in {path}"
        return Err(FileNotFoundError(msg))

    if len(matches) > 1:
        file_list = "\n".join(f"  - {m.name}" for m in sorted(matches))
        msg = f"Multiple files matched pattern '{pattern}' in {path}:\n{file_list}"
        return Err(ValueError(msg))

    logger.debug("Glob pattern {} resolved to: {}", pattern, matches[0])
    return Ok(matches[0])
