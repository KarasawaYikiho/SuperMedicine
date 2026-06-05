"""SuperMedicine 微内核 — 集成所有核心组件"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from agents.checkpoint import CheckpointManager
from core.config_center import ConfigCenter
from core.event_bus import EventBus
from core.llm_client import LLMClient
from core.llm_manager import LLMConfigManager
from core.plugin_registry import PluginRegistry
from core.redaction import redact_sensitive
from core.session_manager import SessionManager
from permission.engine import PermissionEngine
from permission.policy import DEFAULT_POLICY_RELATIVE_PATH, PermissionResult


MEDICAL_BOUNDARY = (
    "Current-stage SuperMedicine output: not production/clinical medical advice; "
    "requires expert review before any research, regulatory, or clinical use."
)


SUPERMEDICINE_SYSTEM_PROMPT = """You are SuperMedicine, the project assistant for the SuperMedicine medical research platform.

Identity and scope:
- When asked who you are, what project you belong to, or what your responsibilities are, answer as SuperMedicine and describe your role in the SuperMedicine project.
- Help with medical research workflows: evidence synthesis, RAG-assisted literature work, statistical analysis support, manuscript/reporting-guideline assistance, citations, and permission-audited workflow coordination.
- Be clear that outputs are prototype/interface-stage research assistance, not production clinical advice, regulatory certification, diagnosis, or treatment.

Operating boundaries:
- Do not reveal hidden runtime wiring, internal adapter details, private policy mechanics, secrets, or implementation-only role documents.
- Do not claim capabilities beyond the configured SuperMedicine runtime, declared tools, and available plugins.
- Preserve permission and safety boundaries: advisory prompt text is not a substitute for runtime permission checks.
- Require human expert review before medical, research, regulatory, or clinical use.

Answer style:
- Be concise, transparent, and project-focused.
- Prefer practical research-assistant wording over generic model self-description.
- If a request is outside SuperMedicine's scope, state the boundary and offer safe project-relevant alternatives."""


class Kernel:
    """SuperMedicine 微内核"""

    def __init__(
        self,
        config_path: Path | None = None,
        plugins_dir: Path | None = None,
        policies_dir: Path | None = None,
    ):
        import os

        # SM_CONFIG 环境变量覆盖配置路径
        if config_path is None:
            env_config = os.environ.get("SM_CONFIG")
            if env_config:
                config_path = Path(env_config)

        self._config_path = config_path or Path(".supermedicine/config.yaml")
        self._plugins_dir = plugins_dir or Path("plugins")
        self._policies_dir = policies_dir or DEFAULT_POLICY_RELATIVE_PATH.parent

        self._config = ConfigCenter(self._config_path)
        self._llm_manager = LLMConfigManager(self._config)
        self._event_bus = EventBus()
        self._plugin_registry = PluginRegistry(self._plugins_dir)
        self._session_manager = SessionManager()
        self._checkpoint_manager = CheckpointManager(
            self._config_path.parent / "checkpoints"
        )

        # P0 权限引擎集成
        audit_log_path = self._policies_dir / "audit.jsonl"
        self._permission_engine = PermissionEngine(
            self._policies_dir,
            audit_log_path,
        )

    @property
    def config(self) -> ConfigCenter:
        return self._config

    @property
    def llm_manager(self) -> LLMConfigManager:
        return self._llm_manager

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def plugin_registry(self) -> PluginRegistry:
        return self._plugin_registry

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def permission_engine(self) -> PermissionEngine:
        """P0 运行时权限引擎。

        Kernel execution is hard-gated by PermissionEngine.check() against the
        code-layer policy and hard_limits. PromptGenerator is advisory/context
        generation only and is not invoked here as a runtime veto layer.
        """
        return self._permission_engine

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        return self._checkpoint_manager

    def _checkpoint_task(
        self,
        *,
        task_id: str,
        agent_id: str,
        state: str,
        task: str,
        plugin: str | None,
        action: str | None,
        output: Any = None,
        error: Any = None,
        recoverable: bool | None = None,
        not_recoverable_reason: str | None = None,
    ) -> None:
        latest = self._checkpoint_manager.get_latest_step(task_id) or 0
        self._checkpoint_manager.save(
            task_id=task_id,
            step=latest + 1,
            state=state,
            status=state,
            agent_id=agent_id,
            input_data={"task": task, "plugin": plugin, "action": action},
            output_data=output
            if isinstance(output, dict)
            else {"output": output}
            if output is not None
            else None,
            error=error,
            recoverable=recoverable,
            not_recoverable_reason=not_recoverable_reason,
            result=output if isinstance(output, dict) else {},
        )

    def execute_task(
        self,
        task: str,
        plugin_name: str | None = None,
        action: str | None = None,
        params: dict[str, Any] | None = None,
        agent_id: str = "alpha",
    ) -> dict[str, Any]:
        """执行用户任务或医疗插件，返回结构化结果。

        Kernel 是插件生产执行的唯一入口：先使用 PermissionEngine 检查
        ``execute`` 权限，再调用插件，并把所有插件结果转换为稳定的
        ``status/task/agent/plugin/action/output/error/metadata`` 形状。
        """
        self._plugin_registry.discover()
        task_id = (
            f"kernel-{abs(hash((task, plugin_name, action, agent_id))) & 0xFFFFFFFF:x}"
        )
        selected_plugin = plugin_name
        selected_action = action

        self._checkpoint_task(
            task_id=task_id,
            agent_id=agent_id,
            state="dispatch",
            task=task,
            plugin=selected_plugin,
            action=selected_action,
            recoverable=True,
        )

        if selected_plugin is None or selected_action is None:
            selected_plugin, selected_action = self._select_plugin_action(task)

        if selected_plugin is None or selected_action is None:
            result = self._execute_llm_chat(task, task_id=task_id, agent_id=agent_id)
            return result

        self._checkpoint_task(
            task_id=task_id,
            agent_id=agent_id,
            state="running",
            task=task,
            plugin=selected_plugin,
            action=selected_action,
            recoverable=True,
        )

        execution_context = {
            "task": task,
            "agent_id": agent_id,
            "plugin": selected_plugin,
            "action": selected_action,
            "llm": self._llm_runtime_context(),
            "permission_engine": self._permission_engine,
            "policy_path": str(
                self._policies_dir / self._permission_engine.DEFAULT_POLICY_FILENAME
            ),
            "resource": {
                "kind": "plugin",
                "plugin": selected_plugin,
                "action": selected_action,
            },
            "security": {"permission_entrypoint": "kernel", "permission_checked": True},
        }
        if selected_plugin == "rag-interface" and selected_action == "rag.query":
            provider_name = str(
                (params or {}).get("provider")
                or (params or {}).get("provider_type")
                or "local"
            ).lower()
            if provider_name == "pubmed":
                execution_context["requires_network"] = True
                execution_context["requires_external_api"] = True
                execution_context["external_resource"] = (
                    "https://eutils.ncbi.nlm.nih.gov/*"
                )

        permission = self._permission_engine.check(
            agent_id,
            "execute",
            selected_action,
            context=execution_context,
        )
        if permission == PermissionResult.DENIED:
            result = {
                "status": "denied",
                "task": task,
                "agent": agent_id,
                "plugin": selected_plugin,
                "action": selected_action,
                "output": None,
                "error": "Permission denied by canonical policy chain.",
                "reason": "Permission denied by canonical policy chain.",
                "metadata": {
                    "medical_boundary": MEDICAL_BOUNDARY,
                    "permission": "denied",
                    "security": {"permission_checked": True, "permission": "denied"},
                    "resource": execution_context["resource"],
                },
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=selected_plugin,
                action=selected_action,
                error=result["error"],
                recoverable=False,
                not_recoverable_reason="Permission denied by canonical policy chain.",
            )
            return result

        plugin = self._plugin_registry.get(selected_plugin)
        if plugin is None:
            result = {
                "status": "missing_plugin",
                "task": task,
                "plugin": selected_plugin,
                "action": selected_action,
                "output": None,
                "error": f"Plugin not found: {selected_plugin}",
                "metadata": {"medical_boundary": MEDICAL_BOUNDARY},
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=selected_plugin,
                action=selected_action,
                error=result["error"],
                recoverable=False,
                not_recoverable_reason="Selected plugin is not installed or discoverable.",
            )
            return result

        try:
            plugin_result = plugin.execute(
                selected_action, params or {}, execution_context
            )
        except Exception as exc:
            result = {
                "status": "plugin_error",
                "task": task,
                "plugin": selected_plugin,
                "action": selected_action,
                "output": None,
                "error": str(exc),
                "metadata": {"medical_boundary": MEDICAL_BOUNDARY},
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=selected_plugin,
                action=selected_action,
                error=result["error"],
                recoverable=False,
                not_recoverable_reason="Plugin raised an exception; manual review required before retry.",
            )
            return result

        metadata = (
            cast(dict[str, Any], plugin_result.get("metadata"))
            if isinstance(plugin_result.get("metadata"), dict)
            else {}
        )
        if "medical_boundary" not in metadata:
            metadata["medical_boundary"] = plugin_result.get(
                "medical_boundary", MEDICAL_BOUNDARY
            )
        if "statistics_boundary" not in metadata and plugin_result.get(
            "statistics_boundary"
        ):
            metadata["statistics_boundary"] = plugin_result.get("statistics_boundary")
        metadata.setdefault("resource", execution_context["resource"])
        security = metadata.get("security")
        if not isinstance(security, dict):
            security = {}
            metadata["security"] = security
        security.setdefault("permission_checked", True)
        security.setdefault("permission", "allowed")
        security.setdefault("permission_entrypoint", "kernel")

        if plugin_result.get("status") not in (None, "success"):
            result = {
                "status": "plugin_error",
                "task": task,
                "plugin": selected_plugin,
                "action": selected_action,
                "output": None,
                "error": plugin_result.get("error")
                or plugin_result.get("message")
                or "Plugin returned error status.",
                "plugin_result": plugin_result,
                "metadata": metadata,
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=selected_plugin,
                action=selected_action,
                output=plugin_result,
                error=result["error"],
                recoverable=False,
                not_recoverable_reason="Plugin returned an error status.",
            )
            return result

        output = plugin_result.get("output", plugin_result.get("result", plugin_result))
        result = {
            "status": "success",
            "task": task,
            "agent": agent_id,
            "plugin": selected_plugin,
            "action": selected_action,
            "output": output,
            "result": output,
            "error": None,
            "metadata": metadata,
            "medical_boundary": metadata.get("medical_boundary", MEDICAL_BOUNDARY),
            "statistics_boundary": metadata.get("statistics_boundary"),
        }
        self._checkpoint_task(
            task_id=task_id,
            agent_id=agent_id,
            state="completed",
            task=task,
            plugin=selected_plugin,
            action=selected_action,
            output=result,
            recoverable=False,
        )
        return result

    def _llm_runtime_context(self) -> dict[str, Any]:
        """Expose secret-safe LLM runtime state to plugin/task paths."""
        provider = self._llm_manager.get_current_provider(redacted=True)
        provider_name = (
            str(
                provider.get("provider")
                or self._config.get_llm_runtime_provider_name()
                or ""
            )
            if provider
            else ""
        )
        validation_error = (
            self._llm_manager.validate_provider(
                provider_name, self._config.get_llm_provider_config(provider_name)
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

    def _execute_llm_chat(
        self, task: str, *, task_id: str, agent_id: str
    ) -> dict[str, Any]:
        """Execute an unmatched natural-language task through the configured LLM."""
        client_or_error = self._llm_manager.create_client()
        if not isinstance(client_or_error, LLMClient):
            error = (
                client_or_error.get("error", client_or_error)
                if isinstance(client_or_error, dict)
                else str(client_or_error)
            )
            result: dict[str, Any] = {
                "status": "llm_configuration_error",
                "task": task,
                "agent": agent_id,
                "plugin": None,
                "action": "llm.chat",
                "output": None,
                "error": error,
                "metadata": {
                    "medical_boundary": MEDICAL_BOUNDARY,
                    "llm": {"configured": False, "error": error},
                },
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=None,
                action="llm.chat",
                error=error,
                recoverable=True,
                not_recoverable_reason="LLM provider must be configured before chat execution can proceed.",
            )
            return result

        try:
            response = client_or_error.chat(self._llm_chat_messages(task))
        except Exception as exc:
            error = {
                "code": "provider_chat_exception",
                "message": str(exc.__class__.__name__),
                "detail": str(exc),
            }
            safe_error = cast(dict[str, Any], redact_sensitive(error))
            result = {
                "status": "llm_error",
                "task": task,
                "agent": agent_id,
                "plugin": None,
                "action": "llm.chat",
                "output": None,
                "error": safe_error,
                "metadata": {
                    "medical_boundary": MEDICAL_BOUNDARY,
                    "llm": self._llm_runtime_context(),
                },
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=None,
                action="llm.chat",
                error=safe_error,
                recoverable=True,
                not_recoverable_reason="Configured LLM provider raised an exception during chat execution.",
            )
            return result
        if not isinstance(response, dict):
            error = {
                "code": "malformed_llm_response",
                "message": "LLM provider returned a non-dict response",
            }
            result = {
                "status": "llm_error",
                "task": task,
                "agent": agent_id,
                "plugin": None,
                "action": "llm.chat",
                "output": None,
                "error": error,
                "llm_response": {"type": type(response).__name__},
                "metadata": {
                    "medical_boundary": MEDICAL_BOUNDARY,
                    "llm": self._llm_runtime_context(),
                },
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=None,
                action="llm.chat",
                error=error,
                recoverable=True,
                not_recoverable_reason="Configured LLM provider returned a malformed response.",
            )
            return result
        if response.get("error"):
            result = {
                "status": "llm_error",
                "task": task,
                "agent": agent_id,
                "plugin": None,
                "action": "llm.chat",
                "output": None,
                "error": response["error"],
                "llm_response": response,
                "metadata": {
                    "medical_boundary": MEDICAL_BOUNDARY,
                    "llm": self._llm_runtime_context(),
                },
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=None,
                action="llm.chat",
                output=response,
                error=response["error"],
                recoverable=True,
                not_recoverable_reason="Configured LLM provider returned an error.",
            )
            return result

        content = str(response.get("content") or "").strip()
        if not content:
            error = {
                "code": "empty_llm_response",
                "message": "LLM provider returned an empty response",
            }
            result = {
                "status": "llm_error",
                "task": task,
                "agent": agent_id,
                "plugin": None,
                "action": "llm.chat",
                "output": None,
                "error": error,
                "llm_response": response,
                "metadata": {
                    "medical_boundary": MEDICAL_BOUNDARY,
                    "llm": self._llm_runtime_context(),
                },
            }
            self._checkpoint_task(
                task_id=task_id,
                agent_id=agent_id,
                state="failed",
                task=task,
                plugin=None,
                action="llm.chat",
                output=response,
                error=error,
                recoverable=True,
                not_recoverable_reason="Configured LLM provider returned no content.",
            )
            return result

        result = {
            "status": "success",
            "task": task,
            "agent": agent_id,
            "plugin": None,
            "action": "llm.chat",
            "output": content,
            "result": content,
            "error": None,
            "llm_response": response,
            "metadata": {
                "medical_boundary": MEDICAL_BOUNDARY,
                "llm": self._llm_runtime_context(),
            },
        }
        self._checkpoint_task(
            task_id=task_id,
            agent_id=agent_id,
            state="completed",
            task=task,
            plugin=None,
            action="llm.chat",
            output=result,
            recoverable=False,
        )
        return result

    def _llm_chat_messages(self, task: str) -> list[dict[str, str]]:
        """Build the canonical LLM chat message list for standalone Kernel chat."""
        return [
            {"role": "system", "content": SUPERMEDICINE_SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]

    def _select_plugin_action(self, task: str) -> tuple[str | None, str | None]:
        """基于任务文本选择当前阶段可控的真实插件路径。"""
        normalized = task.lower()
        if "survival" in normalized or "kaplan" in normalized or "生存" in normalized:
            return "r-survival", "r.survival.km"
        if "ttest" in normalized or "t-test" in normalized or "t 检验" in normalized:
            return "python-stats", "stats.ttest"
        if "anova" in normalized or "方差" in normalized:
            return "python-stats", "stats.anova"
        if "regression" in normalized or "回归" in normalized:
            return "python-stats", "stats.regression"
        if "rag" in normalized or "retrieval" in normalized or "检索" in normalized:
            return "rag-interface", "rag.query"
        if (
            "harness" in normalized
            or "checkpoint" in normalized
            or "monitor" in normalized
            or "检查点" in normalized
            or "监控" in normalized
        ):
            return "harness-core", "harness.integration.checkpoint"
        if "consort" in normalized or "随机对照" in normalized:
            return "medical-writing", "standard.consort"
        if "strobe" in normalized or "观察性" in normalized:
            return "medical-writing", "standard.strobe"
        if (
            "prisma" in normalized
            or "系统综述" in normalized
            or "meta分析" in normalized
            or "meta-analysis" in normalized
        ):
            return "medical-writing", "standard.prisma"
        if "stard" in normalized or "诊断准确性" in normalized:
            return "medical-writing", "standard.stard"
        if "vancouver" in normalized:
            return "medical-citation", "standard.citation.vancouver"
        if "ama" in normalized or "citation" in normalized or "引用" in normalized:
            return "medical-citation", "standard.citation.ama"
        if (
            "medical writing" in normalized
            or "checklist" in normalized
            or "写作规范" in normalized
            or "检查清单" in normalized
        ):
            return "medical-writing", "standard.consort"
        if "medical" in normalized or "stats" in normalized or "统计" in normalized:
            return "python-stats", "stats.descriptive"
        return None, None
