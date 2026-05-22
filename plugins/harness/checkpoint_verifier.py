"""检查点验证器 — 验证检查点完整性和可恢复性"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CheckpointVerifier:
    """检查点验证器 — 复用 agents/checkpoint.py 的 CheckpointManager"""

    def __init__(self, checkpoint_dir: Path):
        self._checkpoint_dir = Path(checkpoint_dir)

    def verify(self, task_id: str) -> dict[str, Any]:
        """验证指定任务的所有检查点是否完整

        Returns:
            {"task_id": str, "total_steps": int, "missing_steps": [...], "complete": bool}
        """
        task_dir = self._checkpoint_dir / task_id
        if not task_dir.exists():
            return {"task_id": task_id, "error": "Task directory not found", "complete": False}

        steps = []
        for d in task_dir.iterdir():
            if d.is_dir() and d.name.startswith("step-"):
                try:
                    step_num = int(d.name.split("-")[1])
                    status_file = d / "status.json"
                    if status_file.exists():
                        data = json.loads(status_file.read_text(encoding="utf-8"))
                        steps.append({"step": step_num, "state": data.get("state", "unknown")})
                except (ValueError, json.JSONDecodeError):
                    continue

        steps.sort(key=lambda x: x["step"])
        existing_steps = {s["step"] for s in steps}
        max_step = max(existing_steps) if existing_steps else 0
        missing = [i for i in range(1, max_step + 1) if i not in existing_steps]

        return {
            "task_id": task_id,
            "total_steps": len(steps),
            "steps": steps,
            "missing_steps": missing,
            "complete": len(missing) == 0 and max_step > 0,
        }

    def verify_all(self) -> list[dict[str, Any]]:
        """验证所有任务的检查点"""
        if not self._checkpoint_dir.exists():
            return []
        results = []
        for d in self._checkpoint_dir.iterdir():
            if d.is_dir():
                results.append(self.verify(d.name))
        return results
