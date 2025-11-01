import pytest

from r2x_core.result import Err, IsNotError, Ok, Result, UnwrapError, is_err, is_ok


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
    assert err_value.unwrap_err()


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
    with pytest.raises(UnwrapError, match="failure: boom"):
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
    assert result.error == "boom"


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
    assert isinstance(result, Err)
    assert result.error == "boom"


def test_ok_or_else(ok_value):
    result = ok_value.or_else(lambda e: Ok(5))
    assert isinstance(result, Ok)
    assert result.unwrap() == 10


def test_err_or_else(err_value):
    result = err_value.or_else(lambda e: Ok(f"fixed-{e}"))
    assert isinstance(result, Ok)
    assert result.unwrap() == "fixed-boom"


def test_result_type_union(ok_value, err_value):
    def takes_result(res: Result[int, str]) -> int:
        if res.is_ok():
            return res.unwrap()
        return -1

    assert takes_result(ok_value) == 10
    assert takes_result(err_value) == -1


def test_ok_repr():
    """Test __repr__ for Ok."""
    ok = Ok(42)
    assert repr(ok) == "Ok(42)"
    ok_str = Ok("hello")
    assert repr(ok_str) == "Ok('hello')"


def test_err_repr():
    """Test __repr__ for Err."""
    err = Err("error")
    assert repr(err) == "Err('error')"
    err_int = Err(404)
    assert repr(err_int) == "Err(404)"


def test_ok_str():
    """Test __str__ for Ok."""
    ok = Ok(42)
    assert str(ok) == "Ok(42)"


def test_err_str():
    """Test __str__ for Err."""
    err = Err("error")
    assert str(err) == "Err(error)"


def test_ok_equality():
    """Test __eq__ for Ok values."""
    assert Ok(1) == Ok(1)
    assert Ok("test") == Ok("test")
    assert Ok(1) != Ok(2)
    assert Ok(1) != Err(1)
    assert Ok(1) != "not a result"


def test_err_equality():
    """Test __eq__ for Err values."""
    assert Err("a") == Err("a")
    assert Err(404) == Err(404)
    assert Err("a") != Err("b")
    assert Err(1) != Ok(1)
    assert Err("x") != "not a result"


def test_ok_hash():
    """Test __hash__ for Ok - enables use in sets and dicts."""
    ok1 = Ok(1)
    ok2 = Ok(1)
    ok3 = Ok(2)

    # Can be added to sets
    result_set = {ok1, ok2, ok3}
    assert len(result_set) == 2  # ok1 and ok2 are the same

    # Can be used as dict keys
    result_dict = {ok1: "first", ok3: "second"}
    assert result_dict[ok2] == "first"


def test_err_hash():
    """Test __hash__ for Err - enables use in sets and dicts."""
    err1 = Err("a")
    err2 = Err("a")
    err3 = Err("b")

    # Can be added to sets
    result_set = {err1, err2, err3}
    assert len(result_set) == 2

    # Can be used as dict keys
    result_dict = {err1: "first", err3: "second"}
    assert result_dict[err2] == "first"


def test_ok_bool():
    """Test __bool__ for Ok - Ok is always truthy."""
    assert bool(Ok(1)) is True
    assert bool(Ok(0)) is True
    assert bool(Ok(None)) is True
    assert bool(Ok(False)) is True

    # Can use in if statements
    passed = bool(Ok(42))
    assert passed is True


def test_err_bool():
    """Test __bool__ for Err - Err is always falsy."""
    assert bool(Err("error")) is False
    assert bool(Err(0)) is False
    assert bool(Err(None)) is False

    # Can use in if statements
    passed = not Err("error")
    assert passed is True


def test_ok_ok_method():
    """Test ok() method for Ok - returns the value."""
    assert Ok(42).ok() == 42
    assert Ok("test").ok() == "test"
    assert Ok(None).ok() is None


def test_ok_err_method():
    """Test err() method for Ok - returns None."""
    with pytest.raises(IsNotError):
        Ok(42).err()

    with pytest.raises(IsNotError):
        Ok("test").err()


def test_err_ok_method():
    """Test ok() method for Err - returns None."""
    assert Err("error").ok() is None
    assert Err(404).ok() is None


def test_err_err_method():
    """Test err() method for Err - returns the error."""
    assert Err("error").err() == "error"
    assert Err(404).err() == 404
    assert Err(None).err() is None


def test_pattern_matching_ok():
    """Test pattern matching with Ok (Python 3.10+)."""
    result = Ok(100)

    match result:
        case Ok(value):
            matched_value = value
        case Err(_):
            matched_value = None

    assert matched_value == 100


def test_pattern_matching_err():
    """Test pattern matching with Err (Python 3.10+)."""
    result = Err("failure")

    match result:
        case Ok(_):
            matched_error = None
        case Err(error):
            matched_error = error

    assert matched_error == "failure"


def test_pattern_matching_with_guard():
    """Test pattern matching with guards."""

    def classify_result(res: Result[int, str]) -> str:
        match res:
            case Ok(value) if value > 10:
                return "big success"
            case Ok(value):
                return "small success"
            case Err(error):
                return f"error: {error}"

    assert classify_result(Ok(100)) == "big success"
    assert classify_result(Ok(5)) == "small success"
    assert classify_result(Err("boom")) == "error: boom"


def test_unwrap_error_exception():
    """Test that UnwrapError is raised and can be caught."""
    err = Err("test error")

    with pytest.raises(UnwrapError):
        err.unwrap()

    assert err.error == err.unwrap_err()


def test_unwrap_error_expect():
    """Test that UnwrapError is raised by expect()."""
    err = Err("original")

    with pytest.raises(UnwrapError) as exc_info:
        err.expect("custom message")

    assert "custom message: original" in str(exc_info.value)


def test_ok_err_extraction_pattern():
    """Test using ok() and err() for safe extraction."""

    def get_value_safely(res: Result[int, str]) -> int:
        value = res.ok()
        if value is not None:
            return value
        return 0

    assert get_value_safely(Ok(42)) == 42
    assert get_value_safely(Err("error")) == 0


def test_hashable_in_complex_structures():
    """Test that Results work in complex data structures."""
    # List of results
    results = [Ok(1), Err("a"), Ok(2), Err("b")]

    # Filter to only Ok values
    ok_values = [r.ok() for r in results if r.is_ok()]
    assert ok_values == [1, 2]

    # Set of results (deduplication)
    result_set = {Ok(1), Ok(1), Err("x"), Err("x")}
    assert len(result_set) == 2

    # Dict mapping results to metadata
    result_metadata = {Ok(1): "first success", Err("x"): "first error"}
    assert result_metadata[Ok(1)] == "first success"


def test_bool_with_truthiness_patterns():
    """Test using bool() in common patterns."""
    results = [Ok(1), Err("a"), Ok(2), Err("b"), Ok(3)]

    # Count successes using truthiness
    success_count = sum(1 for r in results if r)
    assert success_count == 3

    # Get first success or default
    first_success = next((r for r in results if r), Ok(0))
    assert first_success == Ok(1)

    # Filter failures
    failures = [r for r in results if not r]
    assert len(failures) == 2


def test_unwrap_or_raise_ok_returns_value():
    ok = Ok(5)
    assert ok.unwrap_or_raise(ValueError, "should not raise") == 5


def test_unwrap_or_raise_err_non_exception_payload():
    err = Err("boom")
    with pytest.raises(RuntimeError) as exc_info:
        err.unwrap_or_raise(RuntimeError, "failed")
    assert "failed: 'boom'" in str(exc_info.value)


def test_unwrap_or_raise_err_exception_payload_chains():
    inner = ValueError("inner")
    err = Err(inner)
    with pytest.raises(RuntimeError) as exc_info:
        err.unwrap_or_raise(RuntimeError, "failed")

    # preserve chaining
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert str(exc_info.value.__cause__) == "inner"


def test_unwrap_or_raise_prints_traceback_when_requested(capfd):
    inner = ValueError("inner")
    err = Err(inner)
    with pytest.raises(RuntimeError):
        err.unwrap_or_raise(RuntimeError, "failed", print_tb=True)

    captured = capfd.readouterr()
    # traceback printing goes to stderr
    assert "Traceback (most recent call last):" in captured.err
    assert "ValueError" in captured.err
    assert "inner" in captured.err


def test_ok_with_value():
    """Test Ok result with value."""
    result = Ok(42)

    assert result.is_ok()
    assert not result.is_err()
    assert result.value == 42


def test_ok_without_value():
    """Test Ok result without value."""
    result = Ok()

    assert result.is_ok()
    assert result.value is None


def test_err_with_error():
    """Test Err result with error."""
    result = Err("error message")

    assert result.is_err()
    assert not result.is_ok()
    assert result.error == "error message"


def test_err_with_exception():
    """Test Err result with exception."""
    exc = ValueError("test error")
    result = Err(exc)

    assert result.is_err()
    assert result.error == exc


def test_result_map_ok():
    """Test mapping over Ok result."""
    result = Ok(5)
    mapped = result.map(lambda x: x * 2)

    assert mapped.is_ok()
    assert mapped.value == 10


def test_result_map_err():
    """Test mapping over Err result."""
    result = Err("error")
    mapped = result.map(lambda x: x * 2)

    assert mapped.is_err()
    assert mapped.error == "error"


def test_result_unwrap_ok():
    """Test unwrapping Ok result."""
    result = Ok(42)
    assert result.unwrap() == 42


def test_result_unwrap_err():
    """Test unwrapping Err result raises."""
    result = Err("error")
    with pytest.raises(Exception):
        result.unwrap()


def test_result_unwrap_or_ok():
    """Test unwrap_or with Ok result."""
    result = Ok(42)
    assert result.unwrap_or(0) == 42


def test_result_unwrap_or_err():
    """Test unwrap_or with Err result."""
    result = Err("error")
    assert result.unwrap_or(0) == 0
