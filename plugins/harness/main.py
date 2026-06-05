"""Executable entrypoint for the harness-core manifest plugin."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plugins.base_plugin import plugin_result
from plugins.harness.checkpoint_verifier import CheckpointVerifier
from plugins.harness.monitor import AgentMonitor, AgentPerformanceMonitor
from plugins.tools._common import required_str


PLUGIN_NAME = "harness-core"

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "harness.integration.checkpoint": {
        "required_params": {"checkpoint_dir": "str", "task_id": "str"},
        "output_fields": [
            "task_id",
            "total_steps",
            "steps",
            "missing_steps",
            "complete",
            "structurally_complete",
            "final_state_success",
            "warnings",
        ],
    },
    "harness.integration.checkpoint_all": {
        "required_params": {"checkpoint_dir": "str"},
        "output_fields": ["results", "total_tasks"],
    },
    "harness.monitor.permission_audit": {
        "required_params": {"audit_log_path": "str"},
        "optional_params": {"agent_id": "str"},
        "output_fields": ["entries", "total", "warnings"],
    },
    "harness.monitor.denied_actions": {
        "required_params": {"audit_log_path": "str"},
        "output_fields": ["entries", "total", "warnings"],
    },
    "harness.monitor.anomaly": {
        "required_params": {"audit_log_path": "str"},
        "optional_params": {"anomaly_threshold": "int"},
        "output_fields": ["anomalies", "total", "warnings"],
    },
    "harness.monitor.performance": {
        "required_params": {"performance_log_path": "str"},
        "optional_params": {"agent_id": "str"},
        "output_fields": ["stats", "warnings"],
    },
    "harness.monitor.failure_patterns": {
        "required_params": {"performance_log_path": "str"},
        "optional_params": {"agent_id": "str"},
        "output_fields": ["failures", "total", "warnings"],
    },
}


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute supported harness actions using existing harness components."""
    params = params or {}
    context = context or {}
    metadata = _base_metadata(context)

    try:
        if action == "harness.integration.checkpoint":
            output = _execute_checkpoint(params)
        elif action == "harness.integration.checkpoint_all":
            output = _execute_checkpoint_all(params)
        elif action == "harness.monitor.permission_audit":
            output = _execute_permission_audit(params)
        elif action == "harness.monitor.denied_actions":
            output = _execute_denied_actions(params)
        elif action == "harness.monitor.anomaly":
            output = _execute_anomaly(params)
        elif action == "harness.monitor.performance":
            output = _execute_performance(params)
        elif action == "harness.monitor.failure_patterns":
            output = _execute_failure_patterns(params)
        else:
            return plugin_result(
                status="plugin_error",
                plugin=PLUGIN_NAME,
                action=action,
                error=f"Unsupported harness-core action: {action}",
                metadata=metadata,
            )
    except (TypeError, ValueError) as exc:
        return plugin_result(
            status="plugin_error",
            plugin=PLUGIN_NAME,
            action=action,
            error=f"Invalid harness-core input: {exc}",
            metadata=metadata,
        )

    return plugin_result(
        status="success",
        plugin=PLUGIN_NAME,
        action=action,
        output=output,
        metadata=metadata,
    )


def _execute_checkpoint(params: dict[str, Any]) -> dict[str, Any]:
    checkpoint_dir = _required_path(params, "checkpoint_dir")
    task_id = required_str(params, "task_id")
    return CheckpointVerifier(checkpoint_dir).verify(task_id)


def _execute_checkpoint_all(params: dict[str, Any]) -> dict[str, Any]:
    checkpoint_dir = _required_path(params, "checkpoint_dir")
    results = CheckpointVerifier(checkpoint_dir).verify_all()
    return {"results": results, "total_tasks": len(results)}


def _execute_permission_audit(params: dict[str, Any]) -> dict[str, Any]:
    audit_log_path = _required_path(params, "audit_log_path")
    agent_id = _optional_str(params, "agent_id")
    monitor = AgentMonitor(audit_log_path)
    entries = monitor.get_permission_audit(agent_id=agent_id)
    return {"entries": entries, "total": len(entries), "warnings": monitor.warnings}


def _execute_denied_actions(params: dict[str, Any]) -> dict[str, Any]:
    audit_log_path = _required_path(params, "audit_log_path")
    monitor = AgentMonitor(audit_log_path)
    entries = monitor.get_denied_actions()
    return {"entries": entries, "total": len(entries), "warnings": monitor.warnings}


def _execute_anomaly(params: dict[str, Any]) -> dict[str, Any]:
    audit_log_path = _required_path(params, "audit_log_path")
    threshold = _optional_positive_int(params, "anomaly_threshold", default=100)
    monitor = AgentMonitor(audit_log_path, anomaly_threshold=threshold)
    anomalies = monitor.detect_anomalies()
    return {
        "anomalies": anomalies,
        "total": len(anomalies),
        "warnings": monitor.warnings,
    }


def _execute_performance(params: dict[str, Any]) -> dict[str, Any]:
    performance_log_path = _required_path(params, "performance_log_path")
    agent_id = _optional_str(params, "agent_id")
    monitor = AgentPerformanceMonitor(performance_log_path, create_parent=False)
    stats = monitor.get_stats(agent_id=agent_id)
    return {"stats": stats, "warnings": monitor.warnings}


def _execute_failure_patterns(params: dict[str, Any]) -> dict[str, Any]:
    performance_log_path = _required_path(params, "performance_log_path")
    agent_id = _optional_str(params, "agent_id")
    monitor = AgentPerformanceMonitor(performance_log_path, create_parent=False)
    failures = monitor.detect_failure_patterns(agent_id=agent_id)
    return {"failures": failures, "total": len(failures), "warnings": monitor.warnings}


def _base_metadata(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource": {"kind": "harness", "plugin": PLUGIN_NAME},
        "security": {
            "permission_entrypoint": "kernel",
            "permission_checked": bool(context),
        },
        "contract": {"actions": ACTION_CONTRACTS, "provider_contract": "harness-core"},
        "audit": {"context_keys": sorted(context.keys())},
    }


def _required_path(params: dict[str, Any], key: str) -> Path:
    value = params.get(key)
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError(f"{key} must be a non-empty path string")
    if isinstance(value, str) and any(ch in value for ch in "\x00\r\n"):
        raise ValueError(f"{key} must not contain control characters")
    return Path(value)


def _optional_str(params: dict[str, Any], key: str) -> str | None:
    value = params.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string when provided")
    return value


def _optional_positive_int(params: dict[str, Any], key: str, *, default: int) -> int:
    value = params.get(key, default)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value
