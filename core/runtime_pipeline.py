"""Unified Harness lifecycle primitives for every Kernel task."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any
from uuid import uuid4

from agents.checkpoint import CheckpointManager
from plugins.harness.monitor import AgentPerformanceMonitor, CheckpointVerifier


@dataclass
class TaskRunContext:
    run_id: str
    task: str
    entrypoint: str
    agent_mode: str
    agent_id: str = "alpha"
    workspace_id: str | None = None
    rag_status: str = "skipped"
    permission_checked: bool = False
    stages: list[dict[str, Any]] = field(default_factory=list)
    _started_at: float = field(default_factory=perf_counter, repr=False)
    _finalized: dict[str, Any] | None = field(default=None, repr=False)


class HarnessRuntime:
    """Records one and only one terminal Harness state per task run."""

    def __init__(
        self,
        checkpoints: CheckpointManager,
        performance_monitor: AgentPerformanceMonitor,
    ) -> None:
        self._checkpoints = checkpoints
        self._performance_monitor = performance_monitor

    def begin(
        self,
        *,
        task: str,
        entrypoint: str,
        agent_mode: str,
        agent_id: str = "alpha",
        workspace_id: str | None = None,
    ) -> TaskRunContext:
        run = TaskRunContext(
            run_id=str(uuid4()),
            task=task,
            entrypoint=entrypoint,
            agent_mode=agent_mode,
            agent_id=agent_id,
            workspace_id=workspace_id,
        )
        self.stage(run, "dispatch")
        return run

    def stage(self, run: TaskRunContext, name: str, **details: Any) -> None:
        if run._finalized is not None:
            return
        stage = {"name": name, **details}
        run.stages.append(stage)
        if "rag_status" in details:
            run.rag_status = str(details["rag_status"])
        if "permission_checked" in details:
            run.permission_checked = bool(details["permission_checked"])
        self._checkpoints.save(
            run.run_id,
            len(run.stages),
            "running",
            agent_id=run.agent_id,
            input_data={"task": run.task, "entrypoint": run.entrypoint},
            stage_history=run.stages,
            recoverable=True,
        )

    def finalize(
        self,
        run: TaskRunContext,
        *,
        status: str,
        output: Any = None,
        error: Any = None,
    ) -> dict[str, Any]:
        if run._finalized is not None:
            return run._finalized
        success = status == "success"
        terminal_state = "completed" if success else "failed"
        duration_ms = (perf_counter() - run._started_at) * 1000
        latest_step = self._checkpoints.get_latest_step(run.run_id) or 0
        self._checkpoints.save(
            run.run_id,
            latest_step + 1,
            terminal_state,
            agent_id=run.agent_id,
            status=status,
            output_data=output if isinstance(output, dict) else {"output": output},
            error=error,
            recoverable=False,
            not_recoverable_reason=(
                "Plugin returned an error status."
                if status == "plugin_error"
                else "Task reached a terminal runtime state."
            ),
            stage_history=[*run.stages, {"name": "finalize", "status": status}],
        )
        self._performance_monitor.record(
            run.agent_id, run.run_id, duration_ms, success=success
        )
        verification = CheckpointVerifier(self._checkpoints.base_dir).verify(run.run_id)
        run._finalized = {
            "run_id": run.run_id,
            "finalized": True,
            "duration_ms": round(duration_ms, 3),
            "verification": verification,
        }
        return run._finalized
