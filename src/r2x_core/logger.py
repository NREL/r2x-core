# type: ignore
"""Setup logging for r2x-core."""

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
    """Configure logger."""
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
