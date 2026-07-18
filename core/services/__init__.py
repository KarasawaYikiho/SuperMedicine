"""Shared application services used by CLI, TUI, Web, and GUI adapters."""

from core.services.result import ServiceError, ServiceResult
from core.services.workspace import WorkspaceService

__all__ = ["ServiceError", "ServiceResult", "WorkspaceService"]
