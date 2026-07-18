from __future__ import annotations

import json
import shutil
from typing import Any
from unittest.mock import patch

import yaml
import pytest

from core.kernel import Kernel
from core.runtime_capabilities import RuntimeInvariantError
from core.kernel_constants import SUPERMEDICINE_SYSTEM_PROMPT
from core.kernel_llm_chat import execute_llm_chat
from core.llm_client import LLMClient
from core.llm_manager import LLMConfigManager
from plugins.rag.providers import LocalRAGProvider
from permission.engine import PermissionEngine
from permission.policy import PermissionResult
from permission.prompt_generator import PromptGenerator


# ═══ Kernel Tests ═══


class TestKernel:
    def _create_kernel(self, tmp_path):
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"project": "test"}), encoding="utf-8"
        )
        (tmp_path / "plugins").mkdir()
        (tmp_path / "policies").mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )
        return Kernel(
            config_path=tmp_path / "config.yaml",
            plugins_dir="plugins",
            policies_dir=tmp_path / "policies",
        )

    def test_init(self, tmp_path):
        assert self._create_kernel(tmp_path) is not None

    def test_config(self, tmp_path):
        assert self._create_kernel(tmp_path).config.get("project") == "test"

    def test_plugin_registry(self, tmp_path):
        assert self._create_kernel(tmp_path).plugin_registry is not None

    def test_event_bus(self, tmp_path):
        assert self._create_kernel(tmp_path).event_bus is not None

    def test_identical_tasks_receive_unique_execution_ids(self, tmp_path, monkeypatch):
        kernel = self._create_kernel(tmp_path)

        def capture_task_id(task, *, task_id, **kwargs):
            return {"status": "success", "task_id": task_id}

        monkeypatch.setattr(kernel, "_execute_llm_chat", capture_task_id)

        first = kernel.execute_task("repeatable task")
        second = kernel.execute_task("repeatable task")

        assert first["task_id"] != second["task_id"]

    def test_kernel_permission_engine_is_runtime_gate_not_prompt_generator(
        self, tmp_path
    ):
        kernel = self._create_kernel(tmp_path)

        assert isinstance(kernel.permission_engine, PermissionEngine)
        assert not isinstance(kernel.permission_engine, PromptGenerator)

    def test_execute_task_always_returns_finalized_harness_metadata(
        self, tmp_path, monkeypatch
    ):
        class Client(LLMClient):
            def chat(self, messages, **kwargs):
                return {"content": "ok"}

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(kernel.llm_manager, "create_client", lambda: Client())
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        result = kernel.execute_task("ordinary medical question")

        assert result["metadata"]["harness"]["participated"] is True
        assert result["metadata"]["harness"]["finalized"] is True
        assert result["run_id"]
        checkpoints = kernel.checkpoint_manager.base_dir / result["run_id"]
        states = [
            json.loads(path.read_text(encoding="utf-8"))["state"]
            for path in checkpoints.glob("step-*/status.json")
        ]
        assert sum(state in {"completed", "failed"} for state in states) == 1

    def test_execute_task_fails_closed_when_harness_cannot_begin(self, tmp_path, monkeypatch):
        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(
            kernel._harness_runtime,
            "begin",
            lambda **kwargs: (_ for _ in ()).throw(OSError("checkpoint unavailable")),
        )

        result = kernel.execute_task("ordinary medical question")

        assert result["status"] == "harness_unavailable"
        assert result["metadata"]["harness"]["participated"] is False

    def test_execute_task_fails_closed_when_harness_cannot_finalize(
        self, tmp_path, monkeypatch
    ):
        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(
            kernel._harness_runtime,
            "finalize",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("finalize unavailable")),
        )

        result = kernel.execute_task("ordinary medical question")

        assert result["status"] == "harness_unavailable"
        assert result["metadata"]["harness"]["finalized"] is False

    def test_llm_chat_retrieves_local_rag_context_without_retrieval_keywords(
        self, tmp_path, monkeypatch
    ):
        LocalRAGProvider(tmp_path / ".supermedicine" / "rag" / "local").add_document(
            "Hypertension evidence supports lifestyle and pharmacologic treatment.",
            {"source": "local-fixture", "title": "Evidence note"},
        )
        captured = {}

        class Client(LLMClient):
            def chat(self, messages, **kwargs):
                captured["messages"] = messages
                return {"content": "ok"}

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(kernel.llm_manager, "create_client", lambda: Client())
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        result = kernel.execute_task("What evidence supports hypertension care?")

        assert result["metadata"]["rag"]["status"] == "used"
        assert any(
            "Hypertension evidence" in message["content"]
            for message in captured["messages"]
            if message["role"] == "system"
        )

    def test_llm_chat_uses_selected_workspace_rag_index(self, tmp_path, monkeypatch):
        workspace = tmp_path / "workspaces" / "trial"
        LocalRAGProvider(workspace / ".supermedicine" / "rag" / "local").add_document(
            "Workspace-specific ACEI evidence.",
            {"source": "workspace-paper"},
        )
        captured = {}

        class Client(LLMClient):
            def chat(self, messages, **kwargs):
                captured["messages"] = messages
                return {"content": "ok"}

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(kernel.llm_manager, "create_client", lambda: Client())
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(kernel.llm_manager, "validate_provider", lambda *args: None)

        result = kernel.execute_task(
            "What is the ACEI evidence?",
            params={"_workspace": {"id": "trial", "path": str(workspace)}},
        )

        assert result["metadata"]["rag"]["status"] == "used"
        assert result["metadata"]["sources"][0]["source"] == "workspace-paper"

    def test_deterministic_plugin_records_enumerated_rag_skip(self, tmp_path):
        kernel = self._create_kernel(tmp_path)

        result = kernel.execute_task(
            "describe values",
            plugin_name="python-stats",
            action="python.stats.describe",
            params={"values": [1, 2, 3]},
        )

        assert result["metadata"]["rag"] == {
            "enabled": True,
            "status": "skipped",
            "skip_reason": "deterministic_plugin",
        }
        assert result["metadata"]["permission"]["checked"] is True

    def test_llm_chat_fails_closed_when_local_rag_index_is_corrupt(
        self, tmp_path, monkeypatch
    ):
        index_dir = tmp_path / ".supermedicine" / "rag" / "local"
        index_dir.mkdir(parents=True)
        (index_dir / "documents.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(RuntimeInvariantError) as captured:
            self._create_kernel(tmp_path)

        assert captured.value.code == "rag_index_corrupt"

    def test_empty_rag_context_explicitly_forbids_invented_sources(
        self, tmp_path, monkeypatch
    ):
        captured = {}

        class Client(LLMClient):
            def chat(self, messages, **kwargs):
                captured["messages"] = messages
                return {"content": "Local evidence is unavailable."}

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(kernel.llm_manager, "create_client", lambda: Client())
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(kernel.llm_manager, "validate_provider", lambda *args: None)

        result = kernel.execute_task("What evidence supports treatment?")

        assert result["metadata"]["rag"]["status"] == "empty"
        evidence_messages = [
            item["content"]
            for item in captured["messages"]
            if item["role"] == "system" and "evidence" in item["content"].lower()
        ]
        assert any("do not invent" in message.lower() for message in evidence_messages)

    def test_multi_agent_execution_uses_same_rag_and_harness_pipeline(self, tmp_path):
        LocalRAGProvider(tmp_path / ".supermedicine" / "rag" / "local").add_document(
            "Hypertension cohort evidence.",
            {"source": "local-fixture", "title": "Cohort note"},
        )
        kernel = self._create_kernel(tmp_path)

        result = kernel.execute_task(
            "Summarize hypertension evidence", use_agent_chain=True
        )

        assert result["status"] == "success", result
        assert result["metadata"]["rag"]["status"] == "used"
        assert result["metadata"]["agent_mode"] == "multi"
        assert result["metadata"]["harness"]["finalized"] is True
        audit_entries = [
            json.loads(line)
            for line in (tmp_path / "policies" / "audit.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        assert {
            entry["agent_id"]
            for entry in audit_entries
            if entry["action"] == "plan"
        } == {"delta", "alpha", "beta", "gamma"}

    def test_agents_config_defaults_to_single_and_can_select_multi(self, tmp_path):
        kernel = self._create_kernel(tmp_path)
        kernel.config.set("agents", {"mode": "multi"})
        kernel.config.save()

        result = kernel.execute_task("Summarize hypertension evidence")

        assert result["status"] == "success"
        assert result["metadata"]["agent_mode"] == "multi"
        assert result["metadata"]["harness"]["finalized"] is True

    def test_explicit_single_override_wins_over_multi_config(self, tmp_path, monkeypatch):
        kernel = self._create_kernel(tmp_path)
        kernel.config.set("agents", {"mode": "multi"})
        kernel.config.save()
        monkeypatch.setattr(
            kernel,
            "_execute_agent_chain",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("multi executor must not run")
            ),
        )

        result = kernel.execute_task(
            "deterministic task",
            plugin_name="python-stats",
            action="python.stats.describe",
            params={"values": [1, 2, 3]},
            use_agent_chain=False,
        )

        assert result["metadata"]["agent_mode"] == "single"

    def test_multi_agent_permission_denial_is_structured_and_finalized(
        self, tmp_path, monkeypatch
    ):
        kernel = self._create_kernel(tmp_path)
        original_check = kernel.permission_engine.check

        def deny_beta(agent_id, action, resource, context=None):
            if agent_id == "beta" and action == "plan":
                return PermissionResult.DENIED
            return original_check(agent_id, action, resource, context)

        monkeypatch.setattr(kernel.permission_engine, "check", deny_beta)

        result = kernel.execute_task("Summarize evidence", use_agent_chain=True)

        assert result["status"] == "denied"
        assert result["metadata"]["harness"]["finalized"] is True
        assert result["error"]["code"] == "agent_permission_denied"

    def test_llm_chat_provider_exception_returns_structured_error_and_checkpoint(
        self, tmp_path, monkeypatch
    ):
        class ExplodingClient(LLMClient):
            def chat(self, messages, **kwargs):
                raise RuntimeError("provider failed api_key=sk-kernel-secret")

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(
            kernel.llm_manager, "create_client", lambda: ExplodingClient()
        )
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        result = kernel.execute_task("unmatched natural language")

        assert result["status"] == "llm_error"
        assert result["action"] == "llm.chat"
        assert result["error"]["code"] == "provider_chat_exception"
        assert "sk-kernel-secret" not in str(result)
        assert list((tmp_path / "checkpoints").rglob("status.json"))

    def test_llm_chat_injects_supermedicine_system_prompt_before_user_message(
        self, tmp_path, monkeypatch
    ):
        captured = {}

        class CapturingClient(LLMClient):
            def chat(self, messages, **kwargs):
                captured["messages"] = messages
                return {
                    "content": "I am SuperMedicine, the SuperMedicine project assistant."
                }

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(
            kernel.llm_manager, "create_client", lambda: CapturingClient()
        )
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        result = kernel.execute_task("你是谁？")

        assert result["status"] == "success"
        assert (
            result["output"]
            == "I am SuperMedicine, the SuperMedicine project assistant."
        )
        assert "ChatGPT" not in result["output"]
        assert captured["messages"][0]["role"] == "system"
        assert "SuperMedicine" in captured["messages"][0]["content"]
        assert "project assistant" in captured["messages"][0]["content"]
        assert (
            "prototype/interface-stage research assistance"
            in captured["messages"][0]["content"]
        )
        assert "runtime wiring" in captured["messages"][0]["content"]
        assert captured["messages"][0]["content"] == SUPERMEDICINE_SYSTEM_PROMPT
        assert captured["messages"][1]["role"] == "system"
        assert (
            "Experiment context and authoring rules"
            in captured["messages"][1]["content"]
        )
        assert captured["messages"][2]["role"] == "system"
        assert (
            "Unified runtime configuration state" in captured["messages"][2]["content"]
        )
        assert captured["messages"][3]["role"] == "system"
        assert (
            "Python/R workspace tool authoring rules"
            in captured["messages"][3]["content"]
        )
        assert "plugins/tools/<tool-directory>/" in captured["messages"][3]["content"]
        assert "tool.yaml" in captured["messages"][3]["content"]
        assert (
            "workspaces/<workspace-id>/tools/python/<tool-id>/"
            in captured["messages"][3]["content"]
        )
        assert (
            "workspaces/<workspace-id>/tools/r/<tool-id>/"
            in captured["messages"][3]["content"]
        )
        assert "Retrieved evidence" in captured["messages"][4]["content"]
        assert captured["messages"][-1] == {"role": "user", "content": "你是谁？"}

    def test_llm_chat_system_prompt_preserves_permission_generator_boundary(
        self, tmp_path
    ):
        kernel = self._create_kernel(tmp_path)
        messages = kernel._llm_chat_messages("你的职责是什么？")

        assert messages[0]["role"] == "system"
        assert (
            "advisory prompt text is not a substitute for runtime permission checks"
            in messages[0]["content"]
        )
        assert "PromptGenerator" not in messages[0]["content"]
        assert "PermissionEngine" not in messages[0]["content"]
        assert messages[1]["role"] == "system"
        assert "Experiment context and authoring rules" in messages[1]["content"]
        assert messages[2]["role"] == "system"
        assert "Unified runtime configuration state" in messages[2]["content"]
        assert messages[3]["role"] == "system"
        assert "Python/R workspace tool authoring rules" in messages[3]["content"]
        assert "scan_validate_import_flow" in messages[3]["content"]
        assert "Retrieved evidence" in messages[4]["content"]
        assert messages[-1] == {"role": "user", "content": "你的职责是什么？"}

    def test_llm_chat_context_injects_selected_experiment_permission_and_tools(
        self, tmp_path
    ):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "project": "test",
                    "file_access": {"mode": "full", "full_mode_confirmed": True},
                    "runtime_state": {
                        "current_view": "permission",
                        "selected_experiment_protocol": "cell_culture_basic",
                        "last_workspace_id": "trial-1",
                        "last_tool_import": {
                            "workspace_id": "trial-1",
                            "tools": [
                                {
                                    "language": "python",
                                    "id": "python-stats",
                                    "name": "Python stats",
                                }
                            ],
                        },
                    },
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (tmp_path / "plugins").mkdir()
        (tmp_path / "policies").mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )
        kernel = Kernel(
            config_path=config_path,
            plugins_dir="plugins",
            policies_dir=tmp_path / "policies",
        )

        messages = kernel._llm_chat_messages("根据当前配置说明下一步")
        experiment_context = messages[1]["content"]
        runtime_context = messages[2]["content"]
        tool_context = messages[3]["content"]

        assert "cell_culture_basic" in experiment_context
        assert "western_blot_basic" in experiment_context
        assert "full" in runtime_context
        assert "完全访问" in runtime_context
        assert "permission" in runtime_context
        assert "trial-1" in runtime_context
        assert "python-stats" in runtime_context
        assert "python-stats" in tool_context
        assert "Retrieved evidence" in messages[4]["content"]
        assert messages[-1] == {"role": "user", "content": "根据当前配置说明下一步"}


class TestKernelProgressCallback:
    """Verify Kernel.execute_task emits progress_callback events."""

    def test_execute_task_emits_status_events(self, tmp_path, monkeypatch):
        """Kernel should emit 'status' kind events during task execution."""
        kernel = TestKernel()._create_kernel(tmp_path)
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

        monkeypatch.setattr(kernel.llm_manager, "create_client", lambda: FakeClient())
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

    def test_execute_task_emits_reasoning_event_before_llm_stream(
        self, tmp_path, monkeypatch
    ):
        """A 'reasoning' event must be emitted before any streaming events."""
        kernel = TestKernel()._create_kernel(tmp_path)
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

        monkeypatch.setattr(kernel.llm_manager, "create_client", lambda: FakeClient())
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
        assert "status" in kinds
        assert "reasoning" in kinds
        reasoning_idx = kinds.index("reasoning")
        if "assistant_start" in kinds:
            start_idx = kinds.index("assistant_start")
            assert reasoning_idx < start_idx

    def test_execute_task_no_callback_does_not_raise(self, tmp_path, monkeypatch):
        """No progress_callback should not raise errors."""
        kernel = TestKernel()._create_kernel(tmp_path)

        class FakeClient(LLMClient):
            def chat(self, messages, **kwargs):
                return {"content": "result", "model": "test"}

            def complete(self, prompt, **kwargs):
                return {"content": "result", "model": "test"}

            def chat_stream(self, messages, **kwargs):
                yield {"delta": "result", "model": "test"}

        monkeypatch.setattr(kernel.llm_manager, "create_client", lambda: FakeClient())
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


# ═══ Kernel LLM Chat Tests ═══


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tests — basic streaming
# ---------------------------------------------------------------------------

class TestExecuteLLMChatStream:
    """Verify progress_callback events during streaming chat."""

    def test_stream_emits_assistant_start_before_deltas(self):
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

    def test_stream_emits_all_content_deltas(self):
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

    def test_stream_joins_deltas_into_final_output(self):
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

    def test_stream_without_callback_does_not_raise(self):
        """No progress_callback → must complete without error."""
        chunks = [{"delta": "ok", "model": "m"}]
        result, _ = _run_execute(chunks, progress_callback=None)
        assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Tests — thinking / reasoning content
# ---------------------------------------------------------------------------

class TestExecuteLLMChatStreamThinking:
    """Verify thinking_content and thinking_done events."""

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

        # thinking_content arrives before assistant_delta
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


# ---------------------------------------------------------------------------
# Tests — error handling in stream
# ---------------------------------------------------------------------------

class TestExecuteLLMChatStreamError:
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


# ---------------------------------------------------------------------------
# Tests — no chat_stream fallback
# ---------------------------------------------------------------------------

class TestExecuteLLMChatNoStream:
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


# ---------------------------------------------------------------------------
# Tests — initial reasoning event
# ---------------------------------------------------------------------------

class TestExecuteLLMChatInitialReasoning:
    """The very first event emitted is always a 'reasoning' kind."""

    def test_first_event_is_reasoning(self):
        chunks = [{"delta": "Hi", "model": "m"}]
        events, cb = _collect_events()
        _run_execute(chunks, progress_callback=cb)

        assert len(events) >= 2  # at least reasoning + assistant_start
        assert events[0]["kind"] == "reasoning"
