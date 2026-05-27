"""长任务状态机"""
from __future__ import annotations
from enum import Enum
from typing import Any

from core.time_utils import utc_now

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
    TaskState.FAILED: [],
}

class StateMachine:
    def __init__(self, task_id: str, max_retries: int = 3):
        self._task_id = task_id
        self._state = TaskState.PLANNING
        self._max_retries = max_retries
        self._retry_count = 0
        self._history: list[dict[str, Any]] = [
            {
                "task_id": task_id,
                "from": None,
                "to": self._state.value,
                "status": "initialized",
                "retry_count": 0,
                "timestamp": utc_now(),
            }
        ]

    @property
    def task_id(self) -> str:
        return self._task_id

    @property
    def state(self) -> TaskState:
        return self._state

    @property
    def retry_count(self) -> int:
        return self._retry_count

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
        valid = VALID_TRANSITIONS.get(self._state, [])
        if new_state not in valid:
            raise ValueError(f"Invalid transition: {self._state.value} -> {new_state.value}")
        # 从 RETRY 状态尝试再次 DISPATCH 时检查重试次数
        if self._state == TaskState.RETRY and new_state == TaskState.DISPATCH:
            if self._retry_count >= self._max_retries:
                raise RuntimeError(f"Max retries ({self._max_retries}) exceeded")
        if new_state == TaskState.RETRY:
            self._retry_count += 1
        old_state = self._state
        self._state = new_state
        self._history.append({
            "task_id": self._task_id,
            "from": old_state.value,
            "to": new_state.value,
            "status": status or new_state.value,
            "retry_count": self._retry_count,
            "timestamp": utc_now(),
            "details": details or {},
        })

    def can_resume(self) -> bool:
        return self._state not in {TaskState.COMPLETED, TaskState.FAILED}

    def snapshot(self) -> dict[str, Any]:
        return {
            "task_id": self._task_id,
            "state": self._state.value,
            "status": self._state.value,
            "retry_count": self._retry_count,
            "max_retries": self._max_retries,
            "recoverable": self.can_resume(),
            "history": self.history,
        }
