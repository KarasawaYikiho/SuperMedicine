"""Chinese TUI experience learning screen/controller foundations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.experience import ExperienceScope, ExperienceStore, ExportFormat


@dataclass(slots=True)
class ExperienceScreenController:
    """Controller for suggestion, confirmation, listing, editing, deletion, export."""

    project_root: Path | str | None = None

    @property
    def store(self) -> ExperienceStore:
        return ExperienceStore(self.project_root)

    def suggest_classification(
        self,
        workspace_id: str,
        *,
        summary: str,
        title: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        suggestion = self.store.suggest_classification(
            workspace_id=workspace_id,
            title=title,
            summary=summary,
            tags=tags,
            metadata=metadata,
        )
        payload = suggestion.to_dict()
        payload["label"] = "经验分类建议"
        payload["message"] = "请确认后再写入经验库"
        return payload

    def confirm_suggestion(
        self,
        workspace_id: str,
        *,
        scope: ExperienceScope,
        title: str,
        summary: str,
        tags: list[str] | None = None,
        confirm: bool,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not confirm:
            raise ValueError("写入经验前需要用户最终确认")
        record = self.store.confirm_classification(
            workspace_id=workspace_id,
            scope=scope,
            title=title,
            summary=summary,
            tags=tags,
            source=source,
        )
        payload = record.to_dict()
        payload["label"] = f"经验：{record.title}"
        payload["message"] = "经验已确认写入"
        return payload

    def list_experiences(self, workspace_id: str, *, include_general: bool = False) -> list[dict[str, Any]]:
        return [self._record_payload(record) for record in self.store.list_experiences(workspace_id, include_general=include_general)]

    def edit_experience(
        self,
        record_id: str,
        *,
        workspace_id: str,
        scope: ExperienceScope,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        record = self.store.edit_experience(
            record_id,
            workspace_id=workspace_id,
            scope=scope,
            title=title,
            summary=summary,
            tags=tags,
        )
        return self._record_payload(record, message="经验已更新")

    def delete_experience(self, record_id: str, *, workspace_id: str, scope: ExperienceScope, confirm: str) -> dict[str, Any]:
        if confirm != record_id:
            raise ValueError("删除经验需要输入完全一致的经验 ID 作为确认")
        deleted = self.store.delete_experience(record_id, workspace_id=workspace_id, scope=scope)
        return {"status": "deleted", "id": deleted.id, "scope": deleted.scope, "message": "经验已删除"}

    def export_experiences(
        self,
        *,
        workspace_id: str,
        format: ExportFormat = "json",
        include_general: bool = False,
        path: str | Path | None = None,
    ) -> dict[str, Any]:
        rendered = self.store.export_experiences(
            workspace_id=workspace_id,
            format=format,
            include_general=include_general,
            path=path,
        )
        return {"format": format, "content": rendered, "message": "经验已导出"}

    def _record_payload(self, record, message: str | None = None) -> dict[str, Any]:
        payload = record.to_dict()
        payload["label"] = f"经验：{record.title}"
        if message is not None:
            payload["message"] = message
        return payload
