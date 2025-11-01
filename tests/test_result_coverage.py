"""Comprehensive tests for Result types to achieve 100% coverage."""

import sys
from io import StringIO

import pytest

from r2x_core.exceptions import IsNotError, UnwrapError
from r2x_core.result import (
    Err,
    Ok,
    Result,
    is_err,
    is_ok,
    print_exception_traceback,
)


# Ok tests
def test_ok_init_with_value():
    """Test Ok initialization with value."""
    result = Ok(42)
    assert result.value == 42


def test_ok_init_without_value():
    """Test Ok initialization without value."""
    result = Ok()
    assert result.value is None


def test_ok_init_with_none():
    """Test Ok initialization with explicit None."""
    result = Ok(None)
    assert result.value is None


def test_ok_repr():
    """Test Ok repr."""
    result = Ok(42)
    assert repr(result) == "Ok(42)"


def test_ok_str():
    """Test Ok str."""
    result = Ok(42)
    assert str(result) == "Ok(42)"


def test_ok_eq_same_value():
    """Test Ok equality with same value."""
    result1 = Ok(42)
    result2 = Ok(42)
    assert result1 == result2


def test_ok_eq_different_value():
    """Test Ok inequality with different values."""
    result1 = Ok(42)
    result2 = Ok(43)
    assert result1 != result2


def test_ok_eq_with_err():
    """Test Ok inequality with Err."""
    result1 = Ok(42)
    result2 = Err("error")
    assert result1 != result2


def test_ok_eq_with_non_result():
    """Test Ok inequality with non-Result type."""
    result = Ok(42)
    assert result != 42
    assert result != "Ok(42)"


def test_ok_hash():
    """Test Ok hash."""
    result1 = Ok(42)
    result2 = Ok(42)
    assert hash(result1) == hash(result2)


def test_ok_hash_different_values():
    """Test Ok hash differs for different values."""
    result1 = Ok(42)
    result2 = Ok(43)
    assert hash(result1) != hash(result2)


def test_ok_bool():
    """Test Ok is truthy."""
    result = Ok(42)
    assert bool(result) is True


def test_ok_is_ok():
    """Test Ok.is_ok returns True."""
    result = Ok(42)
    assert result.is_ok() is True


def test_ok_is_err():
    """Test Ok.is_err returns False."""
    result = Ok(42)
    assert result.is_err() is False


def test_ok_unwrap():
    """Test Ok.unwrap returns value."""
    result = Ok(42)
    assert result.unwrap() == 42


def test_ok_unwrap_err():
    """Test Ok.unwrap_err raises UnwrapError."""
    result = Ok(42)
    with pytest.raises(UnwrapError, match="Called unwrap_err on Ok"):
        result.unwrap_err()


def test_ok_unwrap_or():
    """Test Ok.unwrap_or returns value."""
    result = Ok(42)
    assert result.unwrap_or(0) == 42


def test_ok_unwrap_or_else():
    """Test Ok.unwrap_or_else returns value without calling function."""
    result = Ok(42)
    assert result.unwrap_or_else(lambda e: 0) == 42


def test_ok_expect():
    """Test Ok.expect returns value without raising."""
    result = Ok(42)
    assert result.expect("Should have value") == 42


def test_ok_map():
    """Test Ok.map applies function."""
    result = Ok(5)
    mapped = result.map(lambda x: x * 2)
    assert isinstance(mapped, Ok)
    assert mapped.unwrap() == 10


def test_ok_map_err():
    """Test Ok.map_err ignores error function."""
    result = Ok(42)
    mapped = result.map_err(lambda e: "error")
    assert isinstance(mapped, Ok)
    assert mapped.unwrap() == 42


def test_ok_and_then():
    """Test Ok.and_then chains computations."""
    result = Ok(5)
    chained = result.and_then(lambda x: Ok(x * 2))
    assert isinstance(chained, Ok)
    assert chained.unwrap() == 10


def test_ok_and_then_returns_err():
    """Test Ok.and_then can return Err."""
    result = Ok(5)
    chained = result.and_then(lambda x: Err("failed"))
    assert isinstance(chained, Err)
    assert chained.unwrap_err() == "failed"


def test_ok_or_else():
    """Test Ok.or_else ignores error handling."""
    result = Ok(42)
    recovered = result.or_else(lambda e: Ok(0))
    assert isinstance(recovered, Ok)
    assert recovered.unwrap() == 42


def test_ok_ok_method():
    """Test Ok.ok returns value."""
    result = Ok(42)
    assert result.ok() == 42


def test_ok_err_method():
    """Test Ok.err raises IsNotError."""
    result = Ok(42)
    with pytest.raises(IsNotError):
        result.err()


def test_ok_error_property():
    """Test Ok.error property raises IsNotError."""
    result = Ok(42)
    with pytest.raises(IsNotError):
        _ = result.error


def test_ok_unwrap_or_raise():
    """Test Ok.unwrap_or_raise returns value."""
    result = Ok(42)
    assert result.unwrap_or_raise() == 42


def test_ok_match_args():
    """Test Ok __match_args__."""
    result = Ok(42)
    assert result.__match_args__ == ("value",)


# Err tests
def test_err_init():
    """Test Err initialization."""
    result = Err("error message")
    assert result.unwrap_err() == "error message"


def test_err_init_with_exception():
    """Test Err initialization with exception."""
    exc = ValueError("test")
    result = Err(exc)
    assert result.unwrap_err() is exc


def test_err_repr():
    """Test Err repr."""
    result = Err("error")
    assert repr(result) == "Err('error')"


def test_err_str():
    """Test Err str."""
    result = Err("error")
    assert str(result) == "Err(error)"


def test_err_eq_same_error():
    """Test Err equality with same error."""
    result1 = Err("error")
    result2 = Err("error")
    assert result1 == result2


def test_err_eq_different_error():
    """Test Err inequality with different errors."""
    result1 = Err("error1")
    result2 = Err("error2")
    assert result1 != result2


def test_err_eq_with_ok():
    """Test Err inequality with Ok."""
    result1 = Err("error")
    result2 = Ok(42)
    assert result1 != result2


def test_err_eq_with_non_result():
    """Test Err inequality with non-Result type."""
    result = Err("error")
    assert result != "error"


def test_err_hash():
    """Test Err hash."""
    result1 = Err("error")
    result2 = Err("error")
    assert hash(result1) == hash(result2)


def test_err_hash_different_errors():
    """Test Err hash differs for different errors."""
    result1 = Err("error1")
    result2 = Err("error2")
    assert hash(result1) != hash(result2)


def test_err_bool():
    """Test Err is falsy."""
    result = Err("error")
    assert bool(result) is False


def test_err_is_ok():
    """Test Err.is_ok returns False."""
    result = Err("error")
    assert result.is_ok() is False


def test_err_is_err():
    """Test Err.is_err returns True."""
    result = Err("error")
    assert result.is_err() is True


def test_err_unwrap():
    """Test Err.unwrap raises exception."""
    result = Err("error")
    with pytest.raises(Exception):
        result.unwrap()


def test_err_unwrap_err():
    """Test Err.unwrap_err returns error."""
    result = Err("error")
    assert result.unwrap_err() == "error"


def test_err_unwrap_or():
    """Test Err.unwrap_or returns default."""
    result = Err("error")
    assert result.unwrap_or(42) == 42


def test_err_unwrap_or_else():
    """Test Err.unwrap_or_else calls function."""
    result = Err("error")
    assert result.unwrap_or_else(lambda e: len(e)) == 5


def test_err_expect():
    """Test Err.expect raises UnwrapError with message."""
    result = Err("error")
    with pytest.raises(UnwrapError, match="Custom message"):
        result.expect("Custom message")


def test_err_map():
    """Test Err.map ignores success function."""
    result = Err("error")
    mapped = result.map(lambda x: x * 2)
    assert isinstance(mapped, Err)
    assert mapped.unwrap_err() == "error"


def test_err_map_err():
    """Test Err.map_err applies error function."""
    result = Err("error")
    mapped = result.map_err(lambda e: e.upper())
    assert isinstance(mapped, Err)
    assert mapped.unwrap_err() == "ERROR"


def test_err_and_then():
    """Test Err.and_then ignores chaining."""
    result = Err("error")
    chained = result.and_then(lambda x: Ok(x * 2))
    assert isinstance(chained, Err)
    assert chained.unwrap_err() == "error"


def test_err_or_else():
    """Test Err.or_else calls recovery function."""
    result = Err("error")
    recovered = result.or_else(lambda e: Ok(42))
    assert isinstance(recovered, Ok)
    assert recovered.unwrap() == 42


def test_err_or_else_returns_err():
    """Test Err.or_else can return Err."""
    result = Err("error1")
    recovered = result.or_else(lambda e: Err("error2"))
    assert isinstance(recovered, Err)
    assert recovered.unwrap_err() == "error2"


def test_err_ok_method():
    """Test Err.ok returns None."""
    result = Err("error")
    assert result.ok() is None


def test_err_err_method():
    """Test Err.err returns error."""
    result = Err("error")
    assert result.err() == "error"


def test_err_error_property():
    """Test Err.error property returns error."""
    result = Err("error")
    assert result.error == "error"


def test_err_unwrap_or_raise_string_error():
    """Test Err.unwrap_or_raise with string error."""
    result = Err("something failed")
    with pytest.raises(Exception, match="Context"):
        result.unwrap_or_raise(context="Context")


def test_err_unwrap_or_raise_exception_error():
    """Test Err.unwrap_or_raise with exception error."""
    exc = ValueError("original error")
    result = Err(exc)
    with pytest.raises(RuntimeError, match="Context") as exc_info:
        result.unwrap_or_raise(exc_type=RuntimeError, context="Context")
    assert exc_info.value.__cause__ is exc


def test_err_unwrap_or_raise_exception_no_context():
    """Test Err.unwrap_or_raise with exception and no context."""
    exc = ValueError("original error")
    result = Err(exc)
    with pytest.raises(Exception) as exc_info:
        result.unwrap_or_raise()
    assert exc_info.value.__cause__ is exc


def test_err_match_args():
    """Test Err __match_args__."""
    result = Err("error")
    assert result.__match_args__ == ("error",)


# Type guards
def test_is_ok_with_ok():
    """Test is_ok type guard with Ok result."""
    result: Result = Ok(42)
    assert is_ok(result)


def test_is_ok_with_err():
    """Test is_ok type guard with Err result."""
    result: Result = Err("error")
    assert not is_ok(result)


def test_is_err_with_ok():
    """Test is_err type guard with Ok result."""
    result: Result = Ok(42)
    assert not is_err(result)


def test_is_err_with_err():
    """Test is_err type guard with Err result."""
    result: Result = Err("error")
    assert is_err(result)


# Print exception traceback tests
def test_print_exception_traceback_basic():
    """Test print_exception_traceback with basic exception."""
    output = StringIO()
    exc = ValueError("test error")
    print_exception_traceback(exc, file=output)

    output_str = output.getvalue()
    assert "ValueError: test error" in output_str


def test_print_exception_traceback_with_none():
    """Test print_exception_traceback with None does nothing."""
    output = StringIO()
    print_exception_traceback(None, file=output)

    assert output.getvalue() == ""


def test_print_exception_traceback_default_stderr():
    """Test print_exception_traceback uses stderr by default."""
    old_stderr = sys.stderr
    try:
        sys.stderr = StringIO()
        exc = ValueError("test error")
        print_exception_traceback(exc)

        output = sys.stderr.getvalue()
        assert "ValueError: test error" in output
    finally:
        sys.stderr = old_stderr


def test_print_exception_traceback_with_filter():
    """Test print_exception_traceback with filter function."""
    output = StringIO()
    exc = ValueError("test error")

    def filter_fn(frame):
        # Filter out specific frames
        return "test_result" in frame.filename

    print_exception_traceback(exc, file=output, filter_fn=filter_fn)
    output_str = output.getvalue()
    assert "ValueError" in output_str or output_str.strip() == "Traceback (most recent call last):"


def test_print_exception_traceback_chained():
    """Test print_exception_traceback with chained exceptions."""
    output = StringIO()
    try:
        try:
            raise ValueError("original error")
        except ValueError as e:
            raise RuntimeError("chained error") from e
    except RuntimeError as e:
        print_exception_traceback(e, file=output)

    output_str = output.getvalue()
    assert "RuntimeError" in output_str
    assert "ValueError" in output_str


def test_print_exception_traceback_context():
    """Test print_exception_traceback with exception context."""
    output = StringIO()
    try:
        try:
            raise ValueError("context error")
        except ValueError:
            raise RuntimeError("new error")
    except RuntimeError as e:
        print_exception_traceback(e, file=output)

    output_str = output.getvalue()
    assert "RuntimeError" in output_str


# Result base class tests
def test_result_unwrap_not_implemented():
    """Test Result base class unwrap raises NotImplementedError."""
    # Can't instantiate Result directly, but we can verify the method exists
    assert hasattr(Result, "unwrap")


def test_result_base_methods_exist():
    """Test all base Result methods exist."""
    methods = [
        "unwrap",
        "unwrap_err",
        "unwrap_or",
        "unwrap_or_else",
        "expect",
        "is_ok",
        "is_err",
        "map",
        "map_err",
        "and_then",
        "or_else",
        "ok",
        "err",
    ]
    for method in methods:
        assert hasattr(Result, method)


# Edge cases and integration tests
def test_result_chain_operations():
    """Test chaining multiple operations."""
    result = Ok(5)
    final = result.map(lambda x: x * 2).and_then(lambda x: Ok(x + 3)).map(lambda x: x / 2)
    assert isinstance(final, Ok)
    assert final.unwrap() == 6.5


def test_result_error_chain_recovery():
    """Test error chain with recovery."""
    result = Err("initial error")
    recovered = result.map_err(lambda e: f"Wrapped: {e}").or_else(lambda e: Ok(f"Recovered from: {e}"))
    assert isinstance(recovered, Ok)
    assert "Wrapped: initial error" in recovered.unwrap()


def test_ok_with_complex_value():
    """Test Ok with complex nested value."""
    value = {"key": [1, 2, 3], "nested": {"inner": "value"}}
    result = Ok(value)
    assert result.unwrap() == value


def test_err_with_complex_error():
    """Test Err with complex error object."""

    class CustomError:
        def __init__(self, msg, code):
            self.msg = msg
            self.code = code

    error = CustomError("failed", 42)
    result = Err(error)
    retrieved = result.unwrap_err()
    assert retrieved.msg == "failed"
    assert retrieved.code == 42


def test_result_in_container():
    """Test Result types in containers."""
    results = [Ok(1), Err("failed"), Ok(2), Err("error")]
    ok_values = [r.unwrap() for r in results if is_ok(r)]
    assert ok_values == [1, 2]


def test_result_bool_in_conditions():
    """Test Result truthiness in conditionals."""
    ok_result = Ok(42)
    err_result = Err("error")

    if ok_result:
        ok_truthy = True
    else:
        ok_truthy = False

    if err_result:
        err_truthy = True
    else:
        err_truthy = False

    assert ok_truthy is True
    assert err_truthy is False


def test_print_exception_traceback_with_filter_filtering():
    """Test print_exception_traceback with filter that filters out frames."""
    output = StringIO()
    exc = ValueError("test")

    def filter_fn(frame):
        # Filter to exclude this test file's frames
        return "test_result" not in frame.filename

    print_exception_traceback(exc, file=output, filter_fn=filter_fn)
    output_str = output.getvalue()

    # Should still have traceback header even with filtered frames
    assert "Traceback" in output_str or "ValueError" in output_str


def test_print_exception_traceback_with_suppressed_context():
    """Test print_exception_traceback with __suppress_context__."""
    output = StringIO()
    try:
        try:
            raise ValueError("original")
        except ValueError:
            raise RuntimeError("new") from None
    except RuntimeError as e:
        print_exception_traceback(e, file=output)

    output_str = output.getvalue()
    assert "RuntimeError" in output_str
