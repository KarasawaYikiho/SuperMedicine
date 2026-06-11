"""SuperMedicine 微内核 — 集成所有核心组件"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from agents.checkpoint import CheckpointManager
from agents.orchestrator import Orchestrator
from agents.alpha_agent import AlphaAgent
from agents.beta_agent import BetaAgent
from agents.gamma_agent import GammaAgent
from agents.delta_agent import DeltaAgent
from core.config_center import ConfigCenter
from core.event_bus import EventBus
from core.llm_manager import LLMConfigManager
from core.plugin_registry import PluginRegistry
from core.session_manager import SessionManager
from permission.engine import PermissionEngine
from permission.policy import (
    DEFAULT_POLICY_RELATIVE_PATH,
    PermissionResult,
    ensure_default_policy,
)

from core.kernel_constants import MEDICAL_BOUNDARY
from core.kernel_llm_chat import (
    execute_llm_chat as _execute_llm_chat_fn,
    llm_chat_messages as _llm_chat_messages_fn,
    llm_runtime_context as _llm_runtime_context_fn,
    workspace_tool_runtime_context as _workspace_tool_runtime_context_fn,
)
from core.kernel_plugin_select import select_plugin_action


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

        self._ensure_canonical_default_policy()

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

    def _ensure_canonical_default_policy(self) -> None:
        """Create the canonical default policy for normal project policy dirs.

        Custom non-canonical policy directories are left untouched so tests and
        callers that intentionally provide their own policy set still receive
        clear loading errors from PermissionEngine when those files are absent.
        """
        policy_dir = self._policies_dir
        if policy_dir == DEFAULT_POLICY_RELATIVE_PATH.parent:
            ensure_default_policy(Path.cwd())
            return
        if (
            policy_dir.name == DEFAULT_POLICY_RELATIVE_PATH.parent.name
            and policy_dir.parent.name
            == DEFAULT_POLICY_RELATIVE_PATH.parent.parent.name
        ):
            ensure_default_policy(policy_dir.parent.parent)

    def _create_agent_orchestrator(self) -> Orchestrator:
        """Create and return an Orchestrator pre-loaded with alpha, beta, gamma, delta agents."""
        orch = Orchestrator(checkpoint_manager=self._checkpoint_manager)
        orch.register_agent(AlphaAgent())
        orch.register_agent(BetaAgent())
        orch.register_agent(GammaAgent())
        orch.register_agent(DeltaAgent())
        return orch

    def _execute_agent_chain(
        self,
        task: str,
        *,
        task_id: str,
        emit: Callable[..., None],
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Run the full alpha → beta → gamma pipeline coordinated by delta.

        Delta routes the initial task to alpha for analysis, the analysis
        result goes to beta for review, and if approved the reviewed result
        is forwarded to gamma for content generation.  If beta rejects the
        result the chain stops early and returns the review.
        """
        orch = self._create_agent_orchestrator()
        task_dict: dict[str, Any] = {"task": task, "task_id": task_id}

        # Step 1: Delta routes the task
        emit("status", "Delta agent routing task…")
        delta_result = orch.dispatch("delta", task_dict)
        target = delta_result.get("target_agent", "alpha")
        context = delta_result.get("context", {})

        # Step 2: Alpha analysis
        emit("status", "Alpha agent analysing task…")
        alpha_input = {**task_dict, "context": context}
        alpha_result = orch.dispatch(target if target == "alpha" else "alpha", alpha_input)

        # Step 3: Beta review
        emit("status", "Beta agent reviewing analysis…")
        beta_input = {**task_dict, **alpha_result, "context": context}
        beta_result = orch.dispatch("beta", beta_input)

        if not beta_result.get("approved", False):
            emit("status", "Beta agent rejected the analysis; chain halted.")
            return {
                "status": "rejected",
                "task": task,
                "agent": "beta",
                "task_id": task_id,
                "output": None,
                "error": beta_result.get("feedback", "Review rejected."),
                "alpha_result": alpha_result,
                "beta_result": beta_result,
                "metadata": {
                    "chain": ["delta", "alpha", "beta"],
                    "halted_at": "beta",
                },
            }

        # Step 4: Gamma content generation
        emit("status", "Gamma agent generating content…")
        gamma_input = {**task_dict, **alpha_result, "context": context}
        gamma_result = orch.dispatch("gamma", gamma_input)

        emit("status", "Agent chain completed successfully.")
        return {
            "status": "success",
            "task": task,
            "agent": "gamma",
            "task_id": task_id,
            "output": gamma_result.get("content", ""),
            "result": gamma_result,
            "error": None,
            "metadata": {
                "chain": ["delta", "alpha", "beta", "gamma"],
                "alpha_result": alpha_result,
                "beta_result": beta_result,
                "gamma_result": gamma_result,
            },
        }

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
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        use_agent_chain: bool = False,
    ) -> dict[str, Any]:
        """执行用户任务或医疗插件，返回结构化结果。

        Kernel 是插件生产执行的唯一入口：先使用 PermissionEngine 检查
        ``execute`` 权限，再调用插件，并把所有插件结果转换为稳定的
        ``status/task/agent/plugin/action/output/error/metadata`` 形状。

        When *use_agent_chain* is ``True`` the task is routed through the
        multi-agent pipeline (alpha → beta → gamma) coordinated by delta,
        rather than executing a single agent directly.
        """
        self._plugin_registry.discover()

        def emit(kind: str, message: str = "", **payload: Any) -> None:
            if progress_callback is None:
                return
            progress_callback({"kind": kind, "message": message, **payload})

        task_id = (
            f"kernel-{abs(hash((task, plugin_name, action, agent_id))) & 0xFFFFFFFF:x}"
        )

        # --- optional multi-agent chain ---
        if use_agent_chain:
            return self._execute_agent_chain(
                task,
                task_id=task_id,
                emit=emit,
                progress_callback=progress_callback,
            )

        self._checkpoint_task(
            task_id=task_id,
            agent_id=agent_id,
            state="dispatch",
            task=task,
            plugin=plugin_name,
            action=action,
            recoverable=True,
        )
        emit("status", "Kernel 已接收任务，正在选择执行路径。")

        # --- dispatch: resolve plugin/action or fall back to LLM chat ---
        dispatch = self._dispatch_plugin_task(
            task, plugin_name, action, task_id, agent_id, progress_callback
        )
        if dispatch is None:
            return self._execute_llm_chat(
                task,
                task_id=task_id,
                agent_id=agent_id,
                progress_callback=progress_callback,
            )
        selected_plugin, selected_action = dispatch

        self._checkpoint_task(
            task_id=task_id,
            agent_id=agent_id,
            state="running",
            task=task,
            plugin=selected_plugin,
            action=selected_action,
            recoverable=True,
        )
        emit(
            "status",
            f"已选择插件 {selected_plugin} / {selected_action}，正在进行权限检查。",
        )

        # --- build permission context ---
        execution_context = self._build_permission_context(
            task, agent_id, selected_plugin, selected_action, params
        )

        # --- permission check ---
        permission = self._permission_engine.check(
            agent_id,
            "execute",
            selected_action,
            context=execution_context,
        )
        if permission == PermissionResult.DENIED:
            return self._handle_permission_denied(
                task, agent_id, selected_plugin, selected_action,
                task_id, emit, execution_context,
            )
        emit("status", "权限检查通过，插件正在执行。")

        # --- plugin lookup ---
        plugin = self._plugin_registry.get(selected_plugin)
        if plugin is None:
            return self._handle_missing_plugin(
                task, agent_id, selected_plugin, selected_action, task_id,
            )

        # --- execute plugin and shape result ---
        return self._execute_plugin(
            plugin, selected_action, params, execution_context,
            task, agent_id, selected_plugin, task_id, emit,
        )

    def _dispatch_plugin_task(
        self,
        task: str,
        plugin_name: str | None,
        action: str | None,
        task_id: str,
        agent_id: str,
        progress_callback: Callable[[dict[str, Any]], None] | None,
    ) -> tuple[str, str] | None:
        """Select plugin/action; return None to fall back to LLM chat."""
        selected_plugin = plugin_name
        selected_action = action
        if selected_plugin is None or selected_action is None:
            selected_plugin, selected_action = select_plugin_action(task)
        if selected_plugin is None or selected_action is None:
            return None
        return selected_plugin, selected_action

    def _build_permission_context(
        self,
        task: str,
        agent_id: str,
        selected_plugin: str,
        selected_action: str,
        params: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build the execution context dict used for permission checks."""
        execution_context: dict[str, Any] = {
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
        return execution_context

    def _handle_permission_denied(
        self,
        task: str,
        agent_id: str,
        selected_plugin: str,
        selected_action: str,
        task_id: str,
        emit: Callable[..., None],
        execution_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle permission denied: checkpoint and return denied result."""
        emit("status", "权限检查未通过，已停止执行。")
        result: dict[str, Any] = {
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

    def _handle_missing_plugin(
        self,
        task: str,
        agent_id: str,
        selected_plugin: str,
        selected_action: str,
        task_id: str,
    ) -> dict[str, Any]:
        """Handle missing plugin: checkpoint and return missing_plugin result."""
        result: dict[str, Any] = {
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

    def _execute_plugin(
        self,
        plugin: Any,
        selected_action: str,
        params: dict[str, Any] | None,
        execution_context: dict[str, Any],
        task: str,
        agent_id: str,
        selected_plugin: str,
        task_id: str,
        emit: Callable[..., None],
    ) -> dict[str, Any]:
        """Execute the plugin, shape the result, and checkpoint."""
        try:
            plugin_result = plugin.execute(
                selected_action, params or {}, execution_context
            )
        except Exception as exc:
            result: dict[str, Any] = {
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
        emit("status", "插件执行完成，正在整理输出。")
        return result

    def _llm_runtime_context(self) -> dict[str, Any]:
        """Expose secret-safe LLM runtime state to plugin/task paths."""
        return _llm_runtime_context_fn(self._llm_manager, self._config)

    def _execute_llm_chat(
        self,
        task: str,
        *,
        task_id: str,
        agent_id: str,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Execute an unmatched natural-language task through the configured LLM."""
        return _execute_llm_chat_fn(
            task,
            task_id=task_id,
            agent_id=agent_id,
            llm_manager=self._llm_manager,
            config=self._config,
            config_path=self._config_path,
            checkpoint_task_fn=self._checkpoint_task,
            progress_callback=progress_callback,
        )

    def _llm_chat_messages(self, task: str) -> list[dict[str, str]]:
        """Build the canonical LLM chat message list for standalone Kernel chat."""
        return _llm_chat_messages_fn(task, self._config, self._config_path)

    def _workspace_tool_runtime_context(self, workspace_id: str) -> dict[str, Any]:
        """Return currently imported workspace tools for LLM context when available."""
        return _workspace_tool_runtime_context_fn(workspace_id, self._config_path)


