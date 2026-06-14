from __future__ import annotations

import json

from agents.checkpoint import CheckpointManager
from plugins.harness.checkpoint_verifier import CheckpointVerifier


# ═══ Checkpoint Manager Tests ═══


class TestCheckpointManager:
    def test_save_checkpoint(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(task_id="t", step=1, state="completed", result={"output": "test"})
        assert (tmp_path / "t" / "step-1" / "status.json").exists()

    def test_load_checkpoint(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(task_id="t", step=1, state="completed", result={"output": "test"})
        cp = mgr.load("t", step=1)
        assert (
            cp is not None
            and cp["state"] == "completed"
            and cp["result"]["output"] == "test"
        )

    def test_get_latest_step(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(task_id="t", step=1, state="completed", result={})
        mgr.save(task_id="t", step=2, state="completed", result={})
        mgr.save(task_id="t", step=3, state="running", result={})
        assert mgr.get_latest_step("t") == 3

    def test_load_nonexistent_returns_none(self, tmp_path):
        assert CheckpointManager(tmp_path).load("nonexistent", step=1) is None

    def test_checkpoint_includes_agent_state_timestamp_and_summaries(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(
            task_id="t",
            step=1,
            state="running",
            result={"output": "ok"},
            agent_id="agent-a",
            input_data={"prompt": "hello"},
            output_data={"answer": "world"},
        )
        cp = mgr.load("t", step=1)
        assert cp["task_id"] == "t"
        assert cp["agent_id"] == "agent-a"
        assert cp["state"] == "running"
        assert "timestamp" in cp
        assert cp["input_summary"]["prompt"] == "hello"
        assert cp["output_summary"]["answer"] == "world"

    def test_failure_checkpoint_and_not_recoverable_report(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(
            task_id="t",
            step=1,
            state="failed",
            result={},
            agent_id="agent-a",
            error="boom",
            recoverable=False,
            not_recoverable_reason="manual review required",
        )
        cp = mgr.load_latest("t")
        assert cp["error_summary"] == "boom"
        assert cp["recoverable"] is False
        report = mgr.recovery_report("t")
        assert report["recoverable"] is False
        assert report["reason"] == "manual review required"

    def test_recoverable_report_for_running_checkpoint(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(
            task_id="t",
            step=1,
            state="running",
            result={},
            agent_id="agent-a",
            recoverable=True,
        )
        report = mgr.recovery_report("t")
        assert report["status"] == "recoverable"
        assert report["checkpoint"]["state"] == "running"

    def test_checkpoint_redacts_sensitive_values(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(
            task_id="t",
            step=1,
            state="running",
            result={"token": "secret-token", "nested": {"password": "secret-password"}},
            agent_id="agent-a",
            input_data={"api_key": "secret-key", "safe": "value"},
        )
        cp = mgr.load("t", step=1)
        assert cp["input_summary"]["api_key"] == "[REDACTED]"
        assert cp["result"]["token"] == "[REDACTED]"
        assert cp["result"]["nested"]["password"] == "[REDACTED]"
        assert cp["input_summary"]["safe"] == "value"


# ═══ Checkpoint Verifier Tests ═══


class TestCheckpointVerifier:
    """测试检查点验证器"""

    def test_verify_missing_task(self, tmp_path):
        """验证不存在的任务"""
        verifier = CheckpointVerifier(tmp_path)
        result = verifier.verify("nonexistent")
        assert result["complete"] is False
        assert "error" in result

    def test_verify_complete_checkpoint(self, tmp_path):
        """验证完整检查点"""
        task_dir = tmp_path / "task-1"
        for step in range(1, 5):
            step_dir = task_dir / f"step-{step}"
            step_dir.mkdir(parents=True)
            (step_dir / "status.json").write_text(
                json.dumps({"state": "completed"}), encoding="utf-8"
            )

        verifier = CheckpointVerifier(tmp_path)
        result = verifier.verify("task-1")
        assert result["complete"] is True
        assert result["structurally_complete"] is True
        assert result["final_state_success"] is True
        assert result["total_steps"] == 4
        assert result["missing_steps"] == []

    def test_verify_incomplete_checkpoint(self, tmp_path):
        """验证不完整检查点（缺失步骤）"""
        task_dir = tmp_path / "task-2"
        for step in [1, 2, 4]:
            step_dir = task_dir / f"step-{step}"
            step_dir.mkdir(parents=True)
            (step_dir / "status.json").write_text(
                json.dumps({"state": "running"}), encoding="utf-8"
            )

        verifier = CheckpointVerifier(tmp_path)
        result = verifier.verify("task-2")
        assert result["complete"] is False
        assert result["structurally_complete"] is False
        assert result["final_state_success"] is False
        assert 3 in result["missing_steps"]

    def test_verify_structural_complete_distinct_from_final_state_success(
        self, tmp_path
    ):
        """Sequential checkpoints can be structurally complete before final completion."""
        task_dir = tmp_path / "task-running"
        for step in range(1, 3):
            step_dir = task_dir / f"step-{step}"
            step_dir.mkdir(parents=True)
            (step_dir / "status.json").write_text(
                json.dumps({"state": "running"}), encoding="utf-8"
            )

        verifier = CheckpointVerifier(tmp_path)
        result = verifier.verify("task-running")

        assert result["complete"] is True
        assert result["structurally_complete"] is True
        assert result["final_state_success"] is False

    def test_verify_malformed_status_is_warning_not_crash(self, tmp_path):
        """Malformed checkpoint status files are observable and mark structure incomplete."""
        task_dir = tmp_path / "task-bad"
        good_step = task_dir / "step-1"
        bad_step = task_dir / "step-2"
        good_step.mkdir(parents=True)
        bad_step.mkdir(parents=True)
        (good_step / "status.json").write_text(
            json.dumps({"state": "completed"}), encoding="utf-8"
        )
        (bad_step / "status.json").write_text("{not-json", encoding="utf-8")

        verifier = CheckpointVerifier(tmp_path)
        result = verifier.verify("task-bad")

        assert result["complete"] is False
        assert result["structurally_complete"] is False
        assert result["final_state_success"] is True
        assert result["warnings"][0]["code"] == "malformed_json"

    def test_verify_all(self, tmp_path):
        """验证所有任务"""
        task_dir = tmp_path / "task-a"
        step_dir = task_dir / "step-1"
        step_dir.mkdir(parents=True)
        (step_dir / "status.json").write_text(
            json.dumps({"state": "completed"}), encoding="utf-8"
        )

        verifier = CheckpointVerifier(tmp_path)
        results = verifier.verify_all()
        assert len(results) == 1
        assert results[0]["task_id"] == "task-a"
