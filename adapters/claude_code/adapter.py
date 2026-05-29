"""Claude Code 适配器 — 最小可选附加适配器实现。"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, ClassVar

from adapters.base_adapter import BaseAdapter, redact_sensitive
from permission.engine import PermissionEngine
from permission.policy import DEFAULT_POLICY_RELATIVE_PATH, PermissionResult


class ClaudeCodeAdapter(BaseAdapter):
    """Claude Code optional platform adapter.

    This adapter is deliberately not part of the SuperMedicine core runtime. It
    provides discovery/capability metadata plus a permission-checked, timeout-
    bounded ``claude --print`` invocation path when a local Claude Code CLI is
    present. Missing local ``claude`` is therefore a stable optional-adapter
    unavailable condition, not a core failure.
    """

    SUPPORTED_TOOLS = {"claude.capabilities", "claude.runtime_status", "claude.invoke"}
    USER_FACING_AGENT = {"name": "SuperMedicine", "id": "supermedicine"}
    INTERNAL_ROLE_CONTEXTS = ["alpha", "beta", "gamma", "delta"]
    AI_PROVIDER_SUPPORT: ClassVar[dict[str, Any]] = {
        "config_sources": [
            "Installer/runtime injection flags: Install.py --provider openai|anthropic --base-url <url> --api-key <secret> --model <model>",
            "Generic environment variables: SM_LLM_PROVIDER, SM_LLM_BASE_URL, SM_LLM_API_KEY, SM_LLM_MODEL",
            "Provider environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY",
            "Project-local config: .supermedicine/config.yaml llm.provider and llm.providers.*",
        ],
        "supported_api_formats": {
            "openai": {
                "api_format": "openai",
                "default_base_url": "https://api.openai.com/v1",
                "provider_key_env": "OPENAI_API_KEY",
                "generic_key_env": "SM_LLM_API_KEY",
                "custom_base_url": True,
            },
            "anthropic": {
                "api_format": "anthropic",
                "default_base_url": "https://api.anthropic.com/v1",
                "provider_key_env": "ANTHROPIC_API_KEY",
                "generic_key_env": "SM_LLM_API_KEY",
                "custom_base_url": True,
            },
            "openrouter": {
                "api_format": "openai",
                "default_base_url": "https://openrouter.ai/api/v1",
                "provider_key_env": "OPENROUTER_API_KEY",
                "generic_key_env": "SM_LLM_API_KEY",
                "custom_base_url": True,
            },
        },
        "custom_base_url": True,
        "secret_redaction": {
            "required": True,
            "redacted_value": "<redacted>",
            "plain_text_keys_in_manifest_or_docs": False,
        },
        "boundary": (
            "Optional Claude Code platform surface; provider config is supplied by installer/runtime/project config "
            "for SuperMedicine/Claude Code invocation context and must never be embedded as plaintext keys."
        ),
    }

    def __init__(
        self,
        permission_engine: PermissionEngine | None = None,
        project_dir: Path | None = None,
        default_agent_id: str = "alpha",
        runtime_command: str = "claude",
        timeout_seconds: int = 30,
    ):
        super().__init__(permission_engine=permission_engine, project_dir=project_dir, default_agent_id=default_agent_id)
        self._project_dir = Path.cwd() if project_dir is None else Path(project_dir)
        self._default_agent_id = default_agent_id
        self._runtime_command = runtime_command
        self._timeout_seconds = timeout_seconds
        self._permission_engine = permission_engine

    @property
    def platform_name(self) -> str:
        return "claude-code"

    @property
    def registration(self) -> dict[str, Any]:
        """Return adapter discovery metadata for registries and callers."""
        return {
            "platform": self.platform_name,
            "adapter_class": self.__class__.__name__,
            "status": "optional_minimal",
            "optional": True,
            "core": False,
            "default": False,
            "module": "adapters.claude_code.adapter",
            "capability_tool": "claude.capabilities",
            "requires_core_runtime": False,
            "requires_local_runtime_for_invoke": True,
            "ai_provider_support": self.AI_PROVIDER_SUPPORT,
            "limitations": [
                "Optional minimal add-on; not imported, initialized, or probed by default.",
                "Invocation requires an explicitly selected adapter and local Claude Code CLI runtime.",
                "Only SuperMedicine is exposed as a user-facing platform agent; alpha/beta/gamma/delta are internal role contexts only.",
                "OpenAI/Anthropic provider config is injected by installer/runtime/project config; manifests and docs must not contain plaintext API keys.",
            ],
        }

    def capabilities(self) -> dict[str, Any]:
        """Report supported capabilities and current limits without exaggeration."""
        runtime = self._runtime_status()
        return {
            "platform": self.platform_name,
            "status": "available" if runtime["available"] else "runtime_unavailable",
            "adapter_status": "optional_minimal",
            "optional": True,
            "supported_tools": sorted(self.SUPPORTED_TOOLS),
            "features": {
                "registration_discovery": True,
                "capability_reporting": True,
                "permission_checked_calls": True,
                "runtime_discovery": True,
                "contract_invoke": True,
                "timeout_controls": True,
                "sensitive_redaction": True,
                "native_subagent_dispatch": False,
                "native_skill_load": False,
                "core_runtime_dependency": False,
                "ai_provider_config_discovery": True,
                "ai_provider_secret_redaction": True,
                "custom_ai_provider_base_url": True,
            },
            "ai_provider": self.AI_PROVIDER_SUPPORT,
            "user_facing_agents": [self.USER_FACING_AGENT],
            "internal_role_contexts": self.INTERNAL_ROLE_CONTEXTS,
            "resource_limits": {
                "default_timeout_seconds": self._timeout_seconds,
                "max_timeout_seconds": self.MAX_TIMEOUT_SECONDS,
                "permission_resource": "claude.invoke",
            },
            "limits": [
                "Minimal adapter only; not a full Claude Code sub-agent bridge.",
                "Claude Code support is an optional add-on and is not required for core SuperMedicine runtime.",
                "Actual invocation requires a local Claude Code CLI runtime on PATH.",
                "skill_load returns contract metadata; it does not load native Claude Code skills.",
                "subagent_dispatch reports unavailable until a stable native API exists.",
                "Claude Code exposes exactly one user-facing agent/surface: SuperMedicine; α/β/γ/δ remain non-user-facing role contexts.",
                "OpenAI and Anthropic provider settings are read from installer/runtime/project configuration declarations only; no plaintext API keys are stored in adapter docs or manifests.",
            ],
            "runtime": runtime,
        }

    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a minimal Claude Code adapter tool after policy approval."""
        if tool_id not in self.SUPPORTED_TOOLS:
            return {
                "status": "error",
                "tool": tool_id,
                "error": f"Unsupported Claude Code adapter tool: {redact_sensitive(tool_id)}",
                "error_code": "unsupported_tool",
                "supported_tools": sorted(self.SUPPORTED_TOOLS),
                "metadata": {"security": {"permission_checked": False, "reason": "unsupported_tool"}},
            }

        agent_id = params.get("agent_id", self._default_agent_id)
        denied = self._permission_denied(agent_id, "tool_call", tool_id)
        if denied is not None:
            denied["tool"] = tool_id
            return denied

        if tool_id == "claude.capabilities":
            return {"status": "ok", "tool": tool_id, "result": self.capabilities()}
        if tool_id == "claude.runtime_status":
            return {"status": "ok", "tool": tool_id, "result": self._runtime_status()}
        if tool_id == "claude.invoke":
            return self._invoke(params)
        return {"status": "error", "tool": tool_id, "error": "Unhandled Claude Code adapter tool."}

    def skill_load(self, skill_name: str) -> str:
        """Return contract metadata for Claude Code skill loading.

        Native Claude Code skill loading is intentionally not claimed as supported yet, but
        this method is a real permission-checked adapter response rather than Coming Soon.
        """
        denied = self._permission_denied(self._default_agent_id, "skill_load", skill_name)
        if denied is not None:
            return f"Permission denied loading Claude Code skill '{skill_name}': {denied['error']}"
        return (
            f"Claude Code skill '{skill_name}' is not natively loaded by SuperMedicine yet. "
            "Adapter capabilities are available via tool_call('claude.capabilities', ...)."
        )

    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """Report explicit unavailable state for native Claude Code sub-agent dispatch."""
        denied = self._permission_denied(agent_id, "execute", f"claude.subagent.{agent_id}")
        if denied is not None:
            denied["agent_id"] = agent_id
            return denied
        return {
            "agent_id": agent_id,
            "status": "unavailable",
            "platform": self.platform_name,
            "task": redact_sensitive(task),
            "error": "Native Claude Code sub-agent dispatch is not available in this minimal adapter.",
            "capabilities": redact_sensitive(self.capabilities()["features"]),
            "user_facing": False,
            "internal_role_context": agent_id in self.INTERNAL_ROLE_CONTEXTS,
        }

    def _invoke(self, params: dict[str, Any]) -> dict[str, Any]:
        prompt = params.get("prompt") or params.get("task") or ""
        if not isinstance(prompt, str) or not prompt.strip():
            return {"status": "error", "tool": "claude.invoke", "error": "Missing non-empty prompt.", "error_code": "invalid_input"}

        runtime = self._runtime_status()
        if not runtime["available"]:
            return {
                "status": "unavailable",
                "tool": "claude.invoke",
                "error": "Claude Code CLI runtime is unavailable; optional adapter invocation requires a local 'claude' command on PATH.",
                "error_code": "runtime_unavailable",
                "retryable": True,
                "runtime": runtime,
                "metadata": {
                    "adapter": {"optional": True, "core_failure": False},
                    "resource": {"kind": "local_cli", "timeout_seconds": self._timeout_seconds},
                },
            }

        timeout = self._normalize_timeout(params.get("timeout"), self._timeout_seconds)
        command = [runtime["command_path"], "--print", prompt]
        if params.get("dry_run", False):
            safe_command = redact_sensitive([runtime["command_path"], "--print", prompt])
            return {
                "status": "ok",
                "tool": "claude.invoke",
                "result": {"command": safe_command, "dry_run": True},
                "metadata": {"resource": {"timeout_seconds": timeout}, "security": {"permission_checked": True, "redacted": safe_command != command}},
            }

        try:
            result = subprocess.run(
                command,
                cwd=str(self._project_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "tool": "claude.invoke",
                "error": f"Timed out after {timeout:g}s.",
                "error_code": "timeout",
                "retryable": True,
                "metadata": {"resource": {"timeout_seconds": timeout, "kind": "local_cli"}},
            }
        except OSError as exc:
            return {
                "status": "runtime_error",
                "tool": "claude.invoke",
                "error": redact_sensitive(str(exc)),
                "error_code": "runtime_os_error",
                "retryable": True,
                "metadata": {"adapter": {"optional": True, "core_failure": False}, "resource": {"kind": "local_cli", "timeout_seconds": timeout}},
            }

        if result.returncode != 0:
            return {
                "status": "runtime_error",
                "tool": "claude.invoke",
                "error": redact_sensitive(result.stderr or f"Claude CLI exited with {result.returncode}."),
                "error_code": "runtime_error",
                "returncode": result.returncode,
                "metadata": {"resource": {"timeout_seconds": timeout, "kind": "local_cli"}},
            }
        return {
            "status": "ok",
            "tool": "claude.invoke",
            "result": redact_sensitive(result.stdout),
            "metadata": {"resource": {"timeout_seconds": timeout, "kind": "local_cli"}, "security": {"permission_checked": True}},
        }

    def _runtime_status(self) -> dict[str, Any]:
        command_path = shutil.which(self._runtime_command)
        return {
            "available": command_path is not None,
            "command": self._runtime_command,
            "command_path": command_path,
            "required_for_core": False,
            "unavailable_is_core_failure": False,
            "ai_provider_configured": {
                "supported_api_formats": sorted(self.AI_PROVIDER_SUPPORT["supported_api_formats"].keys()),
                "config_sources": self.AI_PROVIDER_SUPPORT["config_sources"],
                "secret_redaction_required": self.AI_PROVIDER_SUPPORT["secret_redaction"]["required"],
                "plaintext_api_keys_in_manifest_or_docs": self.AI_PROVIDER_SUPPORT["secret_redaction"]["plain_text_keys_in_manifest_or_docs"],
                "custom_base_url": self.AI_PROVIDER_SUPPORT["custom_base_url"],
            },
        }

    def _permission_denied(self, agent_id: str, action: str, resource: str) -> dict[str, Any] | None:
        engine = self._get_permission_engine_or_error()
        if isinstance(engine, dict):
            return engine
        result = engine.check(
            agent_id,
            action,
            resource,
            context={
                "adapter": self.platform_name,
                "policy_path": str(self._project_dir / DEFAULT_POLICY_RELATIVE_PATH),
            },
        )
        if result == PermissionResult.ALLOWED:
            return None
        return {
            "status": "denied",
            "platform": self.platform_name,
            "agent": agent_id,
            "action": action,
            "resource": resource,
            "error": "Permission denied by canonical policy chain.",
            "error_code": "permission_denied",
            "metadata": {
                "policy_path": str(self._project_dir / DEFAULT_POLICY_RELATIVE_PATH),
                "security": {"permission": "denied", "permission_checked": True},
            },
        }

    def _get_permission_engine_or_error(self) -> PermissionEngine | dict[str, Any]:
        if self._permission_engine is not None:
            return self._permission_engine
        policy_dir = self._project_dir / DEFAULT_POLICY_RELATIVE_PATH.parent
        try:
            self._permission_engine = PermissionEngine(policy_dir, policy_dir / "audit.jsonl")
        except Exception as exc:
            return {
                "status": "configuration_error",
                "platform": self.platform_name,
                "error": f"Unable to load canonical permission policy: {exc}",
                "metadata": {"policy_path": str(policy_dir / DEFAULT_POLICY_RELATIVE_PATH.name)},
            }
        return self._permission_engine
