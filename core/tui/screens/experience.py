"""Chinese TUI experience learning screen/controller foundations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.experience import ExperienceScope, ExportFormat
from core.services import ExperienceEvolutionService


@dataclass(slots=True)
class ExperienceScreenController:
    """Controller for suggestion, confirmation, listing, editing, deletion, export."""

    project_root: Path | str | None = None

    @property
    def service(self) -> ExperienceEvolutionService:
        return ExperienceEvolutionService(self.project_root)

    def suggest_classification(
        self,
        workspace_id: str,
        *,
        summary: str,
        title: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.service.suggest_experience(
            workspace_id,
            summary,
            title=title,
            tags=tags,
            metadata=metadata,
        )
        payload = dict(self.service.require_data(result))
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
        result = self.service.add_experience(
            workspace_id,
            scope,
            title,
            summary,
            tags=tags,
            confirm=confirm,
            source=source,
        )
        payload = dict(self.service.require_data(result))
        payload["label"] = f"经验：{payload['title']}"
        payload["message"] = "经验已确认写入"
        return payload

    def list_experiences(
        self, workspace_id: str, *, include_general: bool = False
    ) -> list[dict[str, Any]]:
        result = self.service.list_experiences(
            workspace_id, include_general=include_general
        )
        return [self._record_payload(record) for record in self.service.require_data(result)]

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
        result = self.service.edit_experience(
            record_id,
            workspace_id,
            scope,
            title=title,
            summary=summary,
            tags=tags,
        )
        return self._record_payload(
            self.service.require_data(result), message="经验已更新"
        )

    def delete_experience(
        self, record_id: str, *, workspace_id: str, scope: ExperienceScope, confirm: str
    ) -> dict[str, Any]:
        if confirm != record_id:
            raise ValueError("删除经验需要输入完全一致的经验 ID 作为确认")
        result = self.service.delete_experience(
            record_id, workspace_id, scope, confirm=confirm
        )
        payload = dict(self.service.require_data(result))
        payload["message"] = "经验已删除"
        return payload

    def export_experiences(
        self,
        *,
        workspace_id: str,
        format: ExportFormat = "json",
        include_general: bool = False,
        path: str | Path | None = None,
    ) -> dict[str, Any]:
        result = self.service.export_experiences(
            workspace_id,
            format,
            include_general=include_general,
            path=path,
        )
        rendered = self.service.require_data(result)
        return {"format": format, "content": rendered, "message": "经验已导出"}

    def _record_payload(
        self, record: dict[str, Any], message: str | None = None
    ) -> dict[str, Any]:
        payload = dict(record)
        payload["label"] = f"经验：{payload['title']}"
        if message is not None:
            payload["message"] = message
        return payload
