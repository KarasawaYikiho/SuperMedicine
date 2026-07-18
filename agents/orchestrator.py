"""Orchestrator"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .base_agent import BaseAgent
from .checkpoint import CheckpointManager
from .state_machine import StateMachine, TaskState


class Orchestrator:
    def __init__(
        self,
        checkpoint_manager: CheckpointManager | None = None,
        checkpoint_dir: Path | None = None,
        permission_check: Callable[[str, dict[str, Any]], bool] | None = None,
    ):
        self._agents: dict[str, BaseAgent] = {}
        self._checkpoint_manager = checkpoint_manager or CheckpointManager(
            checkpoint_dir or Path(".supermedicine") / "checkpoints"
        )
        self._task_steps: dict[str, int] = {}
        self._task_states: dict[str, StateMachine] = {}
        self._permission_check = permission_check

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        return self._checkpoint_manager

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def describe(self) -> dict[str, Any]:
        return {
            "agents": [agent.describe_state() for agent in self.list_agents()],
            "checkpoint_dir": str(self._checkpoint_manager.base_dir),
        }

    def _next_step(self, task_id: str) -> int:
        current = self._task_steps.get(task_id)
        if current is None:
            current = self._checkpoint_manager.get_latest_step(task_id) or 0
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
        return self._checkpoint_manager.save(
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
        machine = self._task_states.get(state_key) or StateMachine(task_id=task_id)
        self._task_states[state_key] = machine
        if machine.state == TaskState.PLANNING:
            machine.transition(
                TaskState.DISPATCH,
                status="agent_selected",
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
                recoverable=False,
                not_recoverable_reason="Agent execution raised an exception; manual review required before retry.",
            )
            raise

    def recovery_report(self, task_id: str) -> dict[str, Any]:
        return self._checkpoint_manager.recovery_report(task_id)
