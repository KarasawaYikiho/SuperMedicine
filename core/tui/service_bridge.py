"""JSON subprocess bridge from the Bun OpenTUI shell to application services."""

from __future__ import annotations

import json
import re
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
from core.redaction import redact_sensitive


_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_ROUTE_LABELS = {
    "chat": "对话",
    "dashboard": "状态",
    "workspace": "工作区",
    "paper": "论文",
    "experience": "经验",
    "tool": "工具",
    "dialog": "对话历史",
    "llm": "模型",
    "experiment": "实验",
    "log": "日志",
    "permission": "权限",
    "self-evolution": "自进化",
    "diagnose": "诊断",
}
_DISPLAY_KEYS = {
    "chat": ("summary", "event", "title"),
    "workspace": ("name", "id"),
    "paper": ("title", "name", "id"),
    "experience": ("title", "name", "id"),
    "tool": ("name", "title", "id"),
    "dialog": ("summary", "event", "title"),
    "llm": ("provider", "model", "current"),
    "experiment": ("name", "title", "id", "status"),
    "log": ("title", "name", "status", "id"),
    "permission": ("mode_label", "mode", "enabled", "status"),
    "self-evolution": ("title", "name", "id", "status"),
    "diagnose": ("title", "name", "status", "message"),
}
_DISPLAY_VALUE_TRANSLATIONS = {
    "conservative": "保守模式",
    "full_access": "完全访问模式",
    "enabled": "已启用",
    "disabled": "未启用",
    "running": "运行中",
    "completed": "已完成",
    "failed": "失败",
    "pending": "等待中",
    "ready": "就绪",
}


def _configure_utf8_stdio() -> None:
    """Keep the JSONL protocol Unicode-safe on Windows and redirected pipes."""
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


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


def _records(result: ServiceResult[Any]) -> list[Any]:
    """Return real records only; empty/error state is carried as page metadata."""

    if not result.ok:
        return []
    data = result.data
    if isinstance(data, list):
        return data
    return [data] if data not in (None, {}, "") else []


def _page_notice(result: ServiceResult[Any]) -> str:
    if result.ok:
        return ""
    return "数据暂时无法读取，请稍后重试。"


def _first_page_notice(*results: ServiceResult[Any]) -> str:
    return next((notice for result in results if (notice := _page_notice(result))), "")


def _safe_label(value: Any, fallback: str) -> str:
    text = str(redact_sensitive(str(value)))
    text = _CONTROL_CHARACTERS.sub(" ", text)
    text = " ".join(text.split()).strip()
    return (text or fallback)[:160]


def _presentation_entry(route: str, record: Any) -> dict[str, Any]:
    fallback = f"{_ROUTE_LABELS.get(route, '页面')}记录"
    if isinstance(record, str):
        return {"label": _safe_label(record, fallback)}
    if not isinstance(record, dict):
        return {"label": fallback}

    parts: list[str] = []
    for key in _DISPLAY_KEYS.get(route, ("title", "name", "id", "status")):
        value = record.get(key)
        if isinstance(value, bool):
            if key == "current":
                value = "当前" if value else ""
            elif key == "enabled":
                value = "已启用" if value else "未启用"
            else:
                value = "是" if value else "否"
        if isinstance(value, str):
            value = _DISPLAY_VALUE_TRANSLATIONS.get(value.lower(), value)
        if isinstance(value, (str, int, float)) and str(value).strip():
            parts.append(_safe_label(value, fallback))
        if len(parts) == 2:
            break
    entry: dict[str, Any] = {"label": " · ".join(parts) or fallback}
    if route == "workspace" and record.get("id"):
        entry["activation"] = {"id": _safe_label(record["id"], "")}
    elif route == "llm" and record.get("provider"):
        entry["activation"] = {
            "provider": _safe_label(record["provider"], "")
        }
    return entry


def _present(route: str, records: list[Any]) -> list[dict[str, Any]]:
    return [_presentation_entry(route, record) for record in records]


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
    experiment_records = experiments.list_experiments()
    log_records = system.list_logs()
    permission_status = system.permission_status()
    multi_agent_status = system.multi_agent_status()
    evolution_records = ExperienceEvolutionService(root).list_evolution_artifacts()
    diagnostics = system.config_diagnostics()
    pages = {
        "chat": _present("chat", _records(dialog)),
        "dashboard": [
            {"label": f"工作区：{len(workspaces.data or []) if workspaces.ok else 0} 个"},
            {"label": f"可用插件：{sum(1 for value in capability_data.values() if isinstance(value, dict) and value.get('enabled'))} 个"},
            {"label": f"当前工作区：{_safe_label(workspace_id, '未选择') if workspace_id else '未选择'}"},
        ],
        "workspace": _present("workspace", _records(workspaces)),
        "paper": _present("paper", _records(papers)),
        "experience": _present("experience", _records(experiences)),
        "tool": _present("tool", _records(tools)),
        "dialog": _present("dialog", _records(dialog)),
        "llm": _present("llm", _llm_records(llm)),
        "experiment": _present("experiment", _records(experiment_records)),
        "log": _present("log", _records(log_records)),
        "permission": _present(
            "permission", _records(permission_status) + _records(multi_agent_status)
        ),
        "self-evolution": _present("self-evolution", _records(evolution_records)),
        "diagnose": _present("diagnose", _records(diagnostics)),
    }
    notice_results = {
        "chat": (dialog,),
        "dashboard": (runtime, workspaces, capabilities),
        "workspace": (workspaces,),
        "paper": (papers,),
        "experience": (experiences,),
        "tool": (tools,),
        "dialog": (dialog,),
        "llm": (llm,),
        "experiment": (experiment_records,),
        "log": (log_records,),
        "permission": (permission_status, multi_agent_status),
        "self-evolution": (evolution_records,),
        "diagnose": (diagnostics,),
    }
    notices = {
        route: notice
        for route, results in notice_results.items()
        if (notice := _first_page_notice(*results))
    }
    return ServiceResult.success(
        {
            "pages": pages,
            "notices": notices,
            "runtime_state": runtime_data,
            "capabilities": capability_data,
        },
        meta={"service": "opentui", "operation": "catalog_snapshot"},
    ).to_dict()


def _llm_records(result: ServiceResult[Any]) -> list[dict[str, Any]]:
    if not result.ok or not isinstance(result.data, dict):
        return []
    current = result.data.get("current_provider")
    providers = result.data.get("providers")
    if not isinstance(providers, dict) or not providers:
        return []
    return [
        {
            "provider": name,
            "model": values.get("model", ""),
            "current": name == current,
        }
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
    _configure_utf8_stdio()
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
