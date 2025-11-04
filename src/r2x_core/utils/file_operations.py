"""Utility functions script."""

import os
import platform
from pathlib import Path

from loguru import logger

from ..result import Err, Ok, Result


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
