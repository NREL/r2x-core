"""Rust-like error handling."""

# ruff: noqa D101
from __future__ import annotations
from typing import Callable, Generic, Literal, Optional, TypeVar, cast, overload, Any, TypeGuard, Type, TextIO
import sys
from .exceptions import IsNotError, UnwrapError
import traceback

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


class Result(Generic[T, E]):
    """Base type for Ok/Err results."""

    __slots__ = ()

    def unwrap(self) -> T:
        """Return the contained value if successful, else raise in subclass."""
        raise NotImplementedError  # pragma: no cover

    def unwrap_err(self) -> E:
        """Return the contained error if Err, else raise in subclass."""
        raise NotImplementedError  # pragma: no cover

    def unwrap_or(self, default: T) -> T:
        """Return the contained value if Ok, otherwise return the default."""
        raise NotImplementedError  # pragma: no cover

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Return the contained value if Ok, otherwise compute a default with func."""
        raise NotImplementedError  # pragma: no cover

    def expect(self, msg: str) -> T:
        """Return the contained value if Ok, otherwise raise with custom message."""
        raise NotImplementedError  # pragma: no cover

    def is_ok(self) -> bool:  # pragma: no cover
        """Return true if Ok"""
        return isinstance(self, Ok)

    def is_err(self) -> bool:  # pragma: no cover
        """Return true if Err"""
        return isinstance(self, Err)

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        """Apply func to the contained value if Ok, returning a new Result."""
        raise NotImplementedError  # pragma: no cover

    def map_err(self, func: Callable[[E], F]) -> Result[T, F]:
        """Apply func to the error if Err, returning a new Result."""
        raise NotImplementedError  # pragma: no cover

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another computation on the contained value if Ok."""
        raise NotImplementedError  # pragma: no cover

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Handle the error by calling func if Err, returning a new Result."""
        raise NotImplementedError  # pragma: no cover

    def ok(self) -> T | None:
        """Return the success value if Ok, otherwise None."""
        raise NotImplementedError  # pragma: no cover

    def err(self) -> E:
        """Return the error value if Err, otherwise None."""
        raise NotImplementedError  # pragma: no cover

    @property
    def error(self) -> E | None:
        """Return the error value if Err, otherwise None."""
        return self.err()

    # new API: return value or raise an exception (boundary helper)
    def unwrap_or_raise(
        self,
        exc_type: Type[BaseException] = Exception,
        context: Optional[str] = None,
        *,
        print_tb: bool = False,
        filter_fn: Optional[Callable[[traceback.FrameSummary], bool]] = None,
    ) -> T:
        """
        Return the Ok value or raise `exc_type`.

        - On Err with a BaseException payload, raise `exc_type(context)` from payload.
        - On Err with non-exception payload, raise `exc_type(f"{context}: {payload!r}")`.
        - `print_tb` is opt-in and prints the original payload traceback if it's an exception.
        """
        raise NotImplementedError  # pragma: no cover


class Ok(Result[T, E]):
    """Success result containing a value."""

    __slots__ = ("value",)
    __match_args__ = ("value",)

    value: T

    @overload
    def __init__(self: "Ok[None, E]", value: Literal[None] = None) -> None:
        """Ok() or Ok(None) -> T resolves to None"""

    @overload
    def __init__(self: "Ok[T, E]", value: T) -> None:
        """Ok(value) -> T resolves to the type of value"""

    def __init__(self, value: Optional[T] = None) -> None:
        """Initialize an Ok result wrapping the given value.

        Parameters
        ----------
        value : T, optional
            The success value to wrap. If not provided, defaults to None.
        """
        self.value = cast(T, value)

    def __repr__(self) -> str:
        """Return repr(self)."""
        return f"Ok({self.value!r})"

    def __str__(self) -> str:
        """Return str(self)."""
        return f"Ok({self.value})"

    def __eq__(self, other: object) -> bool:
        """Return self==other."""
        if isinstance(other, Ok):
            return bool(self.value == other.value)
        return False

    def __hash__(self) -> int:
        """Return hash(self)."""
        return hash(("Ok", self.value))

    def __bool__(self) -> bool:
        """Return True (Ok results are truthy)."""
        return True

    def unwrap(self) -> T:
        """Return the wrapped success value."""
        return self.value

    def unwrap_err(self) -> E:
        """Called on Ok — no error present."""
        raise UnwrapError("Called unwrap_err on Ok")

    def unwrap_or(self, default: T) -> T:
        """Return the wrapped value, ignoring default."""
        return self.value

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Return the wrapped value, ignoring the error handling function."""
        return self.value

    def expect(self, msg: str) -> T:
        """Return the wrapped value without error."""
        return self.value

    def is_ok(self) -> bool:
        """Return True indicating this is an Ok result."""
        return True

    def is_err(self) -> bool:
        """Return False indicating this is not an Err result."""
        return False

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        """Apply func to the wrapped value, returning a new Ok result."""
        return Ok(func(self.value))

    def map_err(self, func: Callable[[E], F]) -> Result[T, F]:
        """Ignore errors and return self unchanged."""
        return Ok(self.value)

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Apply func to the wrapped value and return its result."""
        return func(self.value)

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Ignore errors and return self unchanged."""
        return Ok(self.value)

    def ok(self) -> T:
        """Return the success value."""
        return self.value

    def err(self) -> E:
        """Return None as this is not an error."""
        raise IsNotError

    def unwrap_or_raise(
        self,
        exc_type: Type[BaseException] = Exception,
        context: str | None = None,
        *,
        print_tb: bool = False,
        filter_fn: Optional[Callable[[traceback.FrameSummary], bool]] = None,
    ) -> T:
        """Return the Ok value (never raises since this is Ok).

        Parameters
        ----------
        exc_type : Type[BaseException], optional
            Exception type to raise (unused, but accepted for API compatibility).
        context : str | None, optional
            Context message (unused for Ok).
        print_tb : bool, optional
            Whether to print traceback (unused for Ok).
        filter_fn : Callable | None, optional
            Traceback filter function (unused for Ok).

        Returns
        -------
        T
            The wrapped success value.
        """
        return self.value


class Err(Result[T, E]):
    """Error result containing an error value."""

    __slots__ = ("_error_value",)
    __match_args__ = ("error",)

    def __init__(self, error: E) -> None:
        """Initialize an Err result wrapping the given error.

        Parameters
        ----------
        error : E
            The error to wrap.
        """
        self._error_value = error

    def __repr__(self) -> str:
        """Return repr(self)."""
        return f"Err({self._error_value!r})"

    def __str__(self) -> str:
        """Return str(self)."""
        return f"Err({self._error_value})"

    def __eq__(self, other: object) -> bool:
        """Return self==other."""
        if isinstance(other, Err):
            return bool(self._error_value == other._error_value)
        return False

    def __hash__(self) -> int:
        """Return hash(self)."""
        return hash(("Err", self._error_value))

    def __bool__(self) -> bool:
        """Return False (Err results are falsy)."""
        return False

    def unwrap(self) -> T:
        """Raise UnwrapError when called on Err."""
        raise UnwrapError(f"Called unwrap on Err: {self._error_value}")

    def unwrap_err(self) -> E:
        """Called on Err return error value"""
        return self._error_value

    def unwrap_or(self, default: T) -> T:
        """Return the default value as this is an Err result."""
        return default

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Invoke func on the error to obtain a default value."""
        return func(self._error_value)

    def expect(self, msg: str) -> T:
        """Raise an error with a custom message and the wrapped error."""
        raise UnwrapError(f"{msg}: {self._error_value}")

    def is_ok(self) -> bool:
        """Return False indicating this is not an Ok result."""
        return False

    def is_err(self) -> bool:
        """Return True indicating this is an Err result."""
        return True

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        """Ignore success mapping and return self unchanged."""
        return Err(self._error_value)

    def map_err(self, func: Callable[[E], F]) -> Result[T, F]:
        """Apply func to the error, returning a new Err result."""
        return Err(func(self._error_value))

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Ignore chaining for Err and return self unchanged."""
        return Err(self._error_value)

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Invoke func on the error to recover and return its result."""
        return func(self._error_value)

    def ok(self) -> T | None:
        """Return None as this is an error."""
        return None

    def err(self) -> E:
        """Return the error value."""
        return self._error_value

    def unwrap_or_raise(
        self,
        exc_type: Type[BaseException] = Exception,
        context: Optional[str] = None,
        *,
        print_tb: bool = False,
        filter_fn: Optional[Callable[[traceback.FrameSummary], bool]] = None,
    ) -> T:
        """Raise an exception containing the error value.

        If the error is a BaseException, raise it with context. For non-exception
        errors, raise exc_type with formatted error details. Optionally prints
        traceback for exception payloads.

        Parameters
        ----------
        exc_type : Type[BaseException], optional
            Exception type to raise. Defaults to Exception.
        context : str | None, optional
            Message context. If None, uses str(error). Default is None.
        print_tb : bool, optional
            If True and error is BaseException, print traceback to stderr.
            Default is False.
        filter_fn : Callable | None, optional
            Function to filter traceback frames. Default is None.

        Returns
        -------
        T
            Never returns (always raises).

        Raises
        ------
        BaseException
            The exc_type with error information chained from payload.
        """
        payload = self._error_value
        msg = context if context is not None else str(payload)

        if isinstance(payload, BaseException):
            if print_tb:
                print_exception_traceback(payload, filter_fn=filter_fn)
            raise exc_type(msg) from payload

        raise exc_type(f"{msg}: {payload!r}")


def is_ok(result: Result[T, E]) -> TypeGuard[Ok[T, E]]:
    """Check if result is Ok.

    Parameters
    ----------
    result : Result[T, E]
        Result to check

    Returns
    -------
    bool
        True if Ok, False if Err
    """
    return isinstance(result, Ok)


def is_err(result: Result[T, E]) -> TypeGuard[Err[T, E]]:
    """Check if result is Err.

    Parameters
    ----------
    result : Result[T, E]
        Result to check

    Returns
    -------
    bool
        True if Err, False if Ok
    """
    return isinstance(result, Err)


def print_exception_traceback(
    exc: BaseException,
    file: Optional[TextIO] = None,
    filter_fn: Optional[Callable[[traceback.FrameSummary], bool]] = None,
) -> None:
    """Print a readable traceback for `exc` including chained exceptions.

    This uses traceback.TracebackException so chained exceptions are preserved.
    Printing is opt-in from `unwrap_or_raise`.
    """
    if exc is None:
        return

    if file is None:
        file = sys.stderr

    te = traceback.TracebackException.from_exception(exc, capture_locals=False)

    def _print_te(te_obj: traceback.TracebackException) -> None:
        """Print traceback and exception info for TracebackException object.

        Parameters
        ----------
        te_obj : traceback.TracebackException
            Exception object to print (may have chained exceptions).
        """
        print("Traceback (most recent call last):", file=file)
        for frame in te_obj.stack:
            if filter_fn and not filter_fn(frame):
                continue  # pragma: no cover
            print(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}', file=file)
            if frame.line:
                print(f"    {frame.line.strip()}", file=file)
        for line in te_obj.format_exception_only():
            print(line.rstrip("\n"), file=file)

        if te_obj.__cause__:
            print("The above exception was the direct cause of the following exception:", file=file)
            _print_te(te_obj.__cause__)
        elif te_obj.__context__ and not te_obj.__suppress_context__:
            print("During handling of the above exception, another exception occurred:", file=file)
            _print_te(te_obj.__context__)

    _print_te(te)
