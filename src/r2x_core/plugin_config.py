"""Base configuration class for plugins.

This module provides the foundational configuration class that plugin implementations
should inherit from to define model-specific parameters. This applies to parsers,
exporters, and system modifiers.

Classes
-------
PluginConfig
    Base configuration class with support for defaults loading.

Examples
--------
Create a model-specific configuration:

>>> from r2x_core.plugin_config import PluginConfig
>>> from pydantic import field_validator
>>>
>>> class ReEDSConfig(PluginConfig):
...     model_year: int
...     weather_year: int
...     scenario: str = "base"
...
...     @field_validator("model_year")
...     @classmethod
...     def validate_year(cls, v):
...         if v < 2020 or v > 2050:
...             raise ValueError("Year must be between 2020 and 2050")
...         return v
>>>
>>> config = ReEDSConfig(
...     model_year=2030,
...     weather_year=2012,
...     scenario="high_re"
... )

Load constants from JSON:

>>> constants = ReEDSConfig.load_defaults()
>>> # Use constants in your parser/exporter logic

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
    """Base configuration class for plugin inputs and model parameters.

    This is the foundation for model-specific configuration in parsers, exporters,
    and system modifiers. Subclasses should define model-specific parameters and
    can override the config directory path.

    Attributes
    ----------
    config_path : Path | None
        Path to the configuration directory. If None, defaults to the 'config'
        subdirectory relative to the subclass module location.

    Methods
    -------
    load_file_mapping(fpath=None)
        Load file mapping configuration from JSON.
    load_defaults(defaults_file=None)
        Load default values from JSON.

    See Also
    --------
    :class:`BaseParser` : Uses PluginConfig for input parameters
    :class:`BaseExporter` : Uses PluginConfig for output configuration

    Examples
    --------
    Create a model-specific configuration:

    >>> from r2x_core.plugin_config import PluginConfig
    >>> from pydantic import field_validator
    >>>
    >>> class ReEDSConfig(PluginConfig):
    ...     model_year: int
    ...     weather_year: int
    ...     scenario: str = "base"
    ...
    ...     @field_validator("model_year")
    ...     @classmethod
    ...     def validate_year(cls, v):
    ...         if v < 2020 or v > 2050:
    ...             raise ValueError("Year must be between 2020 and 2050")
    ...         return v
    >>>
    >>> config = ReEDSConfig(
    ...     model_year=2030,
    ...     weather_year=2012,
    ...     scenario="high_re"
    ... )

    Load defaults from JSON:

    >>> defaults = config.load_defaults()
    >>> print(defaults.get("model_year"))

    Notes
    -----
    Config directory structure expected: config/
        - file_mapping.json: Maps input file patterns to processing functions
        - defaults.json: Default model parameters and constants
    """

    CONFIG_DIR: ClassVar[str] = "config"
    FILE_MAPPING_NAME: ClassVar[str] = "file_mapping.json"
    DEFAULTS_FILE_NAME: ClassVar[str] = "defaults.json"

    config_path: Path | None = Field(default=None)

    @model_validator(mode="after")
    def resolve_config_path_after(self) -> "PluginConfig":
        """Resolve config path after validation."""
        if self.config_path is None:
            module_file = inspect.getfile(self.__class__)
            self.config_path = Path(module_file).parent / self.CONFIG_DIR
        # At this point, config_path is guaranteed to be Path (not None)
        assert isinstance(self.config_path, Path)
        return self

    @property
    def file_mapping_path(self) -> Path:
        """Get path to file mapping configuration file.

        Returns
        -------
        Path
            Path to file_mapping.json in config directory
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
        """
        assert self.config_path is not None
        return self.config_path / self.DEFAULTS_FILE_NAME

    def load_file_mapping(self, fpath: Path | str | None = None) -> list[dict[str, Any]]:
        """Load file mapping configuration from JSON.

        Parameters
        ----------
        fpath : Path | str | None, optional
            Path to file mapping JSON file. If None, uses default path.

        Returns
        -------
        dict[str, Any]
            File mapping configuration as dictionary

        Raises
        ------
        FileNotFoundError
            If the file mapping file does not exist
        json.JSONDecodeError
            If the JSON is malformed
        """
        fpath = Path(fpath) if fpath else self.file_mapping_path

        if not fpath.exists():
            raise FileNotFoundError(f"File mapping not found: {fpath}")
        try:
            with open(fpath, encoding="utf-8") as f:
                data: list[dict[str, Any]] = json.load(f)
                assert isinstance(data, list), "File mapping is not a JSON Array."
                return data
        except json.JSONDecodeError as e:
            logger.error("Failed to parse file mapping JSON from %s: %s", fpath, e)
            raise

    def load_defaults(self, defaults_file: Path | str | None = None) -> dict[str, Any]:
        """Load default model parameters and constants from JSON.

        Parameters
        ----------
        defaults_file : Path | str | None, optional
            Path to defaults JSON file. If None, uses default path.

        Returns
        -------
        dict[str, Any]
            Default parameters and constants as dictionary

        Raises
        ------
        FileNotFoundError
            If the defaults file does not exist
        json.JSONDecodeError
            If the JSON is malformed
        """
        fpath = Path(defaults_file) if defaults_file else self.defaults_path
        if not fpath.exists():
            raise FileNotFoundError(f"Defaults file not found: {fpath}")
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise TypeError(f"Expected dict, got {type(data).__name__}")
                return data
        except json.JSONDecodeError as e:
            logger.error("Failed to parse defaults JSON from %s: %s", fpath, e)
            raise
