"""Agent and harness application service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.dialog_history import DialogHistoryPrivacyError, DialogHistoryStore
from core.redaction import redact_sensitive
from core.services.result import ServiceResult
from core.workspace import WorkspaceError


class AgentHarnessService:
    """Own user-facing agent/harness summaries without raw conversation storage."""

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
                str(redact_sensitive(str(exc))) or "Agent/harness service failed",
                meta=self._meta(operation),
            )

    @staticmethod
    def require_data(result: ServiceResult[Any]) -> Any:
        if result.ok:
            return result.data
        raise ValueError(
            result.error.message if result.error else "Agent/harness service failed"
        )

    @staticmethod
    def _meta(operation: str) -> dict[str, str]:
        return {"service": "agent_harness", "operation": operation}
