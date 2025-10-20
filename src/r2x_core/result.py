"""Rust-like error handling."""

# ruff: noqa D101
from __future__ import annotations
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


class Result(Generic[T, E]):
    """Base type for Ok/Err results."""

    __slots__ = ()

    def unwrap(self) -> T:
        """Return the contained value if successful, else raise in subclass."""
        raise NotImplementedError

    def unwrap_or(self, default: T) -> T:
        """Return the contained value if Ok, otherwise return the default."""
        raise NotImplementedError

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Return the contained value if Ok, otherwise compute a default with func."""
        raise NotImplementedError

    def expect(self, msg: str) -> T:
        """Return the contained value if Ok, otherwise raise with custom message."""
        raise NotImplementedError

    def is_ok(self) -> bool:
        """Return True if this is an Ok result, False otherwise."""
        raise NotImplementedError

    def is_err(self) -> bool:
        """Return True if this is an Err result, False otherwise."""
        raise NotImplementedError

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        """Apply func to the contained value if Ok, returning a new Result."""
        raise NotImplementedError

    def map_err(self, func: Callable[[E], F]) -> Result[T, F]:
        """Apply func to the error if Err, returning a new Result."""
        raise NotImplementedError

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another computation on the contained value if Ok."""
        raise NotImplementedError

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Handle the error by calling func if Err, returning a new Result."""
        raise NotImplementedError


class Ok(Result[T, E]):
    """Success result containing a value."""

    __slots__ = ("value",)

    def __init__(self, value: T) -> None:
        """Initialize an Ok result wrapping the given value.

        Parameters
        ----------
        value : T
            The success value to wrap.
        """
        self.value = value

    def unwrap(self) -> T:
        """Return the wrapped success value."""
        return self.value

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
        return self  # type: ignore

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Apply func to the wrapped value and return its result."""
        return func(self.value)

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Ignore errors and return self unchanged."""
        return self  # type: ignore


class Err(Result[T, E]):
    """Error result containing an error value."""

    __slots__ = ("error",)

    def __init__(self, error: E) -> None:
        """Initialize an Err result wrapping the given error.

        Parameters
        ----------
        error : E
            The error to wrap.
        """
        self.error = error

    def unwrap(self) -> T:
        """Raise an error indicating unwrap was called on Err."""
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Return the default value as this is an Err result."""
        return default

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Invoke func on the error to obtain a default value."""
        return func(self.error)

    def expect(self, msg: str) -> T:
        """Raise an error with a custom message and the wrapped error."""
        raise ValueError(f"{msg}: {self.error}")

    def is_ok(self) -> bool:
        """Return False indicating this is not an Ok result."""
        return False

    def is_err(self) -> bool:
        """Return True indicating this is an Err result."""
        return True

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        """Ignore success mapping and return self unchanged."""
        return self  # type: ignore

    def map_err(self, func: Callable[[E], F]) -> Result[T, F]:
        """Apply func to the error, returning a new Err result."""
        return Err(func(self.error))

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Ignore chaining for Err and return self unchanged."""
        return self  # type: ignore

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Invoke func on the error to recover and return its result."""
        return func(self.error)


def is_ok(result: Result[T, E]) -> bool:
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


def is_err(result: Result[T, E]) -> bool:
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
