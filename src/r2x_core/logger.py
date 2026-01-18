"""Logging configuration for R2X Core using loguru.

This module provides a dual-format sink. When stderr is a TTY, logs are rendered
with a compact, colorized layout. Otherwise, logs are emitted as JSON Lines for
easy piping and structured ingestion.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any

LEVEL_NAMES = {
    "TRACE": "TRACE",
    "DEBUG": "DEBUG",
    "INFO": " INFO",
    "WARNING": " WARN",
    "ERROR": "ERROR",
    "CRITICAL": " CRIT",
}
LEVEL_COLORS = {
    "TRACE": "color(249)",  # light gray
    "DEBUG": "color(33)",  # blue
    "INFO": "color(37)",  # cyan
    "WARNING": "color(214)",  # orange
    "ERROR": "color(169)",  # pink/magenta
    "CRITICAL": "color(169) reverse",  # inverted pink
}

# Verbosity level constants
VERBOSITY_TRACE = 2
VERBOSITY_INFO = 1
DEFAULT_LOG_LEVEL = "WARNING"

_VERBOSITY_TO_LEVEL = {
    VERBOSITY_TRACE: "TRACE",
    VERBOSITY_INFO: "INFO",
}
JSON_LEVEL_NAMES = {
    "TRACE": "TRACE",
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARN",
    "ERROR": "ERROR",
    "CRITICAL": "CRIT",
}
DEFAULT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.{ms}"

_verbosity: int = 0
_console: Any | None = None


def _get_console() -> Any | None:
    """Get or create a Rich Console instance for TTY output.

    Returns None if Rich is not installed or if TTY is not available.
    Caches the console instance globally to avoid repeated imports.
    """
    global _console
    if _console is not None:
        return _console or None
    try:
        from rich.console import Console
    except ImportError:
        _console = False
        return None
    _console = Console(stderr=True, force_terminal=True)
    return _console


def _format_timestamp(record: dict[str, Any]) -> str:
    """Format a log record's timestamp using LOG_TIME_FORMAT env var or default.

    Substitutes milliseconds ({ms}) in the format string with zero-padded microseconds.
    """
    time_format = os.environ.get("LOG_TIME_FORMAT", DEFAULT_TIME_FORMAT)
    ms = f"{record['time'].microsecond // 1000:03d}"
    return record["time"].strftime(time_format.replace("{ms}", ms))


def _render_exception(record: dict[str, Any], console: Any | None) -> None:
    """Render exception traceback from log record to stderr.

    Prefers Rich-formatted tracebacks if console is available and Rich is installed.
    Falls back to standard Python traceback formatting.
    """
    exc = record["exception"]
    if not exc or not exc.type or not exc.value:
        return

    if console is not None and exc.traceback:
        try:
            from rich.traceback import Traceback
        except ImportError:
            console = None
        else:
            console.print(Traceback.from_exception(exc.type, exc.value, exc.traceback))
            return

    if exc.traceback:
        lines = traceback.format_exception(exc.type, exc.value, exc.traceback)
        print("".join(lines), file=sys.stderr)


def format_tty(record: dict[str, Any]) -> None:
    """Format log record for terminal output."""
    level = record["level"].name
    level_name = LEVEL_NAMES.get(level, f"{level:>5}")
    color = LEVEL_COLORS.get(level, "white")
    console = _get_console()

    extras = {key: value for key, value in record["extra"].items() if key != "name"}
    if console is not None:
        try:
            from rich.text import Text
        except ImportError:
            console = None
        else:
            text = Text()
            if _verbosity >= 2:
                text.append(_format_timestamp(record), style="dim")
                text.append(" ")
            text.append(level_name, style=f"{color} bold")
            text.append(" ")
            text.append(record["message"])
            if extras:
                pairs = "  ".join(f"{key}={value}" for key, value in extras.items())
                text.append(f"  {pairs}", style="dim")
            console.print(text)
            _render_exception(record, console)
            return

    parts = []
    if _verbosity >= 2:
        parts.append(_format_timestamp(record))
    parts.append(level_name)
    parts.append(record["message"])
    if extras:
        pairs = "  ".join(f"{key}={value}" for key, value in extras.items())
        parts.append(pairs)
    print(" ".join(parts), file=sys.stderr)
    _render_exception(record, None)


def format_json(record: dict[str, Any]) -> str:
    """Format log record as JSON Lines for piping."""
    level = record["level"].name
    obj: dict[str, Any] = {
        "ts": record["time"].strftime(DEFAULT_TIME_FORMAT),
        "level": JSON_LEVEL_NAMES.get(level, level),
        "msg": record["message"],
    }

    name = record["extra"].get("name") or record.get("name")
    if name:
        obj["logger"] = name

    if record.get("file"):
        obj["file"] = record["file"].path
        obj["line"] = record["line"]

    extras = {key: value for key, value in record["extra"].items() if key != "name"}
    if extras:
        obj.update(extras)

    exc = record["exception"]
    if exc and exc.type and exc.value:
        obj["error"] = {
            "type": exc.type.__name__,
            "message": str(exc.value),
        }
        if exc.traceback:
            obj["error"]["traceback"] = traceback.format_exception(exc.type, exc.value, exc.traceback)

    return json.dumps(obj)


def structured_sink(message: Any) -> None:
    """Format logs based on TTY detection."""
    record = message.record
    if sys.stderr.isatty():
        format_tty(record)
    else:
        print(format_json(record), file=sys.stderr)


def setup_logging(verbosity: int = 0) -> None:
    """Configure loguru with the dual-format sink.

    Verbosity levels:
        0: WARNING and above (default)
       -v: INFO and above, no timestamps
      -vv: TRACE and above, with timestamps
    """
    global _verbosity
    from loguru import logger

    _verbosity = verbosity

    logger.enable("r2x_core")

    level = _VERBOSITY_TO_LEVEL.get(verbosity, DEFAULT_LOG_LEVEL)

    logger.remove()
    logger.add(
        structured_sink,
        level=level,
        backtrace=True,
        diagnose=True,
    )


def get_logger(name: str) -> Any:
    """Get a logger for a specific component or plugin."""
    from loguru import logger

    return logger.bind(name=name)
