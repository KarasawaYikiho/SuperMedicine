"""SuperMedicine 微内核 — 集成所有核心组件"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.checkpoint import CheckpointManager
from core.config_center import ConfigCenter
from core.event_bus import EventBus
from core.plugin_registry import PluginRegistry
from core.session_manager import SessionManager
from permission.engine import PermissionEngine
from permission.policy import DEFAULT_POLICY_RELATIVE_PATH, PermissionResult


MEDICAL_BOUNDARY = (
    "Current-stage SuperMedicine output: not production/clinical medical advice; "
    "requires expert review before any research, regulatory, or clinical use."
)


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
        self._event_bus = EventBus()
        self._plugin_registry = PluginRegistry(self._plugins_dir)
        self._session_manager = SessionManager()
        self._checkpoint_manager = CheckpointManager(self._config_path.parent / "checkpoints")

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
        """P0 权限引擎 — 双重约束（代码层 + Prompt 层），一票否决制"""
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
            output_data=output if isinstance(output, dict) else {"output": output} if output is not None else None,
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
        task_id = f"kernel-{abs(hash((task, plugin_name, action, agent_id))) & 0xffffffff:x}"
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
            result = {
                "status": "failure",
                "task": task,
                "error": "No executable medical/statistics plugin action matched the task.",
                "medical_boundary": MEDICAL_BOUNDARY,
            }
            self._checkpoint_task(task_id=task_id, agent_id=agent_id, state="failed", task=task, plugin=selected_plugin, action=selected_action, error=result["error"], recoverable=False, not_recoverable_reason="No executable plugin/action was selected.")
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
            "policy_path": str(self._policies_dir / self._permission_engine.DEFAULT_POLICY_FILENAME),
            "resource": {"kind": "plugin", "plugin": selected_plugin, "action": selected_action},
            "security": {"permission_entrypoint": "kernel", "permission_checked": True},
        }

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
            self._checkpoint_task(task_id=task_id, agent_id=agent_id, state="failed", task=task, plugin=selected_plugin, action=selected_action, error=result["error"], recoverable=False, not_recoverable_reason="Permission denied by canonical policy chain.")
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
            self._checkpoint_task(task_id=task_id, agent_id=agent_id, state="failed", task=task, plugin=selected_plugin, action=selected_action, error=result["error"], recoverable=False, not_recoverable_reason="Selected plugin is not installed or discoverable.")
            return result

        try:
            plugin_result = plugin.execute(selected_action, params or {}, execution_context)
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
            self._checkpoint_task(task_id=task_id, agent_id=agent_id, state="failed", task=task, plugin=selected_plugin, action=selected_action, error=result["error"], recoverable=False, not_recoverable_reason="Plugin raised an exception; manual review required before retry.")
            return result

        metadata = plugin_result.get("metadata") if isinstance(plugin_result.get("metadata"), dict) else {}
        if "medical_boundary" not in metadata:
            metadata["medical_boundary"] = plugin_result.get("medical_boundary", MEDICAL_BOUNDARY)
        if "statistics_boundary" not in metadata and plugin_result.get("statistics_boundary"):
            metadata["statistics_boundary"] = plugin_result.get("statistics_boundary")
        metadata.setdefault("resource", execution_context["resource"])
        metadata.setdefault("security", {"permission_checked": True, "permission": "allowed", "permission_entrypoint": "kernel"})

        if plugin_result.get("status") not in (None, "success"):
            result = {
                "status": "plugin_error",
                "task": task,
                "plugin": selected_plugin,
                "action": selected_action,
                "output": None,
                "error": plugin_result.get("error") or plugin_result.get("message") or "Plugin returned error status.",
                "plugin_result": plugin_result,
                "metadata": metadata,
            }
            self._checkpoint_task(task_id=task_id, agent_id=agent_id, state="failed", task=task, plugin=selected_plugin, action=selected_action, output=plugin_result, error=result["error"], recoverable=False, not_recoverable_reason="Plugin returned an error status.")
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
        self._checkpoint_task(task_id=task_id, agent_id=agent_id, state="completed", task=task, plugin=selected_plugin, action=selected_action, output=result, recoverable=False)
        return result

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
        if "medical" in normalized or "stats" in normalized or "统计" in normalized:
            return "python-stats", "stats.descriptive"
        return "python-stats", "stats.descriptive"
