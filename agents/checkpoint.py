"""检查点管理"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class CheckpointManager:
    def __init__(self, base_dir: Path):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
    def save(self, task_id: str, step: int, state: str, result: dict[str, Any]) -> Path:
        step_dir = self._base_dir / task_id / f"step-{step}"
        step_dir.mkdir(parents=True, exist_ok=True)
        status = {"task_id": task_id, "step": step, "state": state, "timestamp": datetime.now(timezone.utc).isoformat(), "result": result}
        (step_dir / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2))
        return step_dir
    def load(self, task_id: str, step: int) -> dict[str, Any] | None:
        status_file = self._base_dir / task_id / f"step-{step}" / "status.json"
        if not status_file.exists():
            return None
        with open(status_file, encoding="utf-8") as f:
            return json.load(f)
    def get_latest_step(self, task_id: str) -> int | None:
        task_dir = self._base_dir / task_id
        if not task_dir.exists():
            return None
        steps = []
        for d in task_dir.iterdir():
            if d.is_dir() and d.name.startswith("step-"):
                try:
                    steps.append(int(d.name.split("-")[1]))
                except ValueError:
                    continue
        return max(steps) if steps else None
