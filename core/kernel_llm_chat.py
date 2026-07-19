"""Extracted LLM chat helpers for the SuperMedicine kernel.

Standalone functions that were previously private methods on ``Kernel``.
The Kernel class delegates to these functions so that the logic can be
unit-tested and composed independently of the full kernel instance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, cast

from core.config_center import ConfigCenter
from core.experiment_protocols import build_experiment_llm_context
from core.llm_client import LLMClient
from core.llm_manager import LLMConfigManager
from core.redaction import redact_sensitive
from core.workspace_tools import WorkspaceToolService, build_tool_authoring_llm_context

from core.kernel_constants import MEDICAL_BOUNDARY, SUPERMEDICINE_SYSTEM_PROMPT


def workspace_tool_runtime_context(workspace_id: str, config_path) -> dict[str, Any]:
    """Return currently imported workspace tools for LLM context when available."""

    from pathlib import Path

    if not workspace_id:
        return {"workspace_id": "", "tools": {}, "error": "no_workspace_selected"}
    try:
        return {
            "workspace_id": workspace_id,
            "tools": WorkspaceToolService(Path(config_path).parent.parent).list_tools(
                workspace_id
            ),
        }
    except Exception as exc:
        return {"workspace_id": workspace_id, "tools": {}, "error": str(exc)}


def llm_runtime_context(
    llm_manager: LLMConfigManager, config: ConfigCenter
) -> dict[str, Any]:
    """Expose secret-safe LLM runtime state to plugin/task paths."""
    provider = llm_manager.get_current_provider(redacted=True)
    provider_name = (
        str(provider.get("provider") or config.get_llm_runtime_provider_name() or "")
        if provider
        else ""
    )
    validation_error = (
        llm_manager.validate_provider(
            provider_name, config.get_llm_provider_config(provider_name)
        )
        if provider_name
        else None
    )
    if not provider or validation_error is not None:
        return {
            "configured": False,
            "error": validation_error.get("error")
            if validation_error is not None
            else {
                "code": "missing_provider",
                "message": LLMConfigManager.SETUP_HINT,
            },
        }
    return {
        "configured": True,
        "provider": provider.get("provider", provider_name),
        "config": provider,
    }


def llm_chat_messages(
    task: str,
    config: ConfigCenter,
    config_path,
    rag_context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build the canonical LLM chat message list for standalone Kernel chat."""
    selected_protocol = config.get_selected_experiment_protocol()
    experiment_context = build_experiment_llm_context(selected_protocol or None)
    tool_authoring_context = build_tool_authoring_llm_context()
    runtime_state = config.get_runtime_state()
    tool_authoring_context["runtime_tools"] = workspace_tool_runtime_context(
        str(runtime_state.get("last_workspace_id") or ""), config_path
    )
    last_tool_import = runtime_state.get("last_tool_import", {})
    tool_authoring_context["imported_tools"] = (
        last_tool_import.get("tools", []) if isinstance(last_tool_import, dict) else []
    )
    runtime_context = {
        "config_path": str(config.config_path),
        "config_load_error": config.diagnostics().get("load_error", ""),
        "current_view": runtime_state.get("current_view"),
        "selected_experiment_protocol": selected_protocol,
        "permission_mode": config.get_file_access_config().get("mode"),
        "permission_mode_label": config.get_permission_mode_label(),
        "authorized_external_roots": config.get_file_access_config().get(
            "authorized_external_roots", []
        ),
        "last_tool_import": last_tool_import,
    }
    messages = [
        {"role": "system", "content": SUPERMEDICINE_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": "Experiment context and authoring rules:\n"
            + json.dumps(experiment_context, ensure_ascii=False, sort_keys=True),
        },
        {
            "role": "system",
            "content": "Unified runtime configuration state:\n"
            + json.dumps(runtime_context, ensure_ascii=False, sort_keys=True),
        },
        {
            "role": "system",
            "content": "Python/R workspace tool authoring rules:\n"
            + json.dumps(tool_authoring_context, ensure_ascii=False, sort_keys=True),
        },
    ]
    evidence_context = rag_context or {
        "enabled": True,
        "status": "empty",
        "sources": [],
    }
    messages.append(
        {
            "role": "system",
            "content": (
                "Retrieved evidence. Cite only these sources; do not invent sources. "
                "When sources are empty, state that local evidence is unavailable and "
                "do not make unsupported medical factual claims:\n"
                + json.dumps(evidence_context, ensure_ascii=False, sort_keys=True)
            ),
        }
    )
    messages.append({"role": "user", "content": task})
    return messages


_MISSING = object()


@dataclass(slots=True)
class _ChatExecution:
    task: str
    task_id: str
    agent_id: str
    llm_manager: LLMConfigManager
    config: ConfigCenter
    config_path: Any
    checkpoint: Callable[..., None]
    progress: Callable[[dict[str, Any]], None] | None
    rag_context: dict[str, Any] | None

    def emit(self, kind: str, message: str = "", **payload: Any) -> None:
        if self.progress is not None:
            self.progress({"kind": kind, "message": message, **payload})

    def metadata(self) -> dict[str, Any]:
        return {
            "medical_boundary": MEDICAL_BOUNDARY,
            "llm": llm_runtime_context(self.llm_manager, self.config),
            "rag": self.rag_context or {"enabled": True, "status": "empty"},
        }

    def fail(
        self,
        error: Any,
        reason: str,
        *,
        status: str = "llm_error",
        response: Any = _MISSING,
        checkpoint_output: Any = _MISSING,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = {
            "status": status,
            "task": self.task,
            "agent": self.agent_id,
            "plugin": None,
            "action": "llm.chat",
            "output": None,
            "error": error,
            "metadata": metadata or self.metadata(),
        }
        if response is not _MISSING:
            result["llm_response"] = response
        checkpoint_args = {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "state": "failed",
            "task": self.task,
            "plugin": None,
            "action": "llm.chat",
            "error": error,
            "recoverable": True,
            "not_recoverable_reason": reason,
        }
        if checkpoint_output is not _MISSING:
            checkpoint_args["output"] = checkpoint_output
        self.checkpoint(**checkpoint_args)
        return result


def _stream_chat(
    stream_method: Callable[..., Any],
    messages: list[dict[str, str]],
    execution: _ChatExecution,
) -> dict[str, Any]:
    execution.emit("assistant_start", "")
    execution.emit("status", "正在接收回复。")
    parts: list[str] = []
    thinking_parts: list[str] = []
    thinking_done = False
    response_metadata: dict[str, Any] = {}
    excluded = {
        "delta",
        "content",
        "text",
        "reasoning_content",
        "thinking",
        "reasoning",
    }
    for chunk in stream_method(messages):
        delta = ""
        if isinstance(chunk, dict):
            if chunk.get("error"):
                response_metadata = chunk
                break
            thinking_delta = str(
                chunk.get("reasoning_content")
                or chunk.get("thinking")
                or chunk.get("reasoning")
                or ""
            )
            if thinking_delta and not thinking_done:
                thinking_parts.append(thinking_delta)
                execution.emit(
                    "thinking_content", thinking_delta, content=thinking_delta
                )
            delta = str(
                chunk.get("delta") or chunk.get("content") or chunk.get("text") or ""
            )
            if delta and thinking_parts and not thinking_done:
                execution.emit("thinking_done", "")
                thinking_done = True
            response_metadata.update(
                {key: value for key, value in chunk.items() if key not in excluded}
            )
        else:
            delta = str(chunk or "")
        if delta:
            parts.append(delta)
            execution.emit("assistant_delta", delta, content=delta)
    if thinking_parts and not thinking_done:
        execution.emit("thinking_done", "")
    if response_metadata.get("error"):
        return response_metadata
    return {"content": "".join(parts), **response_metadata}


def _request_chat(client: LLMClient, execution: _ChatExecution) -> Any:
    messages = llm_chat_messages(
        execution.task,
        execution.config,
        execution.config_path,
        execution.rag_context,
    )
    execution.emit("status", "已发送请求，等待模型返回。")
    stream_method = getattr(client, "chat_stream", None)
    if callable(stream_method):
        return _stream_chat(stream_method, messages, execution)
    return client.chat(messages)


def _complete_chat(response: Any, execution: _ChatExecution) -> dict[str, Any]:
    if not isinstance(response, dict):
        error = {
            "code": "malformed_llm_response",
            "message": "LLM provider returned a non-dict response",
        }
        return execution.fail(
            error,
            "Configured LLM provider returned a malformed response.",
            response={"type": type(response).__name__},
        )
    if response.get("error"):
        return execution.fail(
            response["error"],
            "Configured LLM provider returned an error.",
            response=response,
            checkpoint_output=response,
        )
    content = str(response.get("content") or "").strip()
    if not content:
        error = {
            "code": "empty_llm_response",
            "message": "LLM provider returned an empty response",
        }
        return execution.fail(
            error,
            "Configured LLM provider returned no content.",
            response=response,
            checkpoint_output=response,
        )
    result = {
        "status": "success",
        "task": execution.task,
        "agent": execution.agent_id,
        "plugin": None,
        "action": "llm.chat",
        "output": content,
        "result": content,
        "error": None,
        "llm_response": response,
        "metadata": execution.metadata(),
    }
    execution.checkpoint(
        task_id=execution.task_id,
        agent_id=execution.agent_id,
        state="completed",
        task=execution.task,
        plugin=None,
        action="llm.chat",
        output=result,
        recoverable=False,
    )
    return result


def execute_llm_chat(
    task: str,
    *,
    task_id: str,
    agent_id: str,
    llm_manager: LLMConfigManager,
    config: ConfigCenter,
    config_path: Any,
    checkpoint_task_fn: Callable[..., None],
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    rag_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an unmatched natural-language task through the configured LLM."""
    execution = _ChatExecution(
        task, task_id, agent_id, llm_manager, config, config_path,
        checkpoint_task_fn, progress_callback, rag_context,
    )
    execution.emit(
        "reasoning",
        "模型正在处理请求；当前 Provider 未暴露完整思考内容，仅显示合规处理进度。",
    )
    client_or_error = llm_manager.create_client()
    if not isinstance(client_or_error, LLMClient):
        error = (
            client_or_error.get("error", client_or_error)
            if isinstance(client_or_error, dict)
            else str(client_or_error)
        )
        return execution.fail(
            error,
            "LLM provider must be configured before chat execution can proceed.",
            status="llm_configuration_error",
            metadata={
                "medical_boundary": MEDICAL_BOUNDARY,
                "llm": {"configured": False, "error": error},
            },
        )
    try:
        response = _request_chat(client_or_error, execution)
    except Exception as exc:
        error = cast(
            dict[str, Any],
            redact_sensitive(
                {
                    "code": "provider_chat_exception",
                    "message": str(exc.__class__.__name__),
                    "detail": str(exc),
                }
            ),
        )
        return execution.fail(
            error,
            "Configured LLM provider raised an exception during chat execution.",
        )
    return _complete_chat(response, execution)
