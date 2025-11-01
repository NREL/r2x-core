"""Setup logging for r2x-core."""

from typing import Literal


def setup_logging(
    level: Literal["WARNING", "INFO", "DEBUG", "TRACE"] = "INFO",
    module: str | None = None,
    tracing: bool = False,
    log_file: str | None = None,
    **kwargs,
):
    """Configure logger."""
    import sys

    from loguru import logger

    """Setup logging from r2x_core."""

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

    fmt = "<level>{extra[short_level]:<4}</level> {message}"

    if tracing:
        fmt = "<green>[{time:YYYY-MM-DDTHH:mm:ss}]</green> {name:.15}:{line:<3} <level>{extra[short_level]:>5}</level> {message}"

    def inject_short_level(record):
        record["extra"]["short_level"] = levels_alias.get(record["level"].name, record["level"].name)
        return True  # filter must return True to keep record

    logger.add(
        sys.stderr,
        level=level,
        enqueue=True,
        colorize=True,
        format=fmt,
        filter=inject_short_level,
        **kwargs,
    )
    if log_file:
        logger.add(
            log_file,
            level=level,
            enqueue=True,
            colorize=False,
            format=fmt,
            mode="w",  # overwrite file each run
            **kwargs,
        )
