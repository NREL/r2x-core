"""Tests for logging."""

import json
import sys

from loguru import logger

from r2x_core.logger import setup_logging


def test_setup_logging_emits_json_when_not_tty(monkeypatch, capsys):
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    setup_logging(verbosity=1)

    logger.bind(name="r2x_core.test").info("hello")

    output = capsys.readouterr().err.strip().splitlines()
    assert output
    payload = json.loads(output[-1])
    assert payload["msg"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "r2x_core.test"


def test_setup_logging_defaults_to_warning(monkeypatch, capsys):
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    setup_logging()

    logger.info("not shown")
    logger.warning("shown")

    output = capsys.readouterr().err.strip().splitlines()
    assert output
    payload = json.loads(output[-1])
    assert payload["level"] == "WARN"
