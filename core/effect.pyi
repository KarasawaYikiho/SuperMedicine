"""Type stub for core.effect module."""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")

class Effect(Generic[T, E]):
    """Functional error handling container inspired by Effect-TS."""

    success: bool
    value: T | None
    error: E | None

    def __init__(
        self,
        success: bool,
        value: T | None = ...,
        error: E | None = ...,
    ) -> None: ...

    @staticmethod
    def succeed(value: T) -> Effect[T, Any]:
        """Create a successful Effect containing the given value."""
        ...

    @staticmethod
    def fail(error: E) -> Effect[Any, E]:
        """Create a failed Effect containing the given error."""
        ...

    @staticmethod
    def from_callable(
        fn: Callable[[], T],
        error_handler: Callable[[Exception], E] | None = ...,
    ) -> Effect[T, E]:
        """Execute a callable and wrap the result in an Effect."""
        ...

    def map(self, f: Callable[[T], Any]) -> Effect[Any, E]:
        """Apply a function to the value if successful, propagating failures."""
        ...

    def flat_map(self, f: Callable[[T], Effect[Any, E]]) -> Effect[Any, E]:
        """Apply a function that returns an Effect to the value if successful."""
        ...

    def get_or_else(self, default: T) -> T:
        """Return the value if successful, otherwise return the default."""
        ...

    def is_success(self) -> bool:
        """Check if this Effect represents a success."""
        ...

    def is_failure(self) -> bool:
        """Check if this Effect represents a failure."""
        ...
