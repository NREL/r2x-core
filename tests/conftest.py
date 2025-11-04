from pathlib import Path

import pytest
from loguru import logger

from r2x_core.logger import setup_logging

DATA_FOLDER = "tests/data"
REEDS_SCENARIO = "test_Pacific"


@pytest.fixture(scope="function")
def empty_file(tmp_path) -> Path:
    empty_fpath = tmp_path / "test.csv"
    empty_fpath.write_text("")
    yield empty_fpath
    empty_fpath.unlink()


@pytest.fixture
def caplog(caplog):
    setup_logging(module="r2x_core", level="TRACE", tracing=True)
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
def data_folder(pytestconfig):
    return pytestconfig.rootpath.joinpath(DATA_FOLDER)


@pytest.fixture
def reeds_data_folder(pytestconfig):
    return pytestconfig.rootpath.joinpath(DATA_FOLDER).joinpath(REEDS_SCENARIO)
