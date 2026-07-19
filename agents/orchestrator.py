"""Orchestrator"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .roles import BaseAgent
from .checkpoint import CheckpointManager


class TaskState(Enum):
    PLANNING = "planning"
    DISPATCH = "dispatch"
    RUNNING = "running"
    VERIFYING = "verifying"
    RETRY = "retry"
    COMPLETED = "completed"
    FAILED = "failed"


VALID_TRANSITIONS: dict[TaskState, list[TaskState]] = {
    TaskState.PLANNING: [TaskState.DISPATCH],
    TaskState.DISPATCH: [TaskState.RUNNING],
    TaskState.RUNNING: [TaskState.VERIFYING, TaskState.FAILED],
    TaskState.VERIFYING: [TaskState.COMPLETED, TaskState.RETRY],
    TaskState.RETRY: [TaskState.DISPATCH],
    TaskState.COMPLETED: [],
    TaskState.FAILED: [TaskState.RETRY],
}


class StateMachine:
    def __init__(self, task_id: str, max_retries: int = 3):
        self.task_id = task_id
        self.state = TaskState.PLANNING
        self._max_retries = max_retries
        self.retry_count = 0
        self._history: list[dict[str, Any]] = [
            {
                "task_id": task_id,
                "from": None,
                "to": self.state.value,
                "status": "initialized",
                "retry_count": 0,
                "timestamp": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
            }
        ]

    @property
    def history(self) -> list[dict[str, Any]]:
        return self._history.copy()

    def transition(
        self,
        new_state: TaskState,
        *,
        status: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        valid = VALID_TRANSITIONS.get(self.state, [])
        if new_state not in valid:
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {new_state.value}"
            )
        # 从 RETRY 状态尝试再次 DISPATCH 时检查重试次数
        if self.state == TaskState.RETRY and new_state == TaskState.DISPATCH:
            if self.retry_count >= self._max_retries:
                raise RuntimeError(f"Max retries ({self._max_retries}) exceeded")
        if new_state == TaskState.RETRY:
            self.retry_count += 1
        old_state = self.state
        self.state = new_state
        self._history.append(
            {
                "task_id": self.task_id,
                "from": old_state.value,
                "to": new_state.value,
                "status": status or new_state.value,
                "retry_count": self.retry_count,
                "timestamp": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                "details": details or {},
            }
        )

    def can_resume(self) -> bool:
        return (
            self.state != TaskState.COMPLETED and self.retry_count < self._max_retries
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "status": self.state.value,
            "retry_count": self.retry_count,
            "max_retries": self._max_retries,
            "recoverable": self.can_resume(),
            "history": self.history,
        }


class Orchestrator:
    def __init__(
        self,
        checkpoint_manager: CheckpointManager | None = None,
        checkpoint_dir: Path | None = None,
        permission_check: Callable[[str, dict[str, Any]], bool] | None = None,
    ):
        self._agents: dict[str, BaseAgent] = {}
        self.checkpoint_manager = checkpoint_manager or CheckpointManager(
            checkpoint_dir or Path(".supermedicine") / "checkpoints"
        )
        self._task_steps: dict[str, int] = {}
        self._task_states: dict[str, StateMachine] = {}
        self._permission_check = permission_check

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def describe(self) -> dict[str, Any]:
        return {
            "agents": [agent.describe_state() for agent in self.list_agents()],
            "checkpoint_dir": str(self.checkpoint_manager.base_dir),
        }

    def _next_step(self, task_id: str) -> int:
        current = self._task_steps.get(task_id)
        if current is None:
            current = self.checkpoint_manager.get_latest_step(task_id) or 0
        current += 1
        self._task_steps[task_id] = current
        return current

    def _save_stage(
        self,
        *,
        task_id: str,
        agent_id: str,
        machine: StateMachine,
        state: TaskState,
        task: dict[str, Any],
        result: dict[str, Any] | None = None,
        error: Any = None,
        recoverable: bool | None = None,
        not_recoverable_reason: str | None = None,
    ) -> Path:
        return self.checkpoint_manager.save(
            task_id=task_id,
            step=self._next_step(task_id),
            state=state.value,
            status=state.value,
            agent_id=agent_id,
            input_data=task,
            output_data=result,
            error=error,
            recoverable=machine.can_resume() if recoverable is None else recoverable,
            not_recoverable_reason=not_recoverable_reason,
            stage_history=machine.history,
            result=result or {},
        )

    def dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        task_id = str(
            task.get("task_id")
            or task.get("id")
            or f"task-{len(self._task_states) + 1}"
        )
        state_key = f"{task_id}:{agent_id}"
        machine = self._task_states.get(state_key)
        if machine is None or machine.state == TaskState.COMPLETED:
            machine = StateMachine(task_id=task_id)
        self._task_states[state_key] = machine
        if machine.state == TaskState.PLANNING:
            machine.transition(
                TaskState.DISPATCH,
                status="agent_selected",
                details={"agent_id": agent_id},
            )
        elif machine.state == TaskState.FAILED:
            machine.transition(TaskState.RETRY, status="resume_requested")
            machine.transition(
                TaskState.DISPATCH,
                status="agent_reselected",
                details={"agent_id": agent_id},
            )
        self._save_stage(
            task_id=task_id,
            agent_id=agent_id,
            machine=machine,
            state=machine.state,
            task=task,
        )

        agent = self._agents.get(agent_id)
        if agent is None:
            machine.transition(TaskState.RUNNING, status="agent_lookup")
            machine.transition(
                TaskState.FAILED, status="unknown_agent", details={"agent_id": agent_id}
            )
            self._save_stage(
                task_id=task_id,
                agent_id=agent_id,
                machine=machine,
                state=TaskState.FAILED,
                task=task,
                error=f"Unknown agent: {agent_id}",
                recoverable=False,
                not_recoverable_reason="No registered agent can resume this dispatch.",
            )
            raise KeyError(f"Unknown agent: {agent_id}")
        if self._permission_check is not None and not self._permission_check(
            agent_id, task
        ):
            machine.transition(TaskState.RUNNING, status="permission_check")
            machine.transition(
                TaskState.FAILED,
                status="permission_denied",
                details={"agent_id": agent_id},
            )
            self._save_stage(
                task_id=task_id,
                agent_id=agent_id,
                machine=machine,
                state=TaskState.FAILED,
                task=task,
                error="Agent dispatch permission denied.",
                recoverable=False,
                not_recoverable_reason="Agent dispatch was denied by policy.",
            )
            raise PermissionError(f"Agent dispatch denied: {agent_id}")
        try:
            machine.transition(
                TaskState.RUNNING,
                status="agent_executing",
                details={"agent_id": agent_id},
            )
            self._save_stage(
                task_id=task_id,
                agent_id=agent_id,
                machine=machine,
                state=machine.state,
                task=task,
            )
            result = agent.execute(task)
            machine.transition(
                TaskState.VERIFYING,
                status="agent_completed",
                details={"agent_id": agent_id},
            )
            machine.transition(
                TaskState.COMPLETED,
                status="dispatch_completed",
                details={"agent_id": agent_id},
            )
            self._save_stage(
                task_id=task_id,
                agent_id=agent_id,
                machine=machine,
                state=TaskState.COMPLETED,
                task=task,
                result=result,
                recoverable=False,
            )
            result.setdefault("task_id", task_id)
            result.setdefault("agent_id", agent_id)
            result.setdefault("state", TaskState.COMPLETED.value)
            return result
        except Exception as exc:
            if machine.state == TaskState.RUNNING:
                machine.transition(
                    TaskState.FAILED,
                    status="agent_error",
                    details={"agent_id": agent_id},
                )
            self._save_stage(
                task_id=task_id,
                agent_id=agent_id,
                machine=machine,
                state=TaskState.FAILED,
                task=task,
                error=str(exc),
                recoverable=machine.can_resume(),
                not_recoverable_reason=(
                    None
                    if machine.can_resume()
                    else "Agent execution exceeded the configured retry limit."
                ),
            )
            raise

    def recovery_report(self, task_id: str) -> dict[str, Any]:
        return self.checkpoint_manager.recovery_report(task_id)
