"""CLI execution module for r2x-core plugins."""

import argparse
import inspect
import json
import sys
from typing import Any, NoReturn

from infrasys import System
from loguru import logger
from pydantic import ValidationError

from .exceptions import CLIError
from .plugins import PluginManager
from .store import DataStore
from .utils.validation import filter_valid_kwargs


def print_stacktrace(exception: Exception) -> None:
    """Print exception traceback for parent applications."""
    if not exception.__traceback__:
        return
    print("Traceback:", file=sys.stderr)
    for frame in inspect.getinnerframes(exception.__traceback__):
        print(f'  File "{frame.filename}", line {frame.lineno}, in {frame.function}', file=sys.stderr)
        if frame.code_context:
            print(f"    {frame.code_context[0].strip()}", file=sys.stderr)


def _handle_error(error: Exception, context: str) -> NoReturn:
    """Handle and print error for parent applications."""
    print_stacktrace(error)
    raise CLIError(context) from error


def execute_parser(plugin_name: str, plugin_config: dict[str, Any]) -> Any:
    """Execute parser and return serialized system."""
    logger.info(f"Executing parser '{plugin_name}'")
    pm = PluginManager()

    parser_class = pm.load_parser(plugin_name)
    if not parser_class:
        raise CLIError(f"Parser '{plugin_name}' not found")

    config_class = pm.load_config_class(plugin_name)
    if not config_class:
        raise CLIError(f"Config class for '{plugin_name}' not found")

    try:
        config = config_class.model_validate(filter_valid_kwargs(config_class, plugin_config))
    except ValidationError as e:
        _handle_error(e, f"Invalid parser config: {e}")

    folder: Any = plugin_config.get("folder_path")
    if not folder:
        raise CLIError("Missing 'folder_path' in config")

    try:
        upgrader_class = pm.get_upgrader(config_class)
        upgrader = upgrader_class(folder) if upgrader_class else None
        store = DataStore.from_plugin_config(config, folder_path=folder, upgrader=upgrader)
        parser = parser_class(config, data_store=store, **filter_valid_kwargs(parser_class, plugin_config))
        system = parser.build_system()
        system.to_json()
        return None
    except Exception as e:
        _handle_error(e, f"Parser failed: {e}")


def execute_sysmod(plugin_name: str, config: dict[str, Any], stdin_data: dict[str, Any] | None = None) -> Any:
    """Execute modifier and return modified system."""
    logger.info(f"Executing modifier '{plugin_name}'")

    if not stdin_data or stdin_data.get("type") != "system":
        raise CLIError("Modifier requires system data in stdin")

    pm = PluginManager()
    modifier = pm.registered_modifiers.get(plugin_name)
    if not modifier:
        raise CLIError(f"Modifier '{plugin_name}' not found")

    try:
        system = System.from_json(stdin_data["data"])
    except Exception as e:
        _handle_error(e, f"Failed to deserialize system: {e}")

    model = stdin_data.get("metadata", {}).get("plugin", "unknown")
    cfg_class = pm.load_config_class(model) if model != "unknown" else None

    plugin_cfg = None
    parser = None
    if cfg_class:
        try:
            plugin_cfg = cfg_class.model_validate(filter_valid_kwargs(cfg_class, config))
            parser_class = pm.load_parser(model)
            if parser_class:
                parser = parser_class(plugin_cfg, data_store=None, name="temp")
        except Exception as e:
            logger.debug(f"Could not load model config/parser: {e}")

    try:
        sig = inspect.signature(modifier)
        params = list(sig.parameters.keys())
        if "config" in params and "parser" in params and plugin_cfg and parser:
            system = modifier(plugin_cfg, system, parser, **config)  # type: ignore[call-arg]
        elif "config" in params and plugin_cfg:
            system = modifier(plugin_cfg, system, **config)  # type: ignore[call-arg]
        elif "system" in params:
            system = modifier(system, **config)
        else:
            system = modifier(**config)
    except TypeError:
        try:
            system = modifier(system)
        except Exception as e:
            _handle_error(e, f"Modifier failed: {e}")
    except Exception as e:
        _handle_error(e, f"Modifier failed: {e}")
        return None

    try:
        system.to_json()
        return None
    except Exception as e:
        _handle_error(e, f"Failed to serialize system: {e}")


def execute_exporter(
    plugin_name: str, config: dict[str, Any], stdin_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Execute exporter and return export result."""
    logger.info(f"Executing exporter '{plugin_name}'")

    if not stdin_data or stdin_data.get("type") != "system":
        raise CLIError("Exporter requires system data in stdin")

    pm = PluginManager()
    exp_class = pm.load_exporter(plugin_name)
    if not exp_class:
        raise CLIError(f"Exporter '{plugin_name}' not found")

    try:
        system = System.from_json(stdin_data["data"])
    except Exception as e:
        _handle_error(e, f"Failed to deserialize system: {e}")

    cfg_class = pm.load_config_class(plugin_name)
    try:
        if cfg_class:
            exp_cfg = cfg_class.model_validate(filter_valid_kwargs(cfg_class, config))
            exporter = exp_class(exp_cfg)
        else:
            exporter = exp_class(**config)
    except Exception as e:
        _handle_error(e, f"Failed to instantiate exporter: {e}")

    try:
        output_path = exporter.export(system)
        return {"type": "export", "output_path": str(output_path), "metadata": {"exporter": plugin_name}}
    except Exception as e:
        _handle_error(e, f"Export failed: {e}")


def list_plugins() -> dict[str, Any]:
    """List all available plugins."""
    pm = PluginManager()
    parsers = [
        {"name": n, "type": "parser", "class": p.__name__ if hasattr(p, "__name__") else str(p)}
        for n, p in pm.registered_parsers.items()
    ]
    exporters = [
        {"name": n, "type": "exporter", "class": p.__name__ if hasattr(p, "__name__") else str(p)}
        for n, p in pm.registered_exporters.items()
    ]
    modifiers = [
        {"name": n, "type": "modifier", "callable": f.__name__ if hasattr(f, "__name__") else str(f)}
        for n, f in pm.registered_modifiers.items()
    ]
    filters = [
        {"name": n, "type": "filter", "callable": f.__name__ if hasattr(f, "__name__") else str(f)}
        for n, f in pm.registered_filters.items()
    ]

    return {
        "parsers": parsers,
        "exporters": exporters,
        "modifiers": modifiers,
        "filters": filters,
        "total": {
            "parsers": len(parsers),
            "exporters": len(exporters),
            "modifiers": len(modifiers),
            "filters": len(filters),
        },
    }


def plugin_info(plugin_type: str, plugin_name: str) -> dict[str, Any]:
    """Get detailed information about a plugin."""
    pm = PluginManager()

    plugin: Any = None
    if plugin_type == "parser":
        plugin = pm.load_parser(plugin_name)
    elif plugin_type == "exporter":
        plugin = pm.load_exporter(plugin_name)
    elif plugin_type in ("modifier", "sysmod"):
        plugin = pm.registered_modifiers.get(plugin_name)
    elif plugin_type == "filter":
        plugin = pm.registered_filters.get(plugin_name)
    else:
        raise CLIError(f"Unknown plugin type: {plugin_type}")

    if not plugin:
        raise CLIError(f"{plugin_type.title()} '{plugin_name}' not found")

    info: dict[str, Any] = {
        "name": plugin_name,
        "type": plugin_type,
        "class": plugin.__name__ if hasattr(plugin, "__name__") else str(plugin),
        "module": plugin.__module__ if hasattr(plugin, "__module__") else "unknown",
        "doc": inspect.getdoc(plugin) or "No documentation",
    }

    cfg_class = pm.load_config_class(plugin_name)
    if cfg_class:
        try:
            info["config_schema"] = cfg_class.model_json_schema()
        except Exception as e:
            logger.debug(f"Could not get config schema: {e}")

    if plugin_type in ("modifier", "sysmod", "filter"):
        try:
            sig = inspect.signature(plugin)
            info["signature"] = str(sig)
            info["parameters"] = list(sig.parameters.keys())
        except Exception as e:
            logger.debug(f"Could not get signature: {e}")

    return info


def main() -> None:
    """Run the R2X Core CLI."""
    parser = argparse.ArgumentParser(description="R2X Core CLI")
    subs = parser.add_subparsers(dest="command")

    exe = subs.add_parser("execute")
    exe.add_argument("plugin_type", choices=["parser", "sysmod", "exporter"])
    exe.add_argument("plugin_name")
    exe.add_argument("--config", default="{}")
    exe.add_argument("--stdin")

    subs.add_parser("list-plugins")
    info = subs.add_parser("plugin-info")
    info.add_argument("plugin_type", choices=["parser", "sysmod", "modifier", "exporter", "filter"])
    info.add_argument("plugin_name")

    args = parser.parse_args()

    try:
        if args.command == "execute":
            config = json.loads(args.config)
            stdin_data = json.loads(args.stdin) if args.stdin else None

            if args.plugin_type == "parser":
                result = execute_parser(args.plugin_name, config)
            elif args.plugin_type == "sysmod":
                result = execute_sysmod(args.plugin_name, config, stdin_data)
            else:
                result = execute_exporter(args.plugin_name, config, stdin_data)

            print(json.dumps(result, indent=2))

        elif args.command == "list-plugins":
            print(json.dumps(list_plugins(), indent=2))

        elif args.command == "plugin-info":
            print(json.dumps(plugin_info(args.plugin_type, args.plugin_name), indent=2))

        else:
            parser.print_help()
            sys.exit(1)

    except CLIError as e:
        logger.error(f"CLI error: {e}")
        error = {"error": str(e), "error_type": "CLIError"}
        if hasattr(args, "plugin_type"):
            error.update({"plugin_type": args.plugin_type, "plugin_name": args.plugin_name})
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print_stacktrace(e)
        print(json.dumps({"error": str(e), "error_type": type(e).__name__}), file=sys.stderr)
        sys.exit(1)
