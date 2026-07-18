"""JSON subprocess bridge from the Bun OpenTUI shell to application services."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from core.services import (
    AgentHarnessService,
    ExperienceEvolutionService,
    ExperimentToolService,
    LLMService,
    PaperRAGService,
    PermissionLogSystemService,
    ServiceResult,
    WorkspaceService,
)


def multi_agent_operation(action: str, project_root: str | Path) -> dict[str, Any]:
    service = PermissionLogSystemService(project_root)
    if action == "status":
        result = service.multi_agent_status()
    elif action == "enable":
        result = service.set_multi_agent_enabled(True)
    elif action == "disable":
        result = service.set_multi_agent_enabled(False)
    else:
        raise ValueError(f"Unsupported multi-agent bridge action: {action}")
    return result.to_dict()


def _records(
    result: ServiceResult[Any], *, empty_reason: str = "no records"
) -> list[Any]:
    if not result.ok:
        return [
            {"status": "error", "error": result.error.to_dict() if result.error else {}}
        ]
    data = result.data
    if isinstance(data, list):
        return data or [{"status": "empty", "reason": empty_reason}]
    return (
        [data]
        if data not in (None, {}, "")
        else [{"status": "empty", "reason": empty_reason}]
    )


def catalog_snapshot(project_root: str | Path) -> dict[str, Any]:
    """Return all OpenTUI page records from shared application services."""
    root = Path(project_root).resolve()
    system = PermissionLogSystemService(root)
    runtime = system.runtime_state()
    runtime_data = runtime.data if runtime.ok and isinstance(runtime.data, dict) else {}
    workspace_id = str(runtime_data.get("last_workspace_id") or "")

    workspaces = WorkspaceService(root).list()
    llm = LLMService(root).list_providers()
    experiments = ExperimentToolService(root)
    capabilities = system.plugin_capabilities()
    capability_data = (
        capabilities.data
        if capabilities.ok and isinstance(capabilities.data, dict)
        else {}
    )
    missing_workspace: ServiceResult[list[Any]] = ServiceResult.success(
        [], meta={"service": "opentui", "reason": "workspace_not_selected"}
    )
    dialog = (
        AgentHarnessService(root).list_dialog_events(workspace_id)
        if workspace_id
        else missing_workspace
    )
    papers = (
        PaperRAGService(root).list_papers(workspace_id)
        if workspace_id
        else missing_workspace
    )
    experiences = (
        ExperienceEvolutionService(root).list_experiences(
            workspace_id, include_general=True
        )
        if workspace_id
        else missing_workspace
    )
    tools = experiments.list_tools(workspace_id) if workspace_id else missing_workspace
    pages = {
        "chat": _records(dialog, empty_reason="no dialog events"),
        "dashboard": [
            {"runtime_state": runtime_data},
            {"workspace_count": len(workspaces.data or []) if workspaces.ok else 0},
            {"capabilities": capability_data},
        ],
        "workspace": _records(workspaces, empty_reason="no workspaces"),
        "paper": _records(papers, empty_reason="select a workspace to list papers"),
        "experience": _records(
            experiences, empty_reason="select a workspace to list experiences"
        ),
        "tool": _records(tools, empty_reason="select a workspace to list tools"),
        "dialog": _records(dialog, empty_reason="no dialog events"),
        "llm": _llm_records(llm),
        "experiment": _records(experiments.list_experiments()),
        "log": _records(system.list_logs(), empty_reason="no log reports"),
        "permission": _records(system.permission_status())
        + _records(system.multi_agent_status()),
        "self-evolution": _records(
            ExperienceEvolutionService(root).list_evolution_artifacts(),
            empty_reason="no evolution artifacts",
        ),
        "diagnose": _records(system.config_diagnostics())
        + [{"plugin_capabilities": capability_data}],
    }
    return ServiceResult.success(
        {
            "pages": pages,
            "runtime_state": runtime_data,
            "capabilities": capability_data,
        },
        meta={"service": "opentui", "operation": "catalog_snapshot"},
    ).to_dict()


def _llm_records(result: ServiceResult[Any]) -> list[dict[str, Any]]:
    if not result.ok or not isinstance(result.data, dict):
        return _records(result, empty_reason="no LLM providers")
    current = result.data.get("current_provider")
    providers = result.data.get("providers")
    if not isinstance(providers, dict) or not providers:
        return [{"status": "empty", "reason": "no LLM providers"}]
    return [
        {"provider": name, "current": name == current, **values}
        for name, values in providers.items()
        if isinstance(values, dict)
    ]


def _runtime_workspace(project_root: str | Path) -> str:
    state = PermissionLogSystemService(project_root).runtime_state()
    if not state.ok or not isinstance(state.data, dict):
        return ""
    return str(state.data.get("last_workspace_id") or "")


def activate_record(
    route: str, record: dict[str, Any], project_root: str | Path
) -> dict[str, Any]:
    """Activate a selected OpenTUI record through its application service."""
    if route == "workspace":
        workspace_id = str(record.get("id") or "")
        shown = WorkspaceService(project_root).show(workspace_id)
        if not shown.ok:
            return shown.to_dict()
        saved = PermissionLogSystemService(project_root).set_runtime_state_value(
            "last_workspace_id", workspace_id
        )
        return saved.to_dict()
    if route == "llm":
        provider = str(record.get("provider") or "")
        switched = LLMService(project_root).switch_provider(provider)
        if switched.ok:
            LLMService(project_root).save_exit_state(provider)
        return switched.to_dict()
    return ServiceResult.success(
        record, meta={"service": "opentui", "operation": "activate", "route": route}
    ).to_dict()


def submit_value(route: str, value: str, project_root: str | Path) -> dict[str, Any]:
    """Submit the OpenTUI input bar to a route-specific application service."""
    if route == "workspace":
        created = WorkspaceService(project_root).create(value, fail_if_exists=True)
        if not created.ok:
            return created.to_dict()
        PermissionLogSystemService(project_root).set_runtime_state_value(
            "last_workspace_id", value
        )
        return created.to_dict()
    if route == "chat":
        workspace_id = _runtime_workspace(project_root)
        if not workspace_id:
            return ServiceResult.failure(
                "workspace_not_selected",
                "Select a workspace before submitting chat input",
                meta={"service": "opentui", "operation": "submit", "route": route},
            ).to_dict()
        return AgentHarnessService(project_root).append_dialog_event(
            workspace_id, event="user_message", summary=value
        ).to_dict()
    if route == "log":
        return PermissionLogSystemService(project_root).write_log(value).to_dict()
    return ServiceResult.failure(
        "unsupported_route_submission",
        f"OpenTUI input submission is not defined for route: {route}",
        meta={"service": "opentui", "operation": "submit", "route": route},
    ).to_dict()


def bridge_request(request: dict[str, Any], project_root: str | Path) -> dict[str, Any]:
    operation = str(request.get("operation") or "")
    if operation == "catalog":
        return catalog_snapshot(project_root)
    if operation == "multi-agent":
        return multi_agent_operation(
            str(request.get("action") or "status"), project_root
        )
    if operation == "state":
        system = PermissionLogSystemService(project_root)
        if request.get("action") == "set":
            return system.set_runtime_state_value(
                str(request.get("key") or ""), request.get("value")
            ).to_dict()
        return system.runtime_state().to_dict()
    if operation == "activate":
        record = request.get("record")
        if not isinstance(record, dict):
            return ServiceResult.failure(
                "invalid_bridge_record",
                "OpenTUI activation record must be an object",
                meta={"service": "opentui", "operation": operation},
            ).to_dict()
        return activate_record(str(request.get("route") or ""), record, project_root)
    if operation == "submit":
        return submit_value(
            str(request.get("route") or ""),
            str(request.get("value") or ""),
            project_root,
        )
    return ServiceResult.failure(
        "unsupported_bridge_operation",
        f"Unsupported OpenTUI bridge operation: {operation}",
        meta={"service": "opentui", "operation": operation},
    ).to_dict()


def jsonl_bridge(project_root: str | Path) -> int:
    exit_code = 0
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("JSONL request must be an object")
            payload = bridge_request(request, project_root)
        except Exception as exc:
            payload = ServiceResult.failure(
                "invalid_bridge_request", str(exc), meta={"service": "opentui"}
            ).to_dict()
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        if not payload["ok"]:
            exit_code = 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 2 and argv[0] == "--jsonl":
        return jsonl_bridge(argv[1])
    if len(argv) != 3 or argv[0] != "multi-agent":
        raise SystemExit(
            "usage: service_bridge multi-agent <status|enable|disable> <root>"
        )
    payload = multi_agent_operation(argv[1], argv[2])
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
