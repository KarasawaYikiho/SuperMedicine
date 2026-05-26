"""Workspace-local TUI dialog history without raw conversation storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.path_safety import validate_path_in_project_root
from core.workspace import WorkspaceManager


DIALOG_HISTORY_FILENAME = "dialog_history.jsonl"
RAW_CONVERSATION_FIELDS = frozenset(
    {
        "raw_conversation",
        "raw_conversation_text",
        "conversation",
        "conversation_text",
        "messages",
        "transcript",
        "prompt",
        "completion",
    }
)


class DialogHistoryPrivacyError(ValueError):
    """Raised when dialog history input contains prohibited raw conversation data."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _contains_prohibited_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in RAW_CONVERSATION_FIELDS:
                return True
            if _contains_prohibited_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_prohibited_key(item) for item in value)
    return False


def _contains_prohibited_marker(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_prohibited_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_prohibited_marker(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in RAW_CONVERSATION_FIELDS)
    return False


def _reject_raw_conversation(payload: dict[str, Any]) -> None:
    if _contains_prohibited_key(payload) or _contains_prohibited_marker(payload):
        raise DialogHistoryPrivacyError("TUI 对话历史只允许保存摘要/事件，不能保存原始对话")


@dataclass(frozen=True, slots=True)
class DialogHistoryEvent:
    """A persisted summary/event row for TUI dialog history."""

    event: str
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "created_at": self.created_at,
            "event": self.event,
            "summary": self.summary,
            "metadata": dict(self.metadata),
        }
        _reject_raw_conversation(payload)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DialogHistoryEvent":
        _reject_raw_conversation(data)
        return cls(
            id=str(data.get("id") or uuid4()),
            created_at=str(data.get("created_at") or _utc_now()),
            event=str(data.get("event") or "event"),
            summary=str(data.get("summary") or ""),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class DialogHistoryStore:
    """JSONL store under ``.supermedicine/sessions`` for one workspace."""

    project_root: Path | str | None = None

    @property
    def workspace_manager(self) -> WorkspaceManager:
        return WorkspaceManager(self.project_root)

    def history_path(self, workspace_id: str, session_id: str = "default") -> Path:
        workspace = self.workspace_manager.get_workspace(workspace_id)
        safe_session_id = _safe_session_id(session_id)
        return validate_path_in_project_root(
            workspace.path / ".supermedicine" / "sessions" / f"{safe_session_id}-{DIALOG_HISTORY_FILENAME}",
            self.workspace_manager.project_root,
        )

    def append_event(
        self,
        workspace_id: str,
        *,
        event: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
        session_id: str = "default",
    ) -> DialogHistoryEvent:
        history_event = DialogHistoryEvent(event=event, summary=summary, metadata=dict(metadata or {}))
        payload = history_event.to_dict()
        path = self.history_path(workspace_id, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return history_event

    def load_events(self, workspace_id: str, *, session_id: str = "default") -> list[DialogHistoryEvent]:
        path = self.history_path(workspace_id, session_id)
        if not path.is_file():
            return []
        events: list[DialogHistoryEvent] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                loaded = json.loads(stripped)
                if not isinstance(loaded, dict):
                    raise DialogHistoryPrivacyError("TUI 对话历史 JSONL 行必须是对象")
                events.append(DialogHistoryEvent.from_dict(loaded))
        return events


def _safe_session_id(session_id: str) -> str:
    if not session_id or "\\" in session_id or "/" in session_id or ".." in session_id:
        raise ValueError("session_id 只能是简单会话名称")
    return session_id
