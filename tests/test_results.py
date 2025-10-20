import pytest

from r2x_core.result import Err, Ok, ResultType, is_err, is_ok


@pytest.fixture
def ok_value():
    return Ok(10)


@pytest.fixture
def err_value():
    return Err("boom")


def test_ok_unwrap(ok_value):
    assert is_ok(ok_value)
    assert ok_value.unwrap() == 10


def test_err_unwrap_raises(err_value):
    assert is_err(err_value)
    with pytest.raises(ValueError, match="Called unwrap on Err: boom"):
        err_value.unwrap()


def test_ok_unwrap_or(ok_value):
    assert ok_value.unwrap_or(5) == 10


def test_err_unwrap_or(err_value):
    assert err_value.unwrap_or(5) == 5


def test_ok_unwrap_or_else(ok_value):
    assert ok_value.unwrap_or_else(lambda e: -1) == 10


def test_err_unwrap_or_else(err_value):
    assert err_value.unwrap_or_else(lambda e: f"default-{e}") == "default-boom"


def test_ok_expect(ok_value):
    assert ok_value.expect("failure") == 10


def test_err_expect_raises(err_value):
    with pytest.raises(ValueError, match="failure: boom"):
        err_value.expect("failure")


def test_ok_is_ok_and_err(ok_value):
    assert ok_value.is_ok()
    assert not ok_value.is_err()


def test_err_is_ok_and_err(err_value):
    assert not err_value.is_ok()
    assert err_value.is_err()


def test_ok_map(ok_value):
    result = ok_value.map(lambda x: x * 2)
    assert isinstance(result, Ok)
    assert result.unwrap() == 20


def test_err_map(err_value):
    result = err_value.map(lambda x: x * 2)
    assert isinstance(result, Err)
    assert result is err_value  # identity preserved


def test_ok_map_err(ok_value):
    result = ok_value.map_err(lambda e: e.upper())
    assert isinstance(result, Ok)
    assert result.unwrap() == 10


def test_err_map_err(err_value):
    result = err_value.map_err(lambda e: e.upper())
    assert isinstance(result, Err)
    assert result.error == "BOOM"


def test_ok_and_then(ok_value):
    result = ok_value.and_then(lambda x: Ok(x * 3))
    assert isinstance(result, Ok)
    assert result.unwrap() == 30


def test_err_and_then(err_value):
    result = err_value.and_then(lambda x: Ok(x * 3))
    assert result is err_value  # identity preserved


def test_ok_or_else(ok_value):
    result = ok_value.or_else(lambda e: Ok(5))
    assert isinstance(result, Ok)
    assert result.unwrap() == 10


def test_err_or_else(err_value):
    result = err_value.or_else(lambda e: Ok(f"fixed-{e}"))
    assert isinstance(result, Ok)
    assert result.unwrap() == "fixed-boom"


def test_result_type_union(ok_value, err_value):
    def takes_result(res: ResultType[int, str]) -> int:
        if res.is_ok():
            return res.unwrap()
        return -1

    assert takes_result(ok_value) == 10
    assert takes_result(err_value) == -1
