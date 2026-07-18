"""Chinese TUI workspace controller backed by the shared application service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.services import ServiceResult, WorkspaceService


WORKSPACE_DELETE_ACTION = "workspace.delete"
TUI_AGENT_ID = "delta"


@dataclass(slots=True)
class WorkspaceScreenController:
    """Translate TUI inputs and messages around shared workspace use cases."""

    project_root: Path | str | None = None
    agent_id: str = TUI_AGENT_ID

    @property
    def service(self) -> WorkspaceService:
        return WorkspaceService(self.project_root)

    @property
    def root(self) -> Path:
        return self.service.project_root

    def list_workspaces(self) -> list[dict[str, Any]]:
        data = self.service.require_data(self.service.list())
        return [self._display_payload(item, selected=False) for item in data]

    def create_workspace(self, workspace_id: str) -> dict[str, Any]:
        service = self.service
        result = service.create(workspace_id, fail_if_exists=True)
        data = self._require_tui_data(result)
        service.require_data(service.save_selection(data["id"], data["id"]))
        return self._display_payload(
            data, selected=True, message="已创建并选择工作区"
        )

    def select_workspace(
        self, workspace_id: str, *, state_workspace_id: str | None = None
    ) -> dict[str, Any]:
        service = self.service
        data = self._require_tui_data(service.show(workspace_id))
        service.require_data(
            service.save_selection(state_workspace_id or data["id"], data["id"])
        )
        return self._display_payload(data, selected=True, message="已选择工作区")

    def recent_workspace(self, workspace_id: str) -> str | None:
        service = self.service
        return service.require_data(service.load_selection(workspace_id))

    def delete_workspace(self, workspace_id: str, *, confirm: str) -> dict[str, Any]:
        service = self.service
        data = self._require_tui_data(
            service.delete(workspace_id, confirm=confirm, agent_id=self.agent_id)
        )
        return {**data, "message": "工作区已硬删除"}

    @staticmethod
    def _require_tui_data(result: ServiceResult[Any]) -> Any:
        if result.ok:
            return result.data
        error = result.error
        code = error.code if error else "workspace_error"
        if code == "invalid_workspace_id":
            raise ValueError(
                "工作区 ID 只能使用小写字母、数字和连字符，且不能以连字符开头或结尾"
            )
        if code == "workspace_exists":
            workspace_id = error.details.get("workspace_id", "") if error else ""
            raise ValueError(f"工作区已存在：{workspace_id}")
        if code == "confirmation_mismatch":
            raise ValueError("删除工作区需要输入完全一致的工作区 ID 作为确认")
        return WorkspaceService.require_data(result)

    @staticmethod
    def _display_payload(
        data: dict[str, Any], *, selected: bool, message: str | None = None
    ) -> dict[str, Any]:
        payload = {
            **data,
            "label": f"工作区：{data['id']}",
            "selected": selected,
        }
        if message is not None:
            payload["message"] = message
        return payload
