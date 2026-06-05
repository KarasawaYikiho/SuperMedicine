from __future__ import annotations

import pytest
from agents.state_machine import TaskState, StateMachine


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine(task_id="t")
        assert sm.state == TaskState.PLANNING

    def test_transition_planning_to_dispatch(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        assert sm.state == TaskState.DISPATCH

    def test_transition_dispatch_to_running(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        assert sm.state == TaskState.RUNNING

    def test_transition_running_to_verifying(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        assert sm.state == TaskState.VERIFYING

    def test_transition_verifying_to_completed(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        sm.transition(TaskState.COMPLETED)
        assert sm.state == TaskState.COMPLETED

    def test_transition_verifying_to_retry(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        sm.transition(TaskState.RETRY)
        assert sm.state == TaskState.RETRY

    def test_invalid_transition_raises(self):
        with pytest.raises(ValueError):
            StateMachine(task_id="t").transition(TaskState.COMPLETED)

    def test_retry_increments_counter(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        sm.transition(TaskState.RETRY)
        assert sm.retry_count == 1

    def test_max_retries_exceeded(self):
        sm = StateMachine(task_id="t", max_retries=3)
        for _ in range(3):
            sm.transition(TaskState.DISPATCH)
            sm.transition(TaskState.RUNNING)
            sm.transition(TaskState.VERIFYING)
            sm.transition(TaskState.RETRY)
        with pytest.raises(RuntimeError):
            sm.transition(TaskState.DISPATCH)

    def test_history_has_explicit_status_and_timestamp(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH, status="selected")
        assert sm.history[-1]["status"] == "selected"
        assert sm.history[-1]["task_id"] == "t"
        assert "timestamp" in sm.history[-1]

    def test_snapshot_reports_recoverability(self):
        sm = StateMachine(task_id="t")
        assert sm.snapshot()["recoverable"] is True
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.FAILED)
        assert sm.snapshot()["recoverable"] is False
