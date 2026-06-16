"""Tests for Kernel progress callback — DBG-BUG-004."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import yaml
import shutil

from core.kernel import Kernel
from core.kernel_llm_chat import execute_llm_chat
from core.llm_client import LLMClient
from core.llm_manager import LLMConfigManager
from permission.engine import PermissionEngine


# ═══ Helpers ═══


class StreamClient(LLMClient):
    """Minimal LLMClient that exposes ``chat_stream`` returning a fixed sequence."""

    def __init__(self, chunks: list[dict[str, Any] | str]) -> None:
        self._chunks = chunks

    def chat(self, messages, **kwargs):
        return {"content": "fallback", "model": "test-model"}

    def complete(self, prompt, **kwargs):
        return {"content": "fallback", "model": "test-model"}

    def chat_stream(self, messages, **kwargs):
        for chunk in self._chunks:
            yield chunk


def _fake_config():
    """Return a minimal ConfigCenter stand-in with required methods."""
    from types import SimpleNamespace

    return SimpleNamespace(
        config_path="/tmp/fake/config.yaml",
        get_selected_experiment_protocol=lambda: None,
        get_runtime_state=lambda: {},
        get_file_access_config=lambda: {"mode": "full", "authorized_external_ropts": []},
        get_permission_mode_label=lambda: "完全访问",
        diagnostics=lambda: {"load_error": ""},
        get=lambda key, default=None: default,
        get_llm_runtime_provider_name=lambda: "test-provider",
        get_llm_provider_config=lambda name: {"api_format": "openai"},
    )


def _run_execute(
    chunks: list[dict[str, Any] | str],
    *,
    progress_callback=None,
):
    """Run ``execute_llm_chat`` with a StreamClient yielding *chunks*."""
    client = StreamClient(chunks)

    class FakeManager(LLMConfigManager):
        def __init__(self):
            pass  # Skip parent init

        def create_client(self):
            return client

        def get_current_provider(self, redacted=False):
            return {"provider": "test-provider"}

        def validate_provider(self, name, config):
            return None

    checkpoint_calls: list[dict[str, Any]] = []

    with patch(
        "core.kernel_llm_chat.llm_chat_messages",
        return_value=[{"role": "user", "content": "hello"}],
    ):
        result = execute_llm_chat(
            task="hello",
            task_id="t1",
            agent_id="a1",
            llm_manager=FakeManager(),
            config=_fake_config(),
            config_path="/tmp/fake/config.yaml",
            checkpoint_task_fn=lambda **kw: checkpoint_calls.append(kw),
            progress_callback=progress_callback,
        )

    return result, checkpoint_calls


def _collect_events() -> tuple[list[dict[str, Any]], Any]:
    """Return (events_list, callback_fn) that records every emitted event."""
    events: list[dict[str, Any]] = []

    def callback(event: dict[str, Any]) -> None:
        events.append(event)

    return events, callback


def _create_kernel(tmp_path):
    """Create a fully initialized Kernel with temp directories."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"project": "test"}), encoding="utf-8")
    (tmp_path / "plugins").mkdir()
    (tmp_path / "policies").mkdir()
    shutil.copyfile(
        PermissionEngine.default_policy_path(),
        tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
    )
    return Kernel(
        config_path=config_path,
        plugins_dir=tmp_path / "plugins",
        policies_dir=tmp_path / "policies",
    )


# ═══ Kernel Progress Callback Tests ═══


class TestKernelProgressCallback:
    """Verify Kernel.execute_task emits progress_callback events."""

    def test_execute_task_emits_status_events(self, tmp_path, monkeypatch):
        """Kernel should emit 'status' kind events during task execution."""
        kernel = _create_kernel(tmp_path)
        events: list[dict[str, Any]] = []

        def callback(event: dict[str, Any]) -> None:
            events.append(event)

        class FakeClient(LLMClient):
            def chat(self, messages, **kwargs):
                return {"content": "result", "model": "test"}

            def complete(self, prompt, **kwargs):
                return {"content": "result", "model": "test"}

            def chat_stream(self, messages, **kwargs):
                yield {"delta": "result", "model": "test"}

        monkeypatch.setattr(
            kernel.llm_manager, "create_client", lambda: FakeClient()
        )
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        result = kernel.execute_task("test task", progress_callback=callback)

        assert result["status"] == "success"
        kinds = [e["kind"] for e in events]
        assert "status" in kinds
        assert "reasoning" in kinds

    def test_execute_task_emits_reasoning_event_before_llm_stream(self, tmp_path, monkeypatch):
        """A 'reasoning' event must be emitted before any streaming events."""
        kernel = _create_kernel(tmp_path)
        events: list[dict[str, Any]] = []

        def callback(event: dict[str, Any]) -> None:
            events.append(event)

        class FakeClient(LLMClient):
            def chat(self, messages, **kwargs):
                return {"content": "result", "model": "test"}

            def complete(self, prompt, **kwargs):
                return {"content": "result", "model": "test"}

            def chat_stream(self, messages, **kwargs):
                yield {"delta": "result", "model": "test"}

        monkeypatch.setattr(
            kernel.llm_manager, "create_client", lambda: FakeClient()
        )
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        kernel.execute_task("test task", progress_callback=callback)

        kinds = [e["kind"] for e in events]
        # Kernel emits 'status' first (dispatch), then 'reasoning' before streaming
        assert "status" in kinds
        assert "reasoning" in kinds
        reasoning_idx = kinds.index("reasoning")
        # reasoning must come before assistant_start (streaming begins)
        if "assistant_start" in kinds:
            start_idx = kinds.index("assistant_start")
            assert reasoning_idx < start_idx

    def test_execute_task_no_callback_does_not_raise(self, tmp_path, monkeypatch):
        """No progress_callback should not raise errors."""
        kernel = _create_kernel(tmp_path)

        class FakeClient(LLMClient):
            def chat(self, messages, **kwargs):
                return {"content": "result", "model": "test"}

            def complete(self, prompt, **kwargs):
                return {"content": "result", "model": "test"}

            def chat_stream(self, messages, **kwargs):
                yield {"delta": "result", "model": "test"}

        monkeypatch.setattr(
            kernel.llm_manager, "create_client", lambda: FakeClient()
        )
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        result = kernel.execute_task("test task", progress_callback=None)

        assert result["status"] == "success"


# ═══ Streaming Progress Events Tests ═══


class TestStreamingProgressEvents:
    """Verify progress_callback events during streaming LLM chat."""

    def test_emits_assistant_start_before_deltas(self):
        """assistant_start must arrive before any assistant_delta."""
        chunks = [
            {"delta": "Hello", "model": "m"},
            {"delta": " world", "model": "m"},
        ]
        events, cb = _collect_events()
        result, _ = _run_execute(chunks, progress_callback=cb)

        assert result["status"] == "success"
        kinds = [e["kind"] for e in events]
        assert "assistant_start" in kinds
        start_idx = kinds.index("assistant_start")
        delta_indices = [i for i, k in enumerate(kinds) if k == "assistant_delta"]
        assert all(i > start_idx for i in delta_indices)

    def test_emits_all_content_deltas(self):
        """Every non-empty delta from the stream should reach the callback."""
        chunks = [
            {"delta": "A", "model": "m"},
            {"delta": "B", "model": "m"},
            {"delta": "C", "model": "m"},
        ]
        events, cb = _collect_events()
        result, _ = _run_execute(chunks, progress_callback=cb)

        assert result["status"] == "success"
        delta_events = [e for e in events if e["kind"] == "assistant_delta"]
        assert [e["content"] for e in delta_events] == ["A", "B", "C"]

    def test_joins_deltas_into_final_output(self):
        """Result content must be the concatenation of all deltas."""
        chunks = [
            {"delta": "foo", "model": "m"},
            {"delta": "bar", "model": "m"},
        ]
        _, cb = _collect_events()
        result, _ = _run_execute(chunks, progress_callback=cb)

        assert result["output"] == "foobar"

    def test_stream_with_string_chunks(self):
        """Non-dict chunks (plain strings) should still produce deltas."""
        chunks = ["alpha", "beta"]
        events, cb = _collect_events()
        result, _ = _run_execute(chunks, progress_callback=cb)

        assert result["status"] == "success"
        delta_events = [e for e in events if e["kind"] == "assistant_delta"]
        assert [e["content"] for e in delta_events] == ["alpha", "beta"]


# ═══ Thinking/Reasoning Content Events Tests ═══


class TestThinkingProgressEvents:
    """Verify thinking_content and thinking_done events during streaming."""

    def test_thinking_content_emitted_before_assistant_delta(self):
        """reasoning_content deltas should produce thinking_content events."""
        chunks = [
            {"reasoning_content": "Let me think...", "model": "m"},
            {"delta": "The answer is 42.", "model": "m"},
        ]
        events, cb = _collect_events()
        result, _ = _run_execute(chunks, progress_callback=cb)

        assert result["status"] == "success"
        kinds = [e["kind"] for e in events]

        assert "thinking_content" in kinds
        assert "assistant_delta" in kinds
        thinking_idx = kinds.index("thinking_content")
        first_delta_idx = kinds.index("assistant_delta")
        assert thinking_idx < first_delta_idx

    def test_thinking_done_emitted_on_transition_to_content(self):
        """When thinking transitions to regular content, thinking_done fires."""
        chunks = [
            {"reasoning_content": "step 1", "model": "m"},
            {"reasoning_content": " step 2", "model": "m"},
            {"delta": "Final answer.", "model": "m"},
        ]
        events, cb = _collect_events()
        _run_execute(chunks, progress_callback=cb)

        kinds = [e["kind"] for e in events]
        assert "thinking_done" in kinds
        thinking_done_idx = kinds.index("thinking_done")
        first_delta_idx = kinds.index("assistant_delta")
        assert thinking_done_idx < first_delta_idx

    def test_thinking_content_uses_thinking_key_fallback(self):
        """The 'thinking' key is accepted as thinking content."""
        chunks = [
            {"thinking": "pondering...", "model": "m"},
            {"delta": "Result", "model": "m"},
        ]
        events, cb = _collect_events()
        _run_execute(chunks, progress_callback=cb)

        thinking_events = [e for e in events if e["kind"] == "thinking_content"]
        assert len(thinking_events) >= 1
        assert thinking_events[0]["content"] == "pondering..."

    def test_thinking_content_uses_reasoning_key_fallback(self):
        """The 'reasoning' key is accepted as thinking content."""
        chunks = [
            {"reasoning": "analysing...", "model": "m"},
            {"delta": "Result", "model": "m"},
        ]
        events, cb = _collect_events()
        _run_execute(chunks, progress_callback=cb)

        thinking_events = [e for e in events if e["kind"] == "thinking_content"]
        assert len(thinking_events) >= 1
        assert thinking_events[0]["content"] == "analysing..."

    def test_thinking_only_stream_emits_thinking_done_at_end(self):
        """If the stream is pure thinking with no regular content,
        thinking_done must still be emitted (post-loop guard)."""
        chunks = [
            {"reasoning_content": "only thinking", "model": "m"},
        ]
        events, cb = _collect_events()
        result, _ = _run_execute(chunks, progress_callback=cb)

        kinds = [e["kind"] for e in events]
        assert "thinking_done" in kinds

    def test_no_thinking_events_when_no_reasoning_content(self):
        """Pure content stream must not emit thinking_content or thinking_done."""
        chunks = [
            {"delta": "Plain answer.", "model": "m"},
        ]
        events, cb = _collect_events()
        _run_execute(chunks, progress_callback=cb)

        kinds = [e["kind"] for e in events]
        assert "thinking_content" not in kinds
        assert "thinking_done" not in kinds


# ═══ Error Stream Events Tests ═══


class TestErrorStreamEvents:
    """Verify error chunk handling during streaming."""

    def test_error_chunk_stops_stream_and_returns_error(self):
        """An error dict in the stream should halt processing."""
        chunks = [
            {"delta": "Partial...", "model": "m"},
            {"error": {"code": "rate_limit", "message": "Too many requests"}},
        ]
        events, cb = _collect_events()
        result, _ = _run_execute(chunks, progress_callback=cb)

        assert result["status"] == "llm_error"
        assert result["error"]["code"] == "rate_limit"

    def test_error_chunk_emits_partial_deltas_before_error(self):
        """Deltas emitted before the error chunk should still reach callback."""
        chunks = [
            {"delta": "OK", "model": "m"},
            {"error": {"code": "timeout", "message": "timed out"}},
        ]
        events, cb = _collect_events()
        _run_execute(chunks, progress_callback=cb)

        delta_events = [e for e in events if e["kind"] == "assistant_delta"]
        assert len(delta_events) >= 1
        assert delta_events[0]["content"] == "OK"


# ═══ Non-streaming Fallback Tests ═══


class TestNonStreamingFallback:
    """When client has no chat_stream, fall back to non-streaming chat()."""

    def test_fallback_to_chat_when_no_stream_method(self):
        """LLMClient base provides a default chat_stream that wraps chat().
        To exercise the non-streaming branch the client shadows chat_stream
        with None so getattr returns None → falls through to chat()."""

        class NoStreamClient(LLMClient):
            chat_stream = None  # type: ignore[assignment]

            def chat(self, messages, **kwargs):
                return {"content": "non-stream response", "model": "m"}

            def complete(self, prompt, **kwargs):
                return {"content": "", "model": "m"}

        class NoStreamManager:
            def create_client(self):
                return NoStreamClient()

            def get_current_provider(self, redacted=False):
                return {"provider": "test-provider"}

            def validate_provider(self, name, config):
                return None

        events, cb = _collect_events()

        with patch(
            "core.kernel_llm_chat.llm_chat_messages",
            return_value=[{"role": "user", "content": "hi"}],
        ):
            result = execute_llm_chat(
                task="hi",
                task_id="t2",
                agent_id="a2",
                llm_manager=NoStreamManager(),
                config=_fake_config(),
                config_path="/tmp/fake/config.yaml",
                checkpoint_task_fn=lambda **kw: None,
                progress_callback=cb,
            )

        assert result["status"] == "success"
        assert result["output"] == "non-stream response"
        # No assistant_start or assistant_delta in non-stream path
        kinds = [e["kind"] for e in events]
        assert "assistant_start" not in kinds
        assert "assistant_delta" not in kinds

    def test_client_creation_error_returns_config_error(self):
        """When create_client returns a dict, status should be llm_configuration_error."""

        class BrokenManager:
            def create_client(self):
                return {"error": {"code": "missing_api_key", "message": "No key"}}

        events, cb = _collect_events()

        with patch(
            "core.kernel_llm_chat.llm_chat_messages",
            return_value=[{"role": "user", "content": "hi"}],
        ):
            result = execute_llm_chat(
                task="hi",
                task_id="t3",
                agent_id="a3",
                llm_manager=BrokenManager(),
                config=_fake_config(),
                config_path="/tmp/fake/config.yaml",
                checkpoint_task_fn=lambda **kw: None,
                progress_callback=cb,
            )

        assert result["status"] == "llm_configuration_error"
