"""Application boundary for platform-adapter authorization."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from core.redaction import redact_sensitive
from core.services.result import ServiceResult
from permission.engine import PermissionEngine
from permission.policy import DEFAULT_POLICY_RELATIVE_PATH, PermissionResult


class PermissionChecker(Protocol):
    def check(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> PermissionResult: ...


class AdapterService:
    """Own canonical permission loading and decisions for every adapter host."""

    def __init__(
        self,
        project_root: str | Path | None = None,
        permission_engine: PermissionChecker | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self._permission_engine = permission_engine

    @property
    def policy_path(self) -> Path:
        return self.project_root / DEFAULT_POLICY_RELATIVE_PATH

    def authorize(
        self,
        *,
        adapter: str,
        agent_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        try:
            engine = self._permission_engine or self._load_permission_engine()
            decision = engine.check(
                agent_id,
                action,
                resource,
                context={
                    "adapter": adapter,
                    "policy_path": str(self.policy_path),
                    **(context or {}),
                },
            )
            return ServiceResult.success(
                {"allowed": decision == PermissionResult.ALLOWED},
                meta={"service": "adapter", "operation": "authorize"},
            )
        except Exception as exc:
            return ServiceResult.failure(
                "permission_engine_unavailable",
                str(redact_sensitive(str(exc))) or "Permission service unavailable",
                details={"policy_path": str(self.policy_path)},
                meta={"service": "adapter", "operation": "authorize"},
            )

    def _load_permission_engine(self) -> PermissionChecker:
        policy_dir = self.policy_path.parent
        self._permission_engine = PermissionEngine(
            policy_dir, policy_dir / "audit.jsonl"
        )
        return self._permission_engine
