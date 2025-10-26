from pathlib import Path

import pytest
from loguru import logger

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
    logger.enable("r2x_core")
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
def data_folder(pytestconfig):
    return pytestconfig.rootpath.joinpath(DATA_FOLDER)


@pytest.fixture
def reeds_data_folder(pytestconfig):
    return pytestconfig.rootpath.joinpath(DATA_FOLDER).joinpath(REEDS_SCENARIO)
