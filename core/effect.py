"""Functional error handling container inspired by Effect-TS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Effect(Generic[T, E]):
    """Functional error handling container inspired by Effect-TS.

    Effect is a monadic container that represents either a successful value
    or a failure with an error. It provides functional combinators for
    composing operations that may fail.

    Example usage::

        result = Effect.succeed(42)
        assert result.is_success()
        assert result.get_or_else(0) == 42

        result = Effect.fail("something went wrong")
        assert result.is_failure()
        assert result.get_or_else(0) == 0

        # Using from_callable to wrap exceptions
        result = Effect.from_callable(lambda: 1 / 0)
        assert result.is_failure()
    """

    success: bool
    value: T | None = None
    error: E | None = None

    @staticmethod
    def succeed(value: T) -> Effect[T, Any]:
        """Create a successful Effect containing the given value."""
        return Effect(success=True, value=value)

    @staticmethod
    def fail(error: E) -> Effect[Any, E]:
        """Create a failed Effect containing the given error."""
        return Effect(success=False, error=error)

    @staticmethod
    def from_callable(
        fn: Callable[[], T],
        error_handler: Callable[[Exception], E] | None = None,
    ) -> Effect[T, E]:
        """Execute a callable and wrap the result in an Effect.

        If the callable raises an exception, it is caught and wrapped in a
        failed Effect. An optional error_handler can transform the exception
        before storing it.
        """
        try:
            return Effect.succeed(fn())
        except Exception as e:
            handler = error_handler or (lambda exc: str(exc))
            return Effect.fail(handler(e))

    def map(self, f: Callable[[T], Any]) -> Effect[Any, E]:
        """Apply a function to the value if successful, propagating failures."""
        if self.success:
            return Effect.succeed(f(self.value))
        return self  # type: ignore[return-value]

    def flat_map(self, f: Callable[[T], Effect[Any, E]]) -> Effect[Any, E]:
        """Apply a function that returns an Effect to the value if successful.

        This is the monadic bind operation, allowing composition of
        effectful operations.
        """
        if self.success:
            return f(self.value)
        return self  # type: ignore[return-value]

    def get_or_else(self, default: T) -> T:
        """Return the value if successful, otherwise return the default."""
        if self.success:
            return self.value  # type: ignore[return-value]
        return default

    def is_success(self) -> bool:
        """Check if this Effect represents a success."""
        return self.success

    def is_failure(self) -> bool:
        """Check if this Effect represents a failure."""
        return not self.success
