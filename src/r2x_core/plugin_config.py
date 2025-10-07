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
from typing import Any

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
        r2x_core.parser.BaseParser.get_file_mapping_path : Related file discovery method
        """
        import inspect
        import json

        if defaults_file is None:
            # Get the module where the config class is defined
            config_module_file = inspect.getfile(cls)
            config_dir = Path(config_module_file).parent
            defaults_file = config_dir / "config" / "constants.json"

        defaults_path = Path(defaults_file)

        if not defaults_path.exists():
            logger.debug(f"Defaults file not found: {defaults_path}")
            return {}

        try:
            with open(defaults_path) as f:
                data: dict[str, Any] = json.load(f)
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse defaults JSON from {defaults_path}: {e}")
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
