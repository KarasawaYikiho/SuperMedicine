"""Chinese TUI paper import screen/controller foundations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.services import PaperRAGService


@dataclass(slots=True)
class PaperScreenController:
    """Controller for paper import/list/show/edit/enrich TUI actions."""

    project_root: Path | str | None = None

    @property
    def service(self) -> PaperRAGService:
        return PaperRAGService(self.project_root)

    @property
    def root(self) -> Path:
        return self.service.project_root

    def import_paper(
        self,
        workspace_id: str,
        source_path: str | Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Copy-only import into the explicit workspace."""

        result = self.service.import_paper(
            workspace_id, source_path, metadata or {}
        )
        data = self.service.require_data(result)
        return self._import_payload(data, message="论文已复制导入工作区")

    def list_papers(self, workspace_id: str) -> list[dict[str, Any]]:
        result = self.service.list_papers(workspace_id)
        return [
            self._metadata_payload(paper)
            for paper in self.service.require_data(result)
        ]

    def show_paper(self, workspace_id: str, paper_id: str) -> dict[str, Any]:
        result = self.service.show_paper(workspace_id, paper_id)
        return self._metadata_payload(
            self.service.require_data(result), message="论文详情"
        )

    def edit_metadata(
        self, workspace_id: str, paper_id: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Edit only importer-supported metadata fields."""

        result = self.service.edit_metadata(workspace_id, paper_id, metadata)
        return self._metadata_payload(
            self.service.require_data(result), message="论文元数据已更新"
        )

    def enrich_metadata(
        self, workspace_id: str, paper_id: str, *, confirm: bool
    ) -> dict[str, Any]:
        """Run explicit enrichment confirmation flow; never performs silent online enrichment."""

        result = self.service.enrich_metadata(
            workspace_id, paper_id, confirm=confirm
        )
        payload = dict(self.service.require_data(result))
        payload["message"] = (
            "论文在线补全已完成"
            if payload["status"] == "enriched"
            else "论文在线补全未执行"
        )
        payload["metadata"] = self._metadata_payload(payload["metadata"])
        return payload

    def _import_payload(
        self, result: dict[str, Any], *, message: str
    ) -> dict[str, Any]:
        payload = dict(result)
        payload["message"] = message
        payload["metadata"] = self._metadata_payload(payload["metadata"])
        return payload

    def _metadata_payload(
        self, metadata: dict[str, Any], message: str | None = None
    ) -> dict[str, Any]:
        payload = dict(metadata)
        payload["label"] = (
            f"论文：{payload.get('title') or payload.get('id') or '未命名'}"
        )
        if message is not None:
            payload["message"] = message
        return payload
