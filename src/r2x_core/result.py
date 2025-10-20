"""Rust-like error handling."""

# ruff: noqa D!01
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
        raise NotImplementedError

    def unwrap_or(self, default: T) -> T:
        raise NotImplementedError

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        raise NotImplementedError

    def expect(self, msg: str) -> T:
        raise NotImplementedError

    def is_ok(self) -> bool:
        raise NotImplementedError

    def is_err(self) -> bool:
        raise NotImplementedError

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        raise NotImplementedError

    def map_err(self, func: Callable[[E], F]) -> Result[T, F]:
        raise NotImplementedError

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        raise NotImplementedError

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        raise NotImplementedError


class Ok(Result[T, E]):
    __slots__ = ("value",)

    def __init__(self, value: T) -> None:
        self.value = value

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        return self.value

    def expect(self, msg: str) -> T:
        return self.value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        return Ok(func(self.value))

    def map_err(self, func: Callable[[E], F]) -> Result[T, F]:
        return self  # type: ignore

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return func(self.value)

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
        return self  # type: ignore


class Err(Result[T, E]):
    __slots__ = ("error",)

    def __init__(self, error: E) -> None:
        self.error = error

    def unwrap(self) -> T:
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        return default

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        return func(self.error)

    def expect(self, msg: str) -> T:
        raise ValueError(f"{msg}: {self.error}")

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def map(self, func: Callable[[T], U]) -> Result[U, E]:
        return self  # type: ignore

    def map_err(self, func: Callable[[E], F]) -> Result[T, F]:
        return Err(func(self.error))

    def and_then(self, func: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return self  # type: ignore

    def or_else(self, func: Callable[[E], Result[T, F]]) -> Result[T, F]:
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
