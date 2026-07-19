"""检查点管理 — 结构化、可审计、敏感信息脱敏。"""

from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
}


def sanitize_for_checkpoint(value: Any, max_string: int = 500) -> Any:
    """Return a JSON-safe summary with common secret fields redacted."""
    if isinstance(value, dict):
        return {
            str(k): "[REDACTED]"
            if any(
                marker in str(k).lower().replace("-", "_") for marker in SENSITIVE_KEYS
            )
            else sanitize_for_checkpoint(v, max_string)
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


@dataclass(frozen=True, slots=True)
class CheckpointScan:
    """Parsed checkpoint steps and non-fatal storage warnings for one task."""

    task_id: str
    steps: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    error: str | None = None


class CheckpointRepository:
    """Single checkpoint reader shared by agents and the Harness plugin."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def task_ids(self) -> list[str]:
        if not self.base_dir.exists():
            return []
        return sorted(path.name for path in self.base_dir.iterdir() if path.is_dir())

    def read(self, task_id: str, step: int) -> dict[str, Any] | None:
        status_file = self.base_dir / task_id / f"step-{step}" / "status.json"
        if not status_file.exists():
            return None
        loaded = json.loads(status_file.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else None

    def scan(self, task_id: str) -> CheckpointScan:
        task_dir = self.base_dir / task_id
        if not task_dir.exists():
            return CheckpointScan(task_id, [], [], "Task directory not found")
        if not task_dir.is_dir():
            return CheckpointScan(task_id, [], [], "Task path is not a directory")
        steps: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        for step_dir in task_dir.iterdir():
            if not step_dir.is_dir() or not step_dir.name.startswith("step-"):
                continue
            try:
                step = int(step_dir.name.removeprefix("step-"))
            except ValueError:
                warnings.append(
                    self._warning(
                        step_dir,
                        "invalid_step_name",
                        "step directory suffix must be an integer",
                    )
                )
                continue
            status_file = step_dir / "status.json"
            if not status_file.exists():
                warnings.append(
                    self._warning(
                        step_dir, "missing_status", "step directory has no status.json"
                    )
                )
                continue
            try:
                data = json.loads(status_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                warnings.append(
                    self._warning(status_file, "malformed_json", str(exc), step=step)
                )
                continue
            if not isinstance(data, dict):
                warnings.append(
                    self._warning(
                        status_file,
                        "non_object_json",
                        "status.json must contain an object",
                        step=step,
                    )
                )
                continue
            steps.append({"step": step, "state": data.get("state", "unknown")})
        steps.sort(key=lambda item: int(item["step"]))
        return CheckpointScan(task_id, steps, warnings)

    @staticmethod
    def _warning(
        path: Path, code: str, message: str, *, step: int | None = None
    ) -> dict[str, Any]:
        warning: dict[str, Any] = {"path": str(path), "code": code, "message": message}
        if step is not None:
            warning["step"] = step
        return warning


class CheckpointManager:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.repository = CheckpointRepository(self.base_dir)

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
        step_dir = self.base_dir / task_id / f"step-{step}"
        step_dir.mkdir(parents=True, exist_ok=True)
        safe_result = sanitize_for_checkpoint(result or {})
        checkpoint = {
            "task_id": task_id,
            "agent_id": agent_id,
            "step": step,
            "state": state,
            "status": status or state,
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "input_summary": sanitize_for_checkpoint(input_data or {}),
            "output_summary": sanitize_for_checkpoint(
                output_data if output_data is not None else safe_result
            ),
            "error_summary": sanitize_for_checkpoint(error)
            if error is not None
            else None,
            "recoverable": recoverable,
            "not_recoverable_reason": not_recoverable_reason,
            "stage_history": sanitize_for_checkpoint(stage_history or []),
            "result": safe_result,
        }
        (step_dir / "status.json").write_text(
            json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return step_dir

    def load(self, task_id: str, step: int) -> dict[str, Any] | None:
        return self.repository.read(task_id, step)

    def load_latest(self, task_id: str) -> dict[str, Any] | None:
        latest = self.get_latest_step(task_id)
        if latest is None:
            return None
        return self.load(task_id, latest)

    def get_latest_step(self, task_id: str) -> int | None:
        steps = [int(item["step"]) for item in self.repository.scan(task_id).steps]
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
                "reason": checkpoint.get("not_recoverable_reason")
                or "Latest checkpoint is marked not recoverable.",
                "checkpoint": checkpoint,
            }
        if (
            checkpoint.get("state") in {"completed", "failed"}
            and checkpoint.get("recoverable") is not True
        ):
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
