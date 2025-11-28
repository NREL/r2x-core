"""Enums for r2x-core."""

from enum import Enum


class PluginConfigAsset(str, Enum):
    """Enum describing configuration assets."""

    FILE_MAPPING = "file_mapping.json"
    DEFAULTS = "defaults.json"
    TRANSLATION_RULES = "translation_rules.json"
    PARSER_RULES = "parser_rules.json"
    EXPORTER_RULES = "exporter_rules.json"


class PluginKind(str, Enum):
    """High-level category for a plugin."""

    PARSER = "parser"
    EXPORTER = "exporter"
    MODIFIER = "modifier"
    UPGRADER = "upgrader"
    UTILITY = "utility"


class ImplementationType(str, Enum):
    """Whether the plugin entry point is a class or a simple function."""

    CLASS = "class"
    FUNCTION = "function"


class ArgumentSource(str, Enum):
    """Source for an invocation argument."""

    SYSTEM = "system"
    STORE = "store"
    STORE_MANIFEST = "store_manifest"
    CONFIG = "config"
    CONFIG_PATH = "config_path"
    PATH = "path"
    STDIN = "stdin"
    CONTEXT = "context"
    LITERAL = "literal"
    CUSTOM = "custom"


class IOSlotKind(str, Enum):
    """Canonical inputs/outputs handled by plugins."""

    SYSTEM = "system"
    STORE_FOLDER = "store_folder"
    STORE_MANIFEST = "store_manifest"
    STORE_INLINE = "store_inline"
    CONFIG_FILE = "config_file"
    CONFIG_INLINE = "config_inline"
    FILE = "file"
    FOLDER = "folder"
    STDIN = "stdin"
    STDOUT = "stdout"
    ARTIFACT = "artifact"
    VOID = "void"


class StoreMode(str, Enum):
    """How a plugin expects its :class:`~r2x_core.store.DataStore`."""

    FOLDER = "folder"
    MANIFEST = "manifest"
    INLINE = "inline"
