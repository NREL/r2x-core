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
...     defaults={"excluded_techs": ["coal", "oil"]}
... )

Load defaults from JSON:

>>> defaults = ReEDSConfig.load_defaults()
>>> config = ReEDSConfig(model_year=2030, weather_year=2012, defaults=defaults)

See Also
--------
r2x_core.parser.BaseParser : Uses this configuration class
r2x_core.exporter.BaseExporter : Uses this configuration class
"""

from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from pydantic import BaseModel, Field


class PluginConfig(BaseModel):
    """Base configuration class for plugin inputs and model parameters.

    Applications should inherit from this class to define model-specific
    configuration parameters for parsers, exporters, and system modifiers.
    This base class provides common fields that most plugins will need,
    while allowing full customization through inheritance.

    Parameters
    ----------
    defaults : dict, optional
        Default values for model-specific parameters. Can include device mappings,
        technology categorizations, filtering rules, etc. Default is empty dict.

    Attributes
    ----------
    defaults : dict
        Dictionary of default values and mappings.

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
    ...     defaults={"excluded_techs": ["coal", "oil"]}
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

    defaults: dict[str, Any] = Field(
        default_factory=dict, description="Default values and model-specific mappings"
    )

    # Standard file mapping filename - can be overridden in subclasses
    FILE_MAPPING_NAME: ClassVar[str] = "file_mapping.json"

    @classmethod
    def get_file_mapping_path(cls) -> Path:
        """Get the path to this plugin's file mapping JSON.

        This method uses importlib.resources to locate the plugin module,
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
        This method uses importlib.resources.files() which properly handles
        both installed packages and editable installs, making the resources
        discoverable in all installation scenarios.
        """
        from importlib.resources import files

        # Get the package where the config class is defined
        module = cls.__module__
        package_name = module.rsplit(".", 1)[0]  # Remove the module name, keep package

        # Use importlib.resources to get the package path
        package_files = files(package_name)
        config_path = package_files / "config" / cls.FILE_MAPPING_NAME

        # Convert Traversable to Path
        try:
            # Try to get as Path - works for file system paths
            return Path(str(config_path))
        except Exception:
            # Fallback for edge cases
            import inspect

            module_file = inspect.getfile(cls)
            module_path = Path(module_file).parent
            return module_path / "config" / cls.FILE_MAPPING_NAME

    @classmethod
    def load_defaults(cls, defaults_file: Path | str | None = None) -> dict[str, Any]:
        """Load default constants from JSON file.

        Provides a standardized way to load model-specific constants, mappings,
        and default values from JSON files. If no file path is provided, automatically
        looks for 'constants.json' in the config directory next to the module.

        Parameters
        ----------
        defaults_file : Path, str, or None, optional
            Path to defaults JSON file. If None, looks for 'constants.json'
            in a 'config' subdirectory relative to the calling module.

        Returns
        -------
        dict[str, Any]
            Dictionary of default constants to use in the `defaults` field.
            Returns empty dict if file doesn't exist.

        Examples
        --------
        Load defaults automatically:

        >>> from r2x_reeds.config import ReEDSConfig
        >>> defaults = ReEDSConfig.load_defaults()
        >>> config = ReEDSConfig(
        ...     solve_years=2030,
        ...     weather_years=2012,
        ...     defaults=defaults
        ... )

        Load from custom path:

        >>> defaults = ReEDSConfig.load_defaults("/path/to/custom_defaults.json")

        See Also
        --------
        PluginConfig : Base configuration class
        get_file_mapping_path : Related file discovery method
        """
        import json
        from importlib.resources import files

        if defaults_file is None:
            # Get the package where the config class is defined
            module = cls.__module__
            package_name = module.rsplit(".", 1)[0]

            # Use importlib.resources to get the package path
            package_files = files(package_name)
            config_path = package_files / "config" / "constants.json"

            # Convert Traversable to Path
            try:
                defaults_file = Path(str(config_path))
            except Exception:
                # Fallback for edge cases
                import inspect

                config_module_file = inspect.getfile(cls)
                config_dir = Path(config_module_file).parent
                defaults_file = config_dir / "config" / "constants.json"
        else:
            defaults_file = Path(defaults_file)

        if not defaults_file.exists():
            logger.debug(f"Defaults file not found: {defaults_file}")
            return {}

        try:
            with open(defaults_file) as f:
                data: dict[str, Any] = json.load(f)
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse defaults JSON from {defaults_file}: {e}")
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
