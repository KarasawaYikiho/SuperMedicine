"""SuperMedicine 微内核 — 集成所有核心组件"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4
from typing import Any, Callable, cast

from agents.checkpoint import CheckpointManager
from agents.orchestrator import Orchestrator
from agents.roles import AlphaAgent
from agents.roles import BetaAgent
from agents.roles import GammaAgent
from agents.roles import DeltaAgent
from core.config_center import ConfigCenter
from core.database.database import Database
from core.database.migrations import MigrationManager
from core.database.repository import AgentRepository
from core.event_bus import EventBus
from core.llm_manager import LLMConfigManager
from core.plugin_registry import PluginRegistry
from core.runtime_capabilities import (
    RuntimeCapabilities,
    RuntimeInvariantError,
    validate_required_plugins,
)
from core.runtime_pipeline import HarnessRuntime
from core.rag_service import RAGService
from plugins.harness.monitor import AgentPerformanceMonitor
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
        self._plugin_registry = PluginRegistry(
            self._plugins_dir, allow_package_fallback=plugins_dir is None
        )
        self._plugin_registry.discover()
        self._runtime_capabilities = validate_required_plugins(
            self._plugin_registry, self._config_path
        )
        self._session_manager = SessionManager()
        self._checkpoint_manager = CheckpointManager(
            self._config_path.parent / "checkpoints"
        )
        self._performance_monitor = AgentPerformanceMonitor(
            self._config_path.parent / "performance.jsonl"
        )
        self._harness_runtime = HarnessRuntime(
            self._checkpoint_manager, self._performance_monitor
        )
        self._refresh_runtime_capabilities()

        # Database initialization with graceful fallback
        self._database: Database | None = None
        try:
            db_path = self._config_path.parent / "data.db"
            self._database = Database(db_path)
            self._database.connect()
            # Run pending migrations
            migration_manager = MigrationManager(self._database)
            migration_manager.run_pending()
            # Re-initialize SessionManager with database support
            self._session_manager = SessionManager(db=self._database)
        except Exception:
            # Fall back to in-memory mode (no persistence)
            if self._database is not None:
                try:
                    self._database.disconnect()
                except Exception:
                    pass
            self._database = None

        # Agent repository for state persistence
        self._agent_repo: AgentRepository | None = None
        if self._database is not None:
            self._agent_repo = AgentRepository(self._database)

        # P0 权限引擎集成
        audit_log_path = self._policies_dir / "audit.jsonl"
        self._permission_engine = PermissionEngine(
            self._policies_dir,
            audit_log_path,
        )
        self._rag_service = RAGService(
            self._config,
            self._config_path,
            permission_engine=self._permission_engine,
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

    def _refresh_runtime_capabilities(self) -> None:
        """Attach config-derived state to the validated shared health snapshot."""
        agent_mode = (
            "multi"
            if self._config.get_multi_agent_config()["enabled"]
            else "single"
        )
        project_root = (
            self._config_path.parent.parent
            if self._config_path.parent.name == ".supermedicine"
            else self._config_path.parent
        )
        rag_index = str(project_root / ".supermedicine" / "rag" / "local")
        self._runtime_capabilities = replace(
            self._runtime_capabilities,
            agent_mode=agent_mode,
            rag_index=rag_index,
        )

    def _create_agent_orchestrator(self) -> Orchestrator:
        """Create and return an Orchestrator pre-loaded with alpha, beta, gamma, delta agents."""
        def permission_check(agent_id: str, task: dict[str, Any]) -> bool:
            return (
                self._permission_engine.check(
                    agent_id,
                    "plan",
                    "agent.pipeline",
                    context={
                        "task": task.get("task"),
                        "agent_mode": "multi",
                    },
                )
                == PermissionResult.ALLOWED
            )

        orch = Orchestrator(
            checkpoint_manager=self._checkpoint_manager,
            permission_check=permission_check,
        )
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
        rag_context: Any = None,
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
        if not isinstance(context, dict):
            context = {}
        if rag_context is not None:
            context = {**context, "rag": rag_context.as_prompt_payload()}

        # Step 2: Alpha analysis
        emit("status", "Alpha agent analysing task…")
        alpha_input = {**task_dict, "context": context}
        alpha_result = orch.dispatch(
            target if target == "alpha" else "alpha", alpha_input
        )

        # Step 3: Beta review
        emit("status", "Beta agent reviewing analysis…")
        beta_input = {**task_dict, **alpha_result, "context": context}
        beta_result = orch.dispatch("beta", beta_input)

        if not beta_result.get("approved", False):
            emit("status", "Beta agent rejected the analysis; chain halted.")
            # Persist agent states after chain execution
            self.save_agent_state("delta", delta_result)
            self.save_agent_state("alpha", alpha_result)
            self.save_agent_state("beta", beta_result)
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
        # Persist agent states after chain execution
        self.save_agent_state("delta", delta_result)
        self.save_agent_state("alpha", alpha_result)
        self.save_agent_state("beta", beta_result)
        self.save_agent_state("gamma", gamma_result)
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
    def runtime_capabilities(self) -> RuntimeCapabilities:
        """Return the validated mandatory-runtime health snapshot."""
        return self._runtime_capabilities

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def database(self) -> Database | None:
        """Database instance for persistent storage, or None if in-memory mode."""
        return self._database

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

    def close(self) -> None:
        """Close database connection and release resources."""
        if self._database is not None:
            try:
                self._database.disconnect()
            except Exception:
                pass
            self._database = None

    def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Persist agent runtime state to the database.

        This is a no-op when the database is not available.

        Args:
            agent_id: Agent identifier (e.g. 'alpha', 'beta', 'gamma', 'delta')
            state: Arbitrary state dict to persist
        """
        if self._agent_repo is None:
            return
        existing = self._agent_repo.get_by_name(agent_id)
        if existing is None:
            self._agent_repo.create({"name": agent_id, "state": state})
        else:
            existing["state"] = state
            self._agent_repo.update(existing)

    def load_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        """Load persisted agent runtime state from the database.

        Args:
            agent_id: Agent identifier (e.g. 'alpha', 'beta', 'gamma', 'delta')

        Returns:
            The agent's persisted state dict, or None if not found or
            database is unavailable.
        """
        if self._agent_repo is None:
            return None
        agent = self._agent_repo.get_by_name(agent_id)
        if agent is None:
            return None
        return agent.get("state")

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
        checkpoint_state = "running" if state in {"completed", "failed"} else state
        self._checkpoint_manager.save(
            task_id=task_id,
            step=latest + 1,
            state=checkpoint_state,
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
            stage_history=[{"name": state}],
        )

    def execute_task(
        self,
        task: str,
        plugin_name: str | None = None,
        action: str | None = None,
        params: dict[str, Any] | None = None,
        agent_id: str = "alpha",
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        use_agent_chain: bool | None = None,
    ) -> dict[str, Any]:
        """Execute every task inside the mandatory Harness lifecycle."""
        self._config.reload()
        configured_multi_agent = self._config.get_multi_agent_config()["enabled"]
        resolved_agent_mode = (
            configured_multi_agent
            if use_agent_chain is None
            else bool(use_agent_chain)
        )
        try:
            run = self._harness_runtime.begin(
                task=task,
                entrypoint="kernel.execute_task",
                agent_mode="multi" if resolved_agent_mode else "single",
                agent_id=agent_id,
            )
        except Exception as exc:
            return {
                "status": "harness_unavailable",
                "task": task,
                "agent": agent_id,
                "plugin": plugin_name,
                "action": action,
                "output": None,
                "error": {"code": "harness_unavailable", "message": str(exc)},
                "metadata": {
                    "harness": {
                        "enabled": True,
                        "participated": False,
                        "finalized": False,
                    }
                },
            }
        result: dict[str, Any]
        try:
            result = self._execute_task_uninstrumented(
                task,
                plugin_name=plugin_name,
                action=action,
                params=params,
                agent_id=agent_id,
                progress_callback=progress_callback,
                use_agent_chain=resolved_agent_mode,
                task_id=run.run_id,
            )
        except RuntimeInvariantError as exc:
            result = {
                "status": "runtime_invariant_error",
                "task": task,
                "agent": agent_id,
                "plugin": plugin_name,
                "action": action,
                "output": None,
                "error": exc.to_dict(),
                "metadata": {},
            }
        except PermissionError as exc:
            result = {
                "status": "denied",
                "task": task,
                "agent": agent_id,
                "plugin": plugin_name,
                "action": action,
                "output": None,
                "error": {
                    "code": "agent_permission_denied",
                    "message": str(exc),
                },
                "metadata": {
                    "permission": {"checked": True, "result": "denied"},
                    "agent_mode": "multi" if resolved_agent_mode else "single",
                },
            }
        except Exception as exc:
            result = {
                "status": "failed",
                "task": task,
                "agent": agent_id,
                "plugin": plugin_name,
                "action": action,
                "output": None,
                "error": {"code": "kernel_execution_error", "message": str(exc)},
                "metadata": {},
            }
        finally:
            final = None
            finalize_error = None
            try:
                final = self._harness_runtime.finalize(
                    run,
                    status=str(result.get("status", "failed"))
                    if "result" in locals()
                    else "failed",
                    output=result.get("output") if "result" in locals() else None,
                    error=result.get("error") if "result" in locals() else None,
                )
            except Exception as exc:
                finalize_error = exc
        if finalize_error is not None:
            return {
                "status": "harness_unavailable",
                "task": task,
                "agent": agent_id,
                "plugin": plugin_name,
                "action": action,
                "output": None,
                "error": {
                    "code": "harness_unavailable",
                    "message": str(finalize_error),
                },
                "metadata": {
                    "harness": {
                        "enabled": True,
                        "participated": True,
                        "finalized": False,
                    }
                },
            }
        assert final is not None
        metadata = result.setdefault("metadata", {})
        if not isinstance(metadata, dict):
            metadata = result["metadata"] = {}
        metadata["harness"] = {
            "enabled": True,
            "participated": True,
            "finalized": True,
            "verification": final["verification"],
        }
        metadata.setdefault(
            "agent_mode", "multi" if resolved_agent_mode else "single"
        )
        if "rag" not in metadata:
            classification = self._rag_service.classify_task(
                task, result.get("plugin"), result.get("action")
            )
            skip_reason = (
                "control_task" if classification == "control" else "deterministic_plugin"
            )
            metadata["rag"] = {
                "enabled": True,
                "status": "skipped",
                "skip_reason": skip_reason,
            }
        rag_metadata = metadata.get("rag")
        if isinstance(rag_metadata, dict) and "sources" in rag_metadata:
            metadata.setdefault("sources", rag_metadata["sources"])
        metadata.setdefault("sources", [])
        permission_metadata = metadata.get("permission")
        if not isinstance(permission_metadata, dict):
            metadata["permission"] = {
                "checked": True,
                "result": permission_metadata or "allowed",
            }
        else:
            permission_metadata.setdefault("checked", True)
        result["run_id"] = run.run_id
        return result

    def _execute_task_uninstrumented(
        self,
        task: str,
        plugin_name: str | None = None,
        action: str | None = None,
        params: dict[str, Any] | None = None,
        agent_id: str = "alpha",
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        use_agent_chain: bool = False,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """执行用户任务或医疗插件，返回结构化结果。

        Kernel 是插件生产执行的唯一入口：先使用 PermissionEngine 检查
        ``execute`` 权限，再调用插件，并把所有插件结果转换为稳定的
        ``status/task/agent/plugin/action/output/error/metadata`` 形状。

        When *use_agent_chain* is ``True`` the task is routed through the
        multi-agent pipeline (alpha → beta → gamma) coordinated by delta,
        rather than executing a single agent directly.
        """
        # Reload config from disk to pick up changes made by TUI/CLI
        # (e.g. permission mode switch via PermissionScreenController).
        self._config.reload()
        self._plugin_registry.discover()
        self._runtime_capabilities = validate_required_plugins(
            self._plugin_registry, self._config_path
        )
        self._refresh_runtime_capabilities()

        def emit(kind: str, message: str = "", **payload: Any) -> None:
            if progress_callback is None:
                return
            progress_callback({"kind": kind, "message": message, **payload})

        task_id = task_id or str(uuid4())
        workspace_path = None
        workspace = (params or {}).get("_workspace")
        if isinstance(workspace, dict) and workspace.get("path"):
            workspace_path = Path(str(workspace["path"]))

        # --- optional multi-agent chain ---
        if use_agent_chain:
            rag_context = self._rag_service.retrieve(task, workspace_path)
            result = self._execute_agent_chain(
                task,
                task_id=task_id,
                emit=emit,
                rag_context=rag_context,
                progress_callback=progress_callback,
            )
            metadata = result.setdefault("metadata", {})
            metadata["rag"] = {
                **rag_context.as_metadata(),
                "sources": list(rag_context.sources),
            }
            metadata["agent_mode"] = "multi"
            return result

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
                workspace_path=workspace_path,
            )
        selected_plugin, selected_action = dispatch
        plugin_rag_context = None
        if (
            self._rag_service.classify_task(task, selected_plugin, selected_action)
            == "knowledge_generation"
        ):
            plugin_rag_context = self._rag_service.retrieve(task, workspace_path)
            params = dict(params or {})
            params["_rag_context"] = plugin_rag_context.as_prompt_payload()

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
                task,
                agent_id,
                selected_plugin,
                selected_action,
                task_id,
                emit,
                execution_context,
            )
        emit("status", "权限检查通过，插件正在执行。")

        # --- plugin lookup ---
        plugin = self._plugin_registry.get(selected_plugin)
        if plugin is None:
            return self._handle_missing_plugin(
                task,
                agent_id,
                selected_plugin,
                selected_action,
                task_id,
            )

        # --- execute plugin and shape result ---
        result = self._execute_plugin(
            plugin,
            selected_action,
            params,
            execution_context,
            task,
            agent_id,
            selected_plugin,
            task_id,
            emit,
        )
        if plugin_rag_context is not None:
            metadata = result.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata["rag"] = {
                    **plugin_rag_context.as_metadata(),
                    "sources": list(plugin_rag_context.sources),
                }
        return result

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
        workspace_path: Path | None = None,
    ) -> dict[str, Any]:
        """Execute an unmatched natural-language task through the configured LLM."""
        # Ensure config is fresh before building LLM messages with permission context.
        self._config.reload()
        rag_context = self._rag_service.retrieve(task, workspace_path)
        return _execute_llm_chat_fn(
            task,
            task_id=task_id,
            agent_id=agent_id,
            llm_manager=self._llm_manager,
            config=self._config,
            config_path=self._config_path,
            checkpoint_task_fn=self._checkpoint_task,
            progress_callback=progress_callback,
            rag_context={
                **rag_context.as_metadata(),
                "sources": list(rag_context.sources),
            },
        )

    def _llm_chat_messages(self, task: str) -> list[dict[str, str]]:
        """Build the canonical LLM chat message list for standalone Kernel chat."""
        return _llm_chat_messages_fn(task, self._config, self._config_path)

    def _workspace_tool_runtime_context(self, workspace_id: str) -> dict[str, Any]:
        """Return currently imported workspace tools for LLM context when available."""
        return _workspace_tool_runtime_context_fn(workspace_id, self._config_path)
