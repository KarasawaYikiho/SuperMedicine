"""Shared runtime helpers for Web route adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable

from core.services import ServiceResult


def web_error(message: str, status_code: int) -> Any:
    """Preserve the public error payload while using HTTP error semantics."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={"error": message, "status": "error"},
    )


def service_data(result: ServiceResult[Any]) -> Any:
    """Return legacy data on success and stable HTTP semantics on failure."""
    if result.ok:
        return result.data
    error = result.error
    code = error.code if error else "service_error"
    status_code = {
        "invalid_workspace_id": 400,
        "confirmation_mismatch": 400,
        "workspace_exists": 409,
        "workspace_not_found": 404,
        "permission_denied": 403,
        "required_file_missing": 500,
        "missing_provider": 400,
        "provider_not_found": 404,
        "missing_base_url": 422,
        "missing_api_key": 422,
        "missing_model": 422,
        "incomplete_provider_config": 422,
        "paper_source_missing": 404,
        "paper_not_found": 404,
        "unsupported_paper_format": 422,
        "invalid_tool_language": 422,
        "invalid_tool_id": 422,
        "invalid_tool_manifest": 422,
        "invalid_tool_candidate": 422,
        "tool_not_found": 404,
        "experiment_error": 400,
        "experiment_session_not_found": 404,
        "experience_error": 400,
        "confirmation_required": 400,
        "evolution_artifact_not_found": 404,
        "system_error": 400,
        "agent_harness_error": 400,
    }.get(code, 500)
    return web_error(error.message if error else "Service failed", status_code)


def llm_provider_list_response(result: Any) -> Any:
    """Expose the provider collection as the list consumed by the Web UI."""
    if not isinstance(result, dict):
        return result
    current = str(result.get("current_provider") or "")
    raw_providers = result.get("providers", {})
    provider_items: Iterable[tuple[str, Any]]
    if isinstance(raw_providers, dict):
        provider_items = raw_providers.items()
    elif isinstance(raw_providers, list):
        provider_items = (
            (str(item.get("provider") or item.get("name") or ""), item)
            for item in raw_providers
            if isinstance(item, dict)
        )
    else:
        provider_items = ()
    providers: list[dict[str, Any]] = []
    for name, values in provider_items:
        if not isinstance(values, dict):
            continue
        provider = dict(values)
        provider_name = str(provider.get("provider") or name)
        provider["provider"] = provider_name
        provider["current"] = provider_name == current
        providers.append(provider)
    return {**result, "providers": providers}


def experiment_session_path(session_file: str) -> Path:
    """Resolve a Web-selected experiment only inside managed storage."""
    storage = (Path.cwd() / ".supermedicine" / "experiments").resolve()
    requested = Path(session_file)
    candidate = (
        requested.resolve()
        if requested.is_absolute()
        else (Path.cwd() / requested).resolve()
    )
    try:
        candidate.relative_to(storage)
    except ValueError as exc:
        raise ValueError("Experiment session file is outside managed storage") from exc
    if candidate.suffix.lower() != ".json":
        raise ValueError("Experiment session file must be JSON")
    return candidate


class WebRuntime:
    """Own lazily initialized process state used by HTTP and WebSocket routes."""

    def __init__(self, service_factories: dict[str, Callable[[Path], Any]]) -> None:
        self._instances: dict[str, Any] = {}
        self._service_factories = service_factories

    def service(self, name: str) -> Any:
        """Create a request-scoped application service from injected factories."""
        return self._service_factories[name](Path.cwd())

    def get_kernel(self) -> Any:
        if "kernel" not in self._instances:
            from core.kernel import Kernel
            from permission.policy import ensure_default_policy

            project_dir = Path.cwd()
            policies_dir = project_dir / ".supermedicine" / "policies"
            ensure_default_policy(project_dir)
            self._instances["kernel"] = Kernel(
                config_path=project_dir / ".supermedicine" / "config.yaml",
                plugins_dir=project_dir / "plugins",
                policies_dir=policies_dir,
            )
        return self._instances["kernel"]

    def workspace_context(self, workspace_id: str | None) -> dict[str, Any] | None:
        if not workspace_id:
            return None
        service = self.service("workspace")
        workspace = service.require_data(service.show(workspace_id))
        return {
            "id": workspace["id"],
            "path": workspace["path"],
            "metadata": workspace["metadata"],
        }

    def execute_chat_message(
        self,
        message: str,
        *,
        workspace_id: str | None = None,
        agent_mode: str | None = None,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        kernel = self.get_kernel()
        workspace_context = self.workspace_context(workspace_id)
        params: dict[str, Any] | None = None
        if workspace_context is not None:
            workspace_id = str(workspace_context["id"])
            params = {"_workspace": workspace_context}
            kernel._config.set_runtime_state_value(
                "last_workspace_id", workspace_id, save=True
            )
        else:
            kernel._config.set_runtime_state_value("last_workspace_id", "", save=True)
        result = kernel.execute_task(
            message,
            params=params,
            progress_callback=progress_callback,
            use_agent_chain=None if agent_mode is None else agent_mode == "multi",
        )
        if workspace_context is not None:
            metadata = result.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata.setdefault("workspace", workspace_context)
                metadata.setdefault("workspace_id", workspace_id)
        return result
