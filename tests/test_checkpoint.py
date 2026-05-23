from agents.checkpoint import CheckpointManager

class TestCheckpointManager:
    def test_save_checkpoint(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(task_id="t", step=1, state="completed", result={"output": "test"})
        assert (tmp_path / "t" / "step-1" / "status.json").exists()
    def test_load_checkpoint(self, tmp_path):
        mgr = CheckpointManager(tmp_path)
        mgr.save(task_id="t", step=1, state="completed", result={"output": "test"})
        cp = mgr.load("t", step=1)
        assert cp is not None and cp["state"] == "completed" and cp["result"]["output"] == "test"
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
        mgr.save(task_id="t", step=1, state="running", result={}, agent_id="agent-a", recoverable=True)
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
