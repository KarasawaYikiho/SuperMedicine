import pytest
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
