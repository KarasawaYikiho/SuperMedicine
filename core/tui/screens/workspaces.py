"""Chinese TUI workspace screen/controller foundations."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.operation_guard import authorize_dangerous_operation
from core.path_safety import validate_destructive_path
from core.tui.state import TUIState
from core.workspace import (
    InvalidWorkspaceId,
    WorkspaceInfo,
    WorkspaceManager,
    WorkspaceNotFoundError,
    validate_workspace_id,
)
from permission.audit import AuditLogger
from permission.engine import PermissionEngine


WORKSPACE_DELETE_ACTION = "workspace.delete"
TUI_AGENT_ID = "delta"


def workspace_label(info: WorkspaceInfo) -> str:
    """Return a Chinese list label for one workspace."""

    return f"工作区：{info.id}"


@dataclass(slots=True)
class WorkspaceScreenController:
    """Controller for testable workspace-selection screen actions."""

    project_root: Path | str | None = None
    agent_id: str = TUI_AGENT_ID

    @property
    def workspace_manager(self) -> WorkspaceManager:
        return WorkspaceManager(self.project_root)

    @property
    def root(self) -> Path:
        return self.workspace_manager.project_root

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List workspaces with Chinese labels for display."""

        return [self._workspace_payload(info, selected=False) for info in self.workspace_manager.list_workspaces()]

    def create_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Create a workspace through the shared WorkspaceManager service."""

        try:
            slug = validate_workspace_id(workspace_id)
        except InvalidWorkspaceId as exc:
            raise ValueError("工作区 ID 只能使用小写字母、数字和连字符，且不能以连字符开头或结尾") from exc

        manager = self.workspace_manager
        try:
            manager.get_workspace(slug)
        except WorkspaceNotFoundError:
            pass
        else:
            raise ValueError(f"工作区已存在：{slug}")

        info = manager.initialize_workspace(slug)
        TUIState(self.root).save_recent_workspace(info.id, info.id)
        return self._workspace_payload(info, selected=True, message="已创建并选择工作区")

    def select_workspace(self, workspace_id: str, *, state_workspace_id: str | None = None) -> dict[str, Any]:
        """Select an existing workspace and persist recent TUI state in workspace sessions."""

        info = self.workspace_manager.get_workspace(workspace_id)
        state_source = state_workspace_id or info.id
        TUIState(self.root).save_recent_workspace(state_source, info.id)
        return self._workspace_payload(info, selected=True, message="已选择工作区")

    def recent_workspace(self, workspace_id: str) -> str | None:
        """Load recent selection from a caller-supplied workspace session state."""

        return TUIState(self.root).load_recent_workspace(workspace_id)

    def delete_workspace(self, workspace_id: str, *, confirm: str) -> dict[str, Any]:
        """Hard-delete a workspace only after exact confirmation and guard approval."""

        manager = self.workspace_manager
        slug = validate_workspace_id(workspace_id)
        workspace_path = manager.workspace_path(slug)
        audit_log = self.root / ".supermedicine" / "policies" / "audit.jsonl"
        audit_logger = AuditLogger(audit_log)

        if confirm != slug:
            audit_logger.log(
                agent_id=self.agent_id,
                action=WORKSPACE_DELETE_ACTION,
                resource=str(workspace_path),
                result="cancelled",
                reason="tui_confirmation_mismatch",
            )
            raise ValueError("删除工作区需要输入完全一致的工作区 ID 作为确认")

        manager.get_workspace(slug)
        safe_path = validate_destructive_path(workspace_path, self.root)
        policies_dir = self.root / ".supermedicine" / "policies"
        default_policy = policies_dir / PermissionEngine.DEFAULT_POLICY_FILENAME
        if not default_policy.exists():
            audit_logger.log(
                agent_id=self.agent_id,
                action=WORKSPACE_DELETE_ACTION,
                resource=str(safe_path),
                result="cancelled",
                reason="missing_default_policy",
            )
            raise FileNotFoundError(f"默认权限策略不存在，无法删除工作区: {default_policy}")

        authorization = authorize_dangerous_operation(
            permission_engine=PermissionEngine(policies_dir, audit_log),
            agent_id=self.agent_id,
            action=WORKSPACE_DELETE_ACTION,
            path=safe_path,
            project_root=self.root,
            context={"workspace_id": slug, "tui_screen": "工作区"},
            destructive=True,
            audit_logger=audit_logger,
            operation="tui_workspace_delete",
        )
        if authorization.path.is_dir():
            shutil.rmtree(authorization.path)
        else:
            authorization.path.unlink()
        return {"status": "deleted", "id": slug, "path": str(authorization.path), "message": "工作区已硬删除"}

    def _workspace_payload(
        self,
        info: WorkspaceInfo,
        *,
        selected: bool,
        message: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": info.id,
            "label": workspace_label(info),
            "path": str(info.path),
            "selected": selected,
            "metadata": info.metadata.to_dict(),
        }
        if message is not None:
            payload["message"] = message
        return payload
