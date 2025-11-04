# type: ignore
"""Logging configuration for R2X Core using loguru.

This module provides unified logging setup using loguru, supporting multiple
output destinations (console, file) with configurable formats. The logging
system is accessible via loguru's global logger instance.

Key features:
- Log level control (WARNING, INFO, DEBUG, TRACE)
- Optional file logging with append mode
- Colored console output
- Module-specific filtering
- Tracing mode with timestamps and line numbers
- Custom short-form log level names (WARN, INFO, DEBUG, FAIL, STEP, OK)

See Also
--------
loguru.logger : Global logger instance for use throughout the application.
"""

from typing import Any, Literal


def setup_logging(
    level: Literal["WARNING", "INFO", "DEBUG", "TRACE"] = "INFO",
    module: str | None = None,
    tracing: bool = False,
    log_file: str | None = None,
    fmt: str | None = None,
    enable_console_log: bool = True,
    **kwargs,
) -> None:
    """Configure loguru logger with console and optional file output.

    Removes existing handlers and adds new ones based on configuration.
    Supports colored console output and optionally writes to file with custom formats.

    Parameters
    ----------
    level : Literal["WARNING", "INFO", "DEBUG", "TRACE"]
        Minimum log level to output. "TRACE" shows function entry/exit level.
        Default is "INFO".
    module : str | None
        Optional module name to filter logs (only show logs from this module).
        Default is None (show all modules).
    tracing : bool
        If True, enables detailed format with timestamps, module names, and line numbers.
        Useful for debugging. Default is False.
    log_file : str | None
        Path to file for logging output. If provided, logs append to file.
        Default is None (no file logging). Format determined by fmt or tracing.
    fmt : str | None
        Custom loguru format string for log output. If None, uses default format
        or tracing format (see tracing parameter). Default is None.
        Format can include: {time}, {level}, {name}, {line}, {message}, {extra[short_level]}
    enable_console_log : bool
        If True, logs output to stderr with colors. Default is True.
    **kwargs : Any
        Additional keyword arguments passed to loguru logger.add().
        Common options: rotation (log file rotation), retention (cleanup policy)

    Returns
    -------
    None

    Examples
    --------
    Basic setup with INFO level:

    >>> from r2x_core.logger import setup_logging
    >>> setup_logging()

    Debug mode with file logging:

    >>> setup_logging(level="DEBUG", log_file="/tmp/debug.log")

    Tracing mode for development:

    >>> setup_logging(level="TRACE", tracing=True)

    Custom format with rotation:

    >>> setup_logging(
    ...     fmt="<level>{level}</level> | {message}",
    ...     log_file="app.log",
    ...     rotation="100 MB"  # Rotate file at 100MB
    ... )

    Notes
    -----
    - First call to setup_logging() removes all existing loguru handlers
    - Subsequent calls will reset logging configuration
    - Log levels are mapped to short names: WARNING→WARN, ERROR→FAIL, INFO→INFO, DEBUG→DEBUG, TRACE→STEP
    - Colorized output only applies to console (stderr), not file
    - File logging appends to existing file (mode='a')
    - Use loguru.logger globally after setup: from loguru import logger; logger.info("message")
    """
    import sys

    from loguru import logger

    levels_alias = {
        "WARNING": "WARN",
        "INFO": "INFO",
        "DEBUG": "DEBUG",
        "ERROR": "FAIL",
        "TRACE": "STEP",
        "SUCCESS": "OK",
    }
    logger.remove()
    logger.enable(module or "")

    fmt = fmt or "<level>{extra[short_level]:<4}</level> {message}"

    if tracing:
        fmt = "<green>[{time:YYYY-MM-DDTHH:mm:ss}]</green> {name:.15}:{line:<3} <level>{extra[short_level]:>5}</level> {message}"

    def _inject_short_level(record: Any) -> bool:
        """Inject custom short log level name into record extra data.

        Maps standard log level names to short forms used in format strings:
        WARNING→WARN, ERROR→FAIL, TRACE→STEP, others unchanged.

        Parameters
        ----------
        record : Any
            Loguru log record with 'level' and 'extra' fields.

        Returns
        -------
        bool
            Always True to pass the filter.
        """
        record["extra"]["short_level"] = levels_alias.get(record["level"].name, record["level"].name)
        return True

    if enable_console_log:
        logger.add(
            sys.stderr,
            level=level,
            colorize=True,
            format=fmt,
            filter=_inject_short_level,
            **kwargs,
        )
    if log_file:
        logger.add(
            log_file,
            level=level,
            colorize=False,
            format=fmt,
            mode="a",  # append to file
            **kwargs,
        )
    return None
