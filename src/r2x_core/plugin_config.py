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

from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from pydantic import BaseModel


class PluginConfig(BaseModel):
    """Base configuration class for plugin inputs and model parameters.

    Applications should inherit from this class to define model-specific
    configuration parameters for parsers, exporters, and system modifiers.
    Subclasses define their own fields for model-specific parameters.

    Examples
    --------
    Create a model-specific configuration:

    >>> class ReEDSConfig(PluginConfig):
    ...     '''Configuration for ReEDS parser.'''
    ...     model_year: int
    ...     weather_year: int
    ...     scenario: str = "base"
    ...
    >>> config = ReEDSConfig(
    ...     model_year=2030,
    ...     weather_year=2012,
    ...     scenario="high_re"
    ... )

    With validation:

    >>> from pydantic import field_validator
    >>>
    >>> class ValidatedConfig(PluginConfig):
    ...     model_year: int
    ...
    ...     @field_validator("model_year")
    ...     @classmethod
    ...     def validate_year(cls, v):
    ...         if v < 2020 or v > 2050:
    ...             raise ValueError("Year must be between 2020 and 2050")
    ...         return v

    See Also
    --------
    r2x_core.parser.BaseParser : Uses this configuration class
    r2x_core.exporter.BaseExporter : Uses this configuration class
    pydantic.BaseModel : Parent class providing validation

    Notes
    -----
    The PluginConfig uses Pydantic for:
    - Automatic type checking and validation
    - JSON serialization/deserialization
    - Field validation and transformation
    - Default value management

    Subclasses can add:
    - Model-specific years (solve_year, weather_year, horizon_year, etc.)
    - Scenario identifiers
    - Feature flags
    - File path overrides
    - Custom validation logic
    """

    CONFIG_DIR: ClassVar[str] = "config"
    FILE_MAPPING_NAME: ClassVar[str] = "file_mapping.json"
    DEFAULTS_FILE_NAME: ClassVar[str] = "defaults.json"

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the path to this plugin's file mapping JSON.

        This method uses inspect.getfile() to locate the plugin module file,
        then constructs the path to the file mapping JSON in the config directory.
        By convention, plugins should store their file_mapping.json in a config/
        subdirectory next to the config module.

        The filename can be customized by overriding the FILE_MAPPING_NAME class variable.

        Returns
        -------
        Path
            Absolute path to the file_mapping.json file. Note that this path may
            not exist if the plugin hasn't created the file yet.

        Examples
        --------
        Get file mapping path for a config:

        >>> from r2x_reeds.config import ReEDSConfig
        >>> mapping_path = ReEDSConfig.get_config_path()
        >>> print(mapping_path)
        /path/to/r2x_reeds/config/file_mapping.json

        Override the filename in a custom config:

        >>> class CustomConfig(PluginConfig):
        ...     FILE_MAPPING_NAME = "custom_mapping.json"
        ...
        >>> path = CustomConfig.get_config_path()
        >>> print(path.name)
        custom_mapping.json


        See Also
        --------
        load_defaults : Similar pattern for loading constants
        get_file_mapping_path: Get file mapping path
        DataStore.from_plugin_config : Direct DataStore creation from config

        Notes
        -----
        This method uses inspect.getfile() to locate the module file, then
        navigates to the config directory. This works for both installed
        packages and editable installs.
        """
        import inspect

        # Get the file where the config class is defined
        module_file = inspect.getfile(cls)
        module_path = Path(module_file).parent
        return module_path / cls.CONFIG_DIR

    @classmethod
    def get_file_mapping_path(cls) -> Path:
        """Get the path to this plugin's file mapping JSON.

        This method uses inspect.getfile() to locate the plugin module file,
        then constructs the path to the file mapping JSON in the config directory.
        By convention, plugins should store their file_mapping.json in a config/
        subdirectory next to the config module.

        The filename can be customized by overriding the FILE_MAPPING_NAME class variable.

        Returns
        -------
        Path
            Absolute path to the file_mapping.json file. Note that this path may
            not exist if the plugin hasn't created the file yet.

        Examples
        --------
        Get file mapping path for a config:

        >>> from r2x_reeds.config import ReEDSConfig
        >>> mapping_path = ReEDSConfig.get_file_mapping_path()
        >>> print(mapping_path)
        /path/to/r2x_reeds/config/file_mapping.json

        Override the filename in a custom config:

        >>> class CustomConfig(PluginConfig):
        ...     FILE_MAPPING_NAME = "custom_mapping.json"
        ...
        >>> path = CustomConfig.get_file_mapping_path()
        >>> print(path.name)
        custom_mapping.json

        Use with DataStore:

        >>> from r2x_core import DataStore
        >>> mapping_path = MyModelConfig.get_file_mapping_path()
        >>> store = DataStore.from_json(mapping_path, folder="/data/mymodel")

        See Also
        --------
        load_defaults : Similar pattern for loading constants
        DataStore.from_plugin_config : Direct DataStore creation from config

        Notes
        -----
        This method uses inspect.getfile() to locate the module file, then
        navigates to the config directory. This works for both installed
        packages and editable installs.
        """
        import inspect

        # Get the file where the config class is defined
        module_file = inspect.getfile(cls)
        module_path = Path(module_file).parent
        return module_path / cls.CONFIG_DIR / cls.FILE_MAPPING_NAME

    @classmethod
    def load_defaults(cls, defaults_file: Path | str | None = None) -> dict[str, Any]:
        """Load default constants from JSON file.

        Provides a standardized way to load model-specific constants, mappings,
        and default values from JSON files. If no file path is provided, automatically
        looks for the file specified by DEFAULTS_FILE_NAME in the config directory.

        Parameters
        ----------
        defaults_file : Path, str, or None, optional
            Path to defaults JSON file. If None, looks for the file specified
            by DEFAULTS_FILE_NAME (default: 'defaults.json') in the CONFIG_DIR
            subdirectory relative to the config module.

        Returns
        -------
        dict[str, Any]
            Dictionary of default constants to use in your parser/exporter logic.
            Returns empty dict if file doesn't exist.

        Examples
        --------
        Load defaults automatically:

        >>> from r2x_reeds.config import ReEDSConfig
        >>> defaults = ReEDSConfig.load_defaults()
        >>> config = ReEDSConfig(
        ...     solve_years=2030,
        ...     weather_years=2012,
        ... )
        >>> # Use defaults dict in your parser/exporter logic
        >>> excluded_techs = defaults.get("excluded_techs", [])

        Load from custom path:

        >>> defaults = ReEDSConfig.load_defaults("/path/to/custom_defaults.json")

        See Also
        --------
        PluginConfig : Base configuration class
        get_file_mapping_path : Related file discovery method
        """
        import inspect
        import json

        if defaults_file is None:
            # Get the file where the config class is defined
            module_file = inspect.getfile(cls)
            module_path = Path(module_file).parent
            defaults_file = module_path / cls.CONFIG_DIR / cls.DEFAULTS_FILE_NAME
        else:
            defaults_file = Path(defaults_file)

        if not defaults_file.exists():
            logger.debug("Defaults file not found: {}", defaults_file)
            return {}

        try:
            with open(defaults_file) as f:
                data: dict[str, Any] = json.load(f)
                return data
        except json.JSONDecodeError as e:
            logger.error("Failed to parse defaults JSON from {}: {}", defaults_file, e)
            return {}

    @classmethod
    def get_cli_schema(cls) -> dict[str, Any]:
        """Get JSON schema for CLI argument generation.

        This method generates a CLI-friendly schema from the configuration class,
        adding metadata useful for building command-line interfaces. It's designed
        to help tools like r2x-cli dynamically generate argument parsers from
        configuration classes.

        Returns
        -------
        dict[str, Any]
            A JSON schema dictionary enhanced with CLI metadata. Each property
            includes:
            - cli_flag: The command-line flag (e.g., "--model-year")
            - required: Whether the argument is required
            - All standard Pydantic schema fields (type, description, default, etc.)

        Examples
        --------
        Generate CLI schema for a configuration class:

        >>> from r2x_core.plugin_config import PluginConfig
        >>>
        >>> class MyConfig(PluginConfig):
        ...     '''My model configuration.'''
        ...     model_year: int
        ...     scenario: str = "base"
        ...
        >>> schema = MyConfig.get_cli_schema()
        >>> print(schema["properties"]["model_year"]["cli_flag"])
        --model-year
        >>> print(schema["properties"]["model_year"]["required"])
        True
        >>> print(schema["properties"]["scenario"]["cli_flag"])
        --scenario
        >>> print(schema["properties"]["scenario"]["required"])
        False

        Use in CLI generation:

        >>> import argparse
        >>> parser = argparse.ArgumentParser()
        >>> schema = MyConfig.get_cli_schema()
        >>> for field_name, field_info in schema["properties"].items():
        ...     flag = field_info["cli_flag"]
        ...     required = field_info["required"]
        ...     help_text = field_info.get("description", "")
        ...     parser.add_argument(flag, required=required, help=help_text)

        See Also
        --------
        load_defaults : Load default constants from JSON file
        r2x_core.parser.BaseParser.get_file_mapping_path : Get file mapping path
        pydantic.BaseModel.model_json_schema : Underlying schema generation

        Notes
        -----
        The CLI flag naming convention converts underscores to hyphens:
        - model_year -> --model-year
        - weather_year -> --weather-year
        - solve_year -> --solve-year

        This follows common CLI conventions (e.g., argparse, click).

        The schema includes all Pydantic field information, so CLI tools can:
        - Determine field types for proper parsing
        - Extract descriptions for help text
        - Identify default values
        - Validate constraints
        """
        base_schema = cls.model_json_schema()

        cli_schema: dict[str, Any] = {
            "title": base_schema.get("title", cls.__name__),
            "description": base_schema.get("description", ""),
            "properties": {},
            "required": base_schema.get("required", []),
        }

        for field_name, field_info in base_schema.get("properties", {}).items():
            cli_field = field_info.copy()
            cli_field["cli_flag"] = f"--{field_name.replace('_', '-')}"
            cli_field["required"] = field_name in cli_schema["required"]
            cli_schema["properties"][field_name] = cli_field

        return cli_schema

    @classmethod
    def from_dict(cls, data: dict[str, Any], **kwargs: Any) -> "PluginConfig":
        """Create configuration instance from dictionary.

        This method is particularly useful when using upgrade_data(),
        which returns an upgraded configuration dictionary. It provides a simple
        way to instantiate the config from that dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Configuration dictionary.
        **kwargs : Any
            Additional keyword arguments to override or add to the config.

        Returns
        -------
        PluginConfig
            Configuration instance.

        Examples
        --------
        Use with upgrade_data:

        >>> from r2x_core import upgrade_data
        >>> config_dict, upgraded_folder = upgrade_data(
        ...     config_file="config.json",
        ...     data_folder="/data/old",
        ...     upgrader="my_plugin"
        ... )
        >>> config = MyPluginConfig.from_dict(config_dict)
        >>> # Now use config with parser

        Override values from dict:

        >>> config = MyPluginConfig.from_dict(
        ...     config_dict,
        ...     model_year=2025  # Override the year from dict
        ... )

        See Also
        --------
        upgrade_data : Phase 1 upgrades returning config dict
        load_defaults : Load default constants
        """
        # Merge data with kwargs (kwargs take precedence)
        merged_data = {**data, **kwargs}
        return cls(**merged_data)
