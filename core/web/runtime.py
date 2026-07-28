"""Shared runtime helpers for Web route adapters."""

from __future__ import annotations

from pathlib import Path
import logging
from typing import Any, Callable, Iterable

from core.services import ServiceResult
from permission.redaction import redact_sensitive

logger = logging.getLogger(__name__)


def web_error(message: str, status_code: int, *, code: str | None = None) -> Any:
    """Return the shared public error envelope without leaking server failures."""
    from core.web.errors import APIError, api_error_response

    codes = {
        "No message provided": "message_required",
        "No workspace id provided": "workspace_id_required",
        "No source_path provided": "source_path_required",
        "scope, title, and summary are required": "experience_fields_required",
        "scope is required": "experience_scope_required",
        "No provider specified": "provider_required",
        "No mode specified": "permission_mode_required",
        "No path specified": "path_required",
        "No protocol specified": "protocol_required",
        "step_id and input_json are required": "experiment_step_input_required",
        "instruction is required": "invalid_self_evolution_request",
        "source and external_id are required": "online_paper_fields_required",
        "agent_mode must be 'single' or 'multi'": "invalid_agent_mode",
        "enabled must be a boolean": "invalid_multi_agent_state",
    }
    if status_code >= 500 and code != "shutdown_unavailable":
        return api_error_response(
            APIError(
                status_code,
                code or "internal_error",
                "系统暂时无法完成请求，请稍后重试。",
            )
        )
    return api_error_response(
        APIError(status_code, code or codes.get(message, "request_error"), message)
    )


def service_data(result: ServiceResult[Any]) -> Any:
    """Return legacy data on success and stable HTTP semantics on failure."""
    if result.ok:
        return result.data
    error = result.error
    code = error.code if error else "service_error"
    public_code = {
        "evolution_artifact_not_found": "artifact_not_found",
    }.get(code, code)
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
        "online_paper_unavailable": 503,
        "invalid_paper_request": 400,
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
        "invalid_artifact_id": 400,
        "system_error": 500,
        "agent_harness_error": 400,
    }.get(code, 500)
    return web_error(
        error.message if error else "Service failed", status_code, code=public_code
    )


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


def experiment_session_path(
    session_file: str, project_root: str | Path | None = None
) -> Path:
    """Resolve a Web-selected experiment only inside managed storage."""
    root = Path(project_root or Path.cwd()).resolve()
    storage = (root / ".supermedicine" / "experiments").resolve()
    requested = Path(session_file)
    candidate = (
        requested.resolve()
        if requested.is_absolute()
        else (root / requested).resolve()
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

    def __init__(
        self,
        service_factories: dict[str, Callable[[Path], Any]],
        *,
        project_root: str | Path | None = None,
        resource_root: str | Path | None = None,
        application: Any = None,
        auth_token: str | None = None,
        shutdown_callback: Callable[[], None] | None = None,
    ) -> None:
        self._instances: dict[str, Any] = {}
        self._service_factories = service_factories
        self.project_root = Path(project_root).resolve() if project_root is not None else None
        self.resource_root = (
            Path(resource_root).resolve() if resource_root is not None else None
        )
        self.application = application
        self.auth_token = auth_token
        self.shutdown_callback = shutdown_callback

    def service(self, name: str) -> Any:
        """Create a request-scoped application service from injected factories."""
        return self._service_factories[name](self.project_root or Path.cwd())

    def get_kernel(self) -> Any:
        if "kernel" not in self._instances:
            from core.kernel import Kernel
            from permission.policy import ensure_default_policy_in

            project_dir = self.project_root or Path.cwd()
            resource_dir = self.resource_root or project_dir
            config_path = (
                self.application.paths.config_path
                if self.application is not None
                else project_dir / ".supermedicine" / "config.yaml"
            )
            policies_dir = config_path.parent / "policies"
            ensure_default_policy_in(policies_dir, source_root=resource_dir)
            self._instances["kernel"] = Kernel(
                config_path=config_path,
                plugins_dir=resource_dir / "plugins",
                policies_dir=policies_dir,
                project_root=project_dir,
            )
        return self._instances["kernel"]

    def close(self) -> None:
        """Release lazily created process resources during server shutdown."""
        kernel = self._instances.pop("kernel", None)
        if kernel is not None:
            kernel.close()

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
        project_dir = self.project_root or Path.cwd()
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
        if result.get("status") == "success":
            from core.services import ExperienceEvolutionService

            safe_message = str(redact_sensitive(message[:500]))
            recommendation = ExperienceEvolutionService(
                project_dir,
                config_path=kernel._config_path,
            ).recommend_evolution(
                "复盘本次 Agent 执行并提炼可复用经验：" + safe_message,
                workspace_id=workspace_id,
                source={
                    "kind": "agent_discovery",
                    "agent": str(result.get("agent") or "alpha"),
                    "task_id": str(result.get("task_id") or ""),
                },
            )
            if not recommendation.ok:
                logger.warning(
                    "Self-evolution recommendation was not queued: %s",
                    recommendation.error.message
                    if recommendation.error is not None
                    else "unknown error",
                )
        if workspace_context is not None:
            metadata = result.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata.setdefault("workspace", workspace_context)
                metadata.setdefault("workspace_id", workspace_id)
        return result
