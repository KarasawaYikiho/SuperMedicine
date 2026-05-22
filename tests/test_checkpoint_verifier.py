"""检查点验证器测试"""
from __future__ import annotations

import json
from pathlib import Path

from plugins.harness.checkpoint_verifier import CheckpointVerifier


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
        assert 3 in result["missing_steps"]

    def test_verify_all(self, tmp_path):
        """验证所有任务"""
        task_dir = tmp_path / "task-a"
        step_dir = task_dir / "step-1"
        step_dir.mkdir(parents=True)
        (step_dir / "status.json").write_text(json.dumps({"state": "completed"}), encoding="utf-8")

        verifier = CheckpointVerifier(tmp_path)
        results = verifier.verify_all()
        assert len(results) == 1
        assert results[0]["task_id"] == "task-a"
