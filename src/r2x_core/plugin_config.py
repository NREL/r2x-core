"""Base configuration class for plugins.

This module provides the foundational configuration class that plugin implementations
should inherit from to define model-specific parameters. This applies to parsers,
exporters, and system modifiers.

The PluginConfig class is a pure Pydantic model designed to serialize cleanly to JSON
for cross-language compatibility (Python/Rust). Loading logic for defaults and file
mappings is handled through separate class methods that the CLI orchestrates.

Classes
-------
PluginConfig
    Base configuration class with support for loading external configuration files.

Examples
--------
Create a model-specific configuration:

>>> from r2x_core.plugin_config import PluginConfig
>>> from pydantic import field_validator
>>>
>>> class ReEDSConfig(PluginConfig):
...     solve_year: int
...     weather_year: int
...     scenario: str = "base"
...
...     @field_validator("solve_year")
...     @classmethod
...     def validate_year(cls, v):
...         if v < 2020 or v > 2050:
...             raise ValueError("Year must be between 2020 and 2050")
...         return v
>>>
>>> config = ReEDSConfig(
...     solve_year=2030,
...     weather_year=2012,
...     scenario="high_re"
... )

Load defaults from JSON:

>>> defaults = ReEDSConfig.load_defaults()
>>> # Use constants in your parser/exporter logic

Load file mapping from JSON:

>>> file_mapping = ReEDSConfig.load_file_mapping()

Load with overrides:

>>> defaults = ReEDSConfig.load_defaults(
...     overrides={"excluded_techs": ["solar"]}
... )
>>> file_mapping = ReEDSConfig.load_file_mapping(
...     file_overrides={"data_file": "/custom/path.csv"}
... )

See Also
--------
r2x_core.parser.BaseParser : Uses this configuration class
r2x_core.exporter.BaseExporter : Uses this configuration class
"""

import inspect
import json
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from pydantic import BaseModel, Field, model_validator


class PluginConfig(BaseModel):
    """Pure Pydantic base configuration class for plugins.

    This class defines the configuration interface for parsers, exporters,
    and system modifiers. Subclasses should define model-specific parameters.

    The class is designed to be:
    - Serializable to JSON for Rust interoperability
    - Pure data structure (no side effects)
    - Combined with external loading methods for defaults and file mappings

    Attributes
    ----------
    config_path : Path | None
        Path to the configuration directory. If None, defaults to the 'config'
        subdirectory relative to the subclass module location. Excluded from
        serialization.

    Class Variables
    ----------------
    CONFIG_DIR : str
        Name of the config directory relative to the module (default: "config")
    FILE_MAPPING_NAME : str
        Filename for file mappings (default: "file_mapping.json")
    DEFAULTS_FILE_NAME : str
        Filename for default values (default: "defaults.json")

    Methods
    -------
    load_defaults(config_path=None, overrides=None)
        Load default values from defaults.json with optional overrides.
    load_file_mapping(config_path=None, file_overrides=None)
        Load file mappings from file_mapping.json with optional path overrides.

    Notes
    -----
    Config directory structure expected:

    .. code-block:: text

        plugin_package/
        ├── config/
        │   ├── defaults.json       # Default model parameters
        │   └── file_mapping.json   # File path mappings
        └── ...

    The defaults.json file should be a dict with default values.
    The file_mapping.json file should be a list of dicts with structure:

    .. code-block:: json

        [
            {
                "name": "data_file",
                "fpath": "*.csv",
                "description": "Input data file pattern"
            }
        ]

    See Also
    --------
    :class:`BaseParser` : Uses PluginConfig for input parameters
    :class:`BaseExporter` : Uses PluginConfig for output configuration
    """

    CONFIG_DIR: ClassVar[str] = "config"
    FILE_MAPPING_NAME: ClassVar[str] = "file_mapping.json"
    DEFAULTS_FILE_NAME: ClassVar[str] = "defaults.json"

    config_path: Path | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def resolve_config_path(self) -> "PluginConfig":
        """Resolve config path to the config directory of the plugin module."""
        if self.config_path is None:
            module_file = inspect.getfile(self.__class__)
            self.config_path = Path(module_file).parent / self.CONFIG_DIR
        assert isinstance(self.config_path, Path)
        return self

    @property
    def file_mapping_path(self) -> Path:
        """Get path to file mapping configuration file.

        Returns
        -------
        Path
            Path to file_mapping.json in config directory

        Notes
        -----
        This property is provided for backward compatibility. Use the
        load_file_mapping() classmethod for new code.
        """
        assert self.config_path is not None
        return self.config_path / self.FILE_MAPPING_NAME

    @property
    def defaults_path(self) -> Path:
        """Get path to defaults configuration file.

        Returns
        -------
        Path
            Path to defaults.json in config directory

        Notes
        -----
        This property is provided for backward compatibility. Use the
        load_defaults() classmethod for new code.
        """
        assert self.config_path is not None
        return self.config_path / self.DEFAULTS_FILE_NAME

    @classmethod
    def load_defaults(
        cls,
        config_path: Path | str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load default model parameters from defaults.json with optional overrides.

        Parameters
        ----------
        config_path : Path | str | None, optional
            Custom config directory path. If None, uses the class's default
            config location (CONFIG_DIR relative to module).
        overrides : dict[str, Any], optional
            Values to merge with loaded defaults. For list values, items are
            appended and deduplicated. For scalar values, they replace defaults.

        Returns
        -------
        dict[str, Any]
            Merged defaults dict. Returns empty dict if defaults.json doesn't exist.

        Raises
        ------
        json.JSONDecodeError
            If defaults.json contains invalid JSON.
        TypeError
            If defaults.json does not contain a dict.

        Examples
        --------
        Load defaults with no overrides:

        >>> defaults = ReEDSConfig.load_defaults()

        Load with scalar override:

        >>> defaults = ReEDSConfig.load_defaults(
        ...     overrides={"horizon_year": 2040}
        ... )

        Load with list override (merged):

        >>> defaults = ReEDSConfig.load_defaults(
        ...     overrides={"excluded_techs": ["solar", "wind"]}
        ... )

        Use custom config path:

        >>> defaults = ReEDSConfig.load_defaults(
        ...     config_path="/custom/config/path"
        ... )
        """
        config_path = cls._resolve_config_path(config_path)
        defaults_file = config_path / cls.DEFAULTS_FILE_NAME

        if not defaults_file.exists():
            logger.debug(f"Defaults file not found: {defaults_file}. Using provided overrides.")
            return overrides or {}

        try:
            with open(defaults_file, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse defaults JSON from {defaults_file}: {e}")
            raise

        if not isinstance(data, dict):
            raise TypeError(f"Defaults file must contain a dict, got {type(data).__name__}")

        if not overrides:
            return data

        return cls._merge_dicts(data, overrides)

    @classmethod
    def load_file_mapping(
        cls,
        config_path: Path | str | None = None,
        file_overrides: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Load file mapping from file_mapping.json with optional path overrides.

        The file_mapping.json should contain a list of dicts with keys:
        - "name": identifier for the file (e.g., "data_file", "xml_file")
        - "fpath": file path pattern or actual path
        - Other optional fields like "description", "optional", etc.

        Path overrides are applied by matching the "name" field and updating
        the "fpath" field.

        Parameters
        ----------
        config_path : Path | str | None, optional
            Custom config directory path. If None, uses the class's default
            config location (CONFIG_DIR relative to module).
        file_overrides : dict[str, str], optional
            File path overrides as {file_name: file_path}. Updates the "fpath"
            field for entries matching the name.

        Returns
        -------
        list[dict[str, Any]]
            File mapping list with overrides applied. Returns empty list if
            file_mapping.json doesn't exist.

        Raises
        ------
        json.JSONDecodeError
            If file_mapping.json contains invalid JSON.
        ValueError
            If file_mapping.json does not contain a list.

        Examples
        --------
        Load file mappings with no overrides:

        >>> mappings = PLEXOSConfig.load_file_mapping()

        Load with path overrides:

        >>> mappings = PLEXOSConfig.load_file_mapping(
        ...     file_overrides={"xml_file": "/path/to/model.xml"}
        ... )

        Use custom config path:

        >>> mappings = PLEXOSConfig.load_file_mapping(
        ...     config_path="/custom/config/path"
        ... )
        """
        config_path = cls._resolve_config_path(config_path)
        mapping_file = config_path / cls.FILE_MAPPING_NAME

        if not mapping_file.exists():
            logger.debug(f"File mapping file not found: {mapping_file}. Returning empty list.")
            return []

        try:
            with open(mapping_file, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse file mapping JSON from {mapping_file}: {e}")
            raise

        if not isinstance(data, list):
            raise ValueError(
                f"File mapping file must contain a list, got {type(data).__name__}. "
                f"Expected format: [{{'name': '...', 'fpath': '...', ...}}]"
            )

        if not file_overrides:
            return data

        # Apply overrides by matching on "name" field
        for item in data:
            if isinstance(item, dict) and "name" in item:
                name = item["name"]
                if name in file_overrides:
                    item["fpath"] = file_overrides[name]

        return data

    @classmethod
    def _resolve_config_path(cls, config_path: Path | str | None) -> Path:
        """Resolve config_path to a Path object.

        If config_path is None, uses the class's CONFIG_DIR location relative
        to the module where the class is defined.

        Parameters
        ----------
        config_path : Path | str | None
            Custom config path or None to use class default.

        Returns
        -------
        Path
            Resolved config path.
        """
        if config_path is not None:
            return Path(config_path)

        module_file = inspect.getfile(cls)
        return Path(module_file).parent / cls.CONFIG_DIR

    @staticmethod
    def _merge_dicts(
        base: dict[str, Any],
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge overrides dict into base dict.

        For list values: items are appended to base and deduplicated.
        For scalar values: override values replace base values.
        New keys from overrides are added to base.

        Parameters
        ----------
        base : dict[str, Any]
            Base dictionary to merge into.
        overrides : dict[str, Any]
            Override values to merge.

        Returns
        -------
        dict[str, Any]
            Merged dictionary (base is modified in-place and returned).
        """
        result = base.copy()

        for key, value in overrides.items():
            if key in result and isinstance(result[key], list) and isinstance(value, list):
                # Merge lists: append new items and deduplicate (preserving order)
                seen = set(result[key])
                for item in value:
                    if item not in seen:
                        result[key].append(item)
                        seen.add(item)
            else:
                # For scalars and new keys: override
                result[key] = value

        return result
