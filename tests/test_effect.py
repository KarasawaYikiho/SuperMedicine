"""Unit tests for the Effect monadic container."""

from __future__ import annotations

from core.effect import Effect


class TestEffectSucceed:
    """Tests for Effect.succeed factory."""

    def test_succeed_returns_success(self):
        eff = Effect.succeed(42)
        assert eff.is_success() is True
        assert eff.is_failure() is False

    def test_succeed_contains_value(self):
        eff = Effect.succeed("hello")
        assert eff.value == "hello"

    def test_succeed_error_is_none(self):
        eff = Effect.succeed(1)
        assert eff.error is None

    def test_succeed_with_none_value(self):
        eff = Effect.succeed(None)
        assert eff.is_success() is True
        assert eff.value is None

    def test_succeed_with_complex_value(self):
        data = {"key": [1, 2, 3]}
        eff = Effect.succeed(data)
        assert eff.value == data


class TestEffectFail:
    """Tests for Effect.fail factory."""

    def test_fail_returns_failure(self):
        eff = Effect.fail("oops")
        assert eff.is_failure() is True
        assert eff.is_success() is False

    def test_fail_contains_error(self):
        eff = Effect.fail("something broke")
        assert eff.error == "something broke"

    def test_fail_value_is_none(self):
        eff = Effect.fail("err")
        assert eff.value is None

    def test_fail_with_exception_as_error(self):
        err = ValueError("bad value")
        eff = Effect.fail(err)
        assert eff.error is err

    def test_fail_with_dict_error(self):
        err = {"code": 500, "message": "server error"}
        eff = Effect.fail(err)
        assert eff.error == err


class TestEffectFromCallable:
    """Tests for Effect.from_callable factory."""

    def test_success_case(self):
        eff = Effect.from_callable(lambda: 10 * 2)
        assert eff.is_success() is True
        assert eff.value == 20

    def test_failure_on_exception(self):
        eff = Effect.from_callable(lambda: 1 / 0)
        assert eff.is_failure() is True
        assert "division" in str(eff.error).lower()

    def test_custom_error_handler(self):
        def handler(exc: Exception) -> dict:
            return {"type": type(exc).__name__, "msg": str(exc)}

        eff = Effect.from_callable(lambda: int("not_a_number"), error_handler=handler)
        assert eff.is_failure() is True
        assert eff.error["type"] == "ValueError"

    def test_callable_with_side_effect_returning_value(self):
        counter = {"n": 0}

        def increment():
            counter["n"] += 1
            return counter["n"]

        eff = Effect.from_callable(increment)
        assert eff.is_success() is True
        assert eff.value == 1

    def test_from_callable_with_none_return(self):
        eff = Effect.from_callable(lambda: None)
        assert eff.is_success() is True
        assert eff.value is None


class TestEffectMap:
    """Tests for Effect.map combinator."""

    def test_map_on_success(self):
        eff = Effect.succeed(5).map(lambda x: x * 3)
        assert eff.is_success() is True
        assert eff.value == 15

    def test_map_on_failure_propagates(self):
        eff = Effect.fail("err").map(lambda x: x * 3)
        assert eff.is_failure() is True
        assert eff.error == "err"

    def test_map_transforms_type(self):
        eff = Effect.succeed(42).map(str)
        assert eff.value == "42"

    def test_map_chain(self):
        eff = (
            Effect.succeed(2)
            .map(lambda x: x + 3)
            .map(lambda x: x * 10)
        )
        assert eff.value == 50

    def test_map_with_exception_in_function(self):
        # map does NOT catch exceptions; they propagate
        eff = Effect.succeed(0)
        try:
            eff.map(lambda x: 1 / x)
            assert False, "Should have raised ZeroDivisionError"
        except ZeroDivisionError:
            pass


class TestEffectFlatMap:
    """Tests for Effect.flat_map (monadic bind)."""

    def test_flat_map_on_success_returns_effect(self):
        eff = Effect.succeed(10).flat_map(lambda x: Effect.succeed(x + 5))
        assert eff.is_success() is True
        assert eff.value == 15

    def test_flat_map_on_success_to_failure(self):
        eff = Effect.succeed(10).flat_map(lambda x: Effect.fail("nope"))
        assert eff.is_failure() is True
        assert eff.error == "nope"

    def test_flat_map_on_failure_propagates(self):
        eff = Effect.fail("original").flat_map(lambda x: Effect.succeed(99))
        assert eff.is_failure() is True
        assert eff.error == "original"

    def test_flat_map_chain(self):
        def safe_divide(x: int) -> Effect:
            if x == 0:
                return Effect.fail("division by zero")
            return Effect.succeed(100 // x)

        eff = Effect.succeed(5).flat_map(safe_divide)
        assert eff.value == 20

        eff2 = Effect.succeed(0).flat_map(safe_divide)
        assert eff2.is_failure() is True

    def test_flat_map_composes_different_types(self):
        eff = Effect.succeed("hello").flat_map(
            lambda s: Effect.succeed(len(s))
        )
        assert eff.value == 5


class TestEffectGetOrElse:
    """Tests for Effect.get_or_else."""

    def test_get_or_else_on_success(self):
        eff = Effect.succeed(42)
        assert eff.get_or_else(0) == 42

    def test_get_or_else_on_failure(self):
        eff = Effect.fail("err")
        assert eff.get_or_else(0) == 0

    def test_get_or_else_with_none_default(self):
        eff = Effect.fail("err")
        assert eff.get_or_else(None) is None

    def test_get_or_else_preserves_type(self):
        eff = Effect.succeed("hello")
        assert eff.get_or_else("default") == "hello"

        eff2 = Effect.fail("err")
        assert eff2.get_or_else("default") == "default"


class TestEffectPredicates:
    """Tests for is_success / is_failure predicates."""

    def test_success_is_not_failure(self):
        eff = Effect.succeed(1)
        assert eff.is_success() is True
        assert eff.is_failure() is False

    def test_failure_is_not_success(self):
        eff = Effect.fail("err")
        assert eff.is_failure() is True
        assert eff.is_success() is False

    def test_predicate_mutual_exclusion(self):
        for val in [0, 1, "", "abc", [], [1], None, True, False]:
            succ = Effect.succeed(val)
            assert succ.is_success() != succ.is_failure()

            fail = Effect.fail(val)
            assert fail.is_success() != fail.is_failure()


class TestEffectFrozen:
    """Verify Effect is immutable (frozen dataclass)."""

    def test_cannot_set_value(self):
        eff = Effect.succeed(1)
        try:
            eff.value = 2  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_cannot_set_error(self):
        eff = Effect.fail("err")
        try:
            eff.error = "new"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_cannot_set_success(self):
        eff = Effect.succeed(1)
        try:
            eff.success = False  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass
