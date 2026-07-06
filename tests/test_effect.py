"""Unit tests for the Effect monadic container."""

from __future__ import annotations

import pytest

from core.effect import Effect


@pytest.mark.parametrize(
    "value",
    [
        42,
        "hello",
        None,
        {"key": [1, 2, 3]},
    ],
)
def test_succeed_values_are_successful(value):
    eff = Effect.succeed(value)

    assert eff.is_success() is True
    assert eff.is_failure() is False
    assert eff.value == value
    assert eff.error is None


@pytest.mark.parametrize(
    "error",
    [
        "oops",
        ValueError("bad value"),
        {"code": 500, "message": "server error"},
    ],
)
def test_fail_values_are_failures(error):
    eff = Effect.fail(error)

    assert eff.is_failure() is True
    assert eff.is_success() is False
    assert eff.value is None
    if isinstance(error, Exception):
        assert eff.error is error
    else:
        assert eff.error == error


def test_from_callable_success_failure_and_custom_error_handler():
    counter = {"n": 0}

    def increment():
        counter["n"] += 1
        return counter["n"]

    def handler(exc: Exception) -> dict:
        return {"type": type(exc).__name__, "msg": str(exc)}

    success = Effect.from_callable(lambda: 10 * 2)
    none_return = Effect.from_callable(lambda: None)
    side_effect = Effect.from_callable(increment)
    failure = Effect.from_callable(lambda: 1 / 0)
    handled_failure = Effect.from_callable(
        lambda: int("not_a_number"),
        error_handler=handler,
    )

    assert success.is_success() is True
    assert success.value == 20
    assert none_return.is_success() is True
    assert none_return.value is None
    assert side_effect.is_success() is True
    assert side_effect.value == 1
    assert failure.is_failure() is True
    assert "division" in str(failure.error).lower()
    assert handled_failure.is_failure() is True
    assert handled_failure.error["type"] == "ValueError"


def test_map_transforms_success_chains_and_propagates_failures():
    mapped = Effect.succeed(5).map(lambda x: x * 3)
    transformed = Effect.succeed(42).map(str)
    chained = Effect.succeed(2).map(lambda x: x + 3).map(lambda x: x * 10)
    failed = Effect.fail("err").map(lambda x: x * 3)

    assert mapped.is_success() is True
    assert mapped.value == 15
    assert transformed.value == "42"
    assert chained.value == 50
    assert failed.is_failure() is True
    assert failed.error == "err"


def test_map_function_exceptions_propagate():
    with pytest.raises(ZeroDivisionError):
        Effect.succeed(0).map(lambda x: 1 / x)


def test_flat_map_success_failure_chain_and_type_composition():
    def safe_divide(x: int) -> Effect:
        if x == 0:
            return Effect.fail("division by zero")
        return Effect.succeed(100 // x)

    success = Effect.succeed(10).flat_map(lambda x: Effect.succeed(x + 5))
    success_to_failure = Effect.succeed(10).flat_map(lambda x: Effect.fail("nope"))
    failure = Effect.fail("original").flat_map(lambda x: Effect.succeed(99))
    chain_success = Effect.succeed(5).flat_map(safe_divide)
    chain_failure = Effect.succeed(0).flat_map(safe_divide)
    typed = Effect.succeed("hello").flat_map(lambda s: Effect.succeed(len(s)))

    assert success.is_success() is True
    assert success.value == 15
    assert success_to_failure.is_failure() is True
    assert success_to_failure.error == "nope"
    assert failure.is_failure() is True
    assert failure.error == "original"
    assert chain_success.value == 20
    assert chain_failure.is_failure() is True
    assert typed.value == 5


@pytest.mark.parametrize(
    ("effect", "default", "expected"),
    [
        (Effect.succeed(42), 0, 42),
        (Effect.fail("err"), 0, 0),
        (Effect.fail("err"), None, None),
        (Effect.succeed("hello"), "default", "hello"),
        (Effect.fail("err"), "default", "default"),
    ],
)
def test_get_or_else_returns_value_or_default(effect, default, expected):
    assert effect.get_or_else(default) == expected


def test_predicates_are_mutually_exclusive_for_successes_and_failures():
    assert Effect.succeed(1).is_success() is True
    assert Effect.succeed(1).is_failure() is False
    assert Effect.fail("err").is_failure() is True
    assert Effect.fail("err").is_success() is False

    for value in [0, 1, "", "abc", [], [1], None, True, False]:
        success = Effect.succeed(value)
        failure = Effect.fail(value)

        assert success.is_success() != success.is_failure()
        assert failure.is_success() != failure.is_failure()


@pytest.mark.parametrize(
    ("effect", "attribute", "value"),
    [
        (Effect.succeed(1), "value", 2),
        (Effect.fail("err"), "error", "new"),
        (Effect.succeed(1), "success", False),
    ],
)
def test_effect_is_immutable(effect, attribute, value):
    with pytest.raises(AttributeError):
        setattr(effect, attribute, value)
