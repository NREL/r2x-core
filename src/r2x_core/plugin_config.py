"""Base configuration class for plugins."""

import inspect
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from .utils.overrides import override_dictionary


class PluginConfigAsset(str, Enum):
    """Enum describing configuration assets."""

    FILE_MAPPING = "file_mapping.json"
    DEFAULTS = "defaults.json"
    TRANSLATION_RULES = "translation_rules.json"
    PARSER_RULES = "parser_rules.json"
    EXPORTER_RULES = "exporter_rules.json"


class PluginConfig(BaseModel):
    """Pure Pydantic base configuration class for plugins."""

    CONFIG_DIR: ClassVar[str] = "config"

    models: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "Module path(s) for component classes, e.g. 'r2x_sienna.models'. "
            "If omitted, rules will use an empty module list."
        ),
    )

    config_path_override: Path | None = Field(
        default=None,
        description="Override for the configuration path. This is used if you want to point to a different place than the `CONFIG_DIR`",
    )

    @field_validator("models", mode="before")
    @classmethod
    def _coerce_models(cls, value: Any | None) -> tuple[str, ...]:
        """Allow models to be configured via str, iterable, or omitted entirely."""
        if value is None:
            return ()
        if isinstance(value, str):
            return (value,)
        if isinstance(value, list | tuple | set):
            return tuple(value)
        raise TypeError("models must be a string or iterable of strings")

    @property
    def config_path(self) -> Path:
        """Return package config path."""
        config_path = self.config_path_override or self._package_config_path()

        if not config_path.exists():
            msg = "Config path={} doe not exist on the Package."
            logger.warning(msg, config_path)
        return config_path

    @classmethod
    def _package_config_path(cls) -> Path:
        """Compute the config directory alongside the defining package."""
        module_file = inspect.getfile(cls)
        module_dir = Path(module_file).parent
        if module_dir.name == cls.CONFIG_DIR:
            return module_dir
        return module_dir / cls.CONFIG_DIR

    @property
    def fmap_path(self) -> Path:
        """Get path to file mapping configuration file.

        Returns
        -------
        Path
            Path to file_mapping.json in config directory
        """
        return self.config_path / PluginConfigAsset.FILE_MAPPING

    @property
    def defaults_path(self) -> Path:
        """Get path to defaults configuration file.

        Returns
        -------
        Path
            Path to defaults.json in config directory
        """
        return self.config_path / PluginConfigAsset.DEFAULTS

    @property
    def exporter_rules_path(self) -> Path:
        """Get path to exporter_rules.json in the config directory."""
        return self.config_path / PluginConfigAsset.EXPORTER_RULES

    @property
    def parser_rules_path(self) -> Path:
        """Get path to parser_rules.json in the config directory."""
        return self.config_path / PluginConfigAsset.PARSER_RULES

    @property
    def translation_rules_path(self) -> Path:
        """Get path to translation_rules.json in the config directory."""
        return self.config_path / PluginConfigAsset.TRANSLATION_RULES

    @classmethod
    def load_config(
        cls,
        *,
        config_path: Path | str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load plugin configuration assets with optional overrides.

        Parameters
        ----------
        config_path : Path | str | None, optional
            Optional override for the config directory to load assets from.
        overrides : dict[str, Any], optional
            Values to merge with loaded assets. For list values, items are
            appended and deduplicated. For scalar values, they replace defaults.

        Returns
        -------
        dict[str, Any]
            Merged assets keyed by asset stem (defaults, file_mapping, etc.).
        """
        import orjson

        resolved_config_path = Path(config_path) if config_path is not None else cls._package_config_path()
        asset_data: dict[str, Any] = {}
        for asset in PluginConfigAsset:
            asset_path = resolved_config_path / asset.value
            if not asset_path.exists():
                msg = f"{asset_path=} not found on Package. Check contents of config_path"
                raise FileNotFoundError(msg)
            with open(asset_path, "rb") as f_in:
                data = orjson.loads(f_in.read())
            asset_data[asset_path.stem] = data

        if not overrides:
            return asset_data

        return override_dictionary(base=asset_data, overrides=overrides)
