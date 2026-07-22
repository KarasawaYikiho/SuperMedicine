"""Agent and harness application service."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, Callable

from core.dialog_history import DialogHistoryPrivacyError, DialogHistoryStore
from core.workspace import WorkspaceError

from . import result as _result
from .result import ServiceResult


class AgentHarnessService:
    """Own user-facing agent/harness summaries without raw conversation storage."""

    require_data = staticmethod(
        partial(_result._require_data, "Agent/harness service failed", {})
    )
    _meta = staticmethod(partial(_result._service_meta, "agent_harness"))

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.history = DialogHistoryStore(project_root)

    def append_dialog_event(
        self,
        workspace_id: str,
        *,
        event: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
        session_id: str = "default",
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "append_dialog_event",
            lambda: self.history.append_event(
                workspace_id,
                event=event,
                summary=summary,
                metadata=metadata,
                session_id=session_id,
            ).to_dict(),
        )

    def list_dialog_events(
        self, workspace_id: str, *, session_id: str = "default"
    ) -> ServiceResult[list[dict[str, Any]]]:
        return self._call(
            "list_dialog_events",
            lambda: [
                event.to_dict()
                for event in self.history.load_events(
                    workspace_id, session_id=session_id
                )
            ],
        )

    def _call(self, operation: str, action: Callable[[], Any]) -> ServiceResult[Any]:
        try:
            return ServiceResult.success(action(), meta=self._meta(operation))
        except (DialogHistoryPrivacyError, WorkspaceError, ValueError, OSError) as exc:
            return ServiceResult.failure(
                "agent_harness_error", str(exc), meta=self._meta(operation)
            )
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                _result._safe_internal_message(exc, "Agent/harness service failed"),
                meta=self._meta(operation),
            )
