"""检查点管理 — 结构化、可审计、敏感信息脱敏。"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from core.time_utils import utc_now

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(marker in normalized for marker in SENSITIVE_KEYS)


def sanitize_for_checkpoint(value: Any, max_string: int = 500) -> Any:
    """Return a JSON-safe summary with common secret fields redacted."""
    if isinstance(value, dict):
        return {
            str(k): "[REDACTED]" if _is_sensitive_key(str(k)) else sanitize_for_checkpoint(v, max_string)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [sanitize_for_checkpoint(item, max_string) for item in value[:20]]
    if isinstance(value, tuple):
        return [sanitize_for_checkpoint(item, max_string) for item in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and len(value) > max_string:
            return value[:max_string] + "...[truncated]"
        return value
    return repr(value)[:max_string]

class CheckpointManager:
    def __init__(self, base_dir: Path):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def save(
        self,
        task_id: str,
        step: int,
        state: str,
        result: dict[str, Any] | None = None,
        *,
        agent_id: str | None = None,
        status: str | None = None,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        error: Any = None,
        recoverable: bool | None = None,
        not_recoverable_reason: str | None = None,
        stage_history: list[dict[str, Any]] | None = None,
    ) -> Path:
        step_dir = self._base_dir / task_id / f"step-{step}"
        step_dir.mkdir(parents=True, exist_ok=True)
        safe_result = sanitize_for_checkpoint(result or {})
        checkpoint = {
            "task_id": task_id,
            "agent_id": agent_id,
            "step": step,
            "state": state,
            "status": status or state,
            "timestamp": utc_now(),
            "input_summary": sanitize_for_checkpoint(input_data or {}),
            "output_summary": sanitize_for_checkpoint(output_data if output_data is not None else safe_result),
            "error_summary": sanitize_for_checkpoint(error) if error is not None else None,
            "recoverable": recoverable,
            "not_recoverable_reason": not_recoverable_reason,
            "stage_history": sanitize_for_checkpoint(stage_history or []),
            "result": safe_result,
        }
        (step_dir / "status.json").write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
        return step_dir

    def load(self, task_id: str, step: int) -> dict[str, Any] | None:
        status_file = self._base_dir / task_id / f"step-{step}" / "status.json"
        if not status_file.exists():
            return None
        with open(status_file, encoding="utf-8") as f:
            return json.load(f)

    def load_latest(self, task_id: str) -> dict[str, Any] | None:
        latest = self.get_latest_step(task_id)
        if latest is None:
            return None
        return self.load(task_id, latest)

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

    def recovery_report(self, task_id: str) -> dict[str, Any]:
        checkpoint = self.load_latest(task_id)
        if checkpoint is None:
            return {
                "task_id": task_id,
                "status": "not_recoverable",
                "recoverable": False,
                "reason": "No checkpoint found for task.",
            }
        if checkpoint.get("recoverable") is False:
            return {
                "task_id": task_id,
                "status": "not_recoverable",
                "recoverable": False,
                "reason": checkpoint.get("not_recoverable_reason") or "Latest checkpoint is marked not recoverable.",
                "checkpoint": checkpoint,
            }
        if checkpoint.get("state") in {"completed", "failed"} and checkpoint.get("recoverable") is not True:
            return {
                "task_id": task_id,
                "status": "not_recoverable",
                "recoverable": False,
                "reason": f"Terminal state cannot be resumed: {checkpoint.get('state')}",
                "checkpoint": checkpoint,
            }
        return {
            "task_id": task_id,
            "status": "recoverable",
            "recoverable": True,
            "checkpoint": checkpoint,
        }
