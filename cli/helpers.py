"""CLI module-level helper functions — conversions, parsing, JSON loading, formatting."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, cast

from core.redaction import redact_sensitive

logger = logging.getLogger(__name__)

PERMISSION_RISK_NOTICE = (
    "风险提示：默认保守模式只允许项目内访问；完全访问模式仅使用当前进程/当前用户"
    "已经拥有的系统权限，不会静默提权、不会绕过系统权限。若系统权限不足，请通过"
    "管理员身份运行或操作系统 UAC/安全提示进行显式授权。"
)

def _self_evolution_cli_result(
    result: dict[str, Any],
    *,
    requested_access_mode: str,
    requested_output: str | Path,
    audit_log: Path,
    preview: bool,
    confirm_write: bool,
    confirm_full_access: bool,
    acknowledge_risk: bool,
) -> dict[str, Any]:
    raw_plan = result.get("plan")
    plan: dict[str, Any] = (
        cast(dict[str, Any], raw_plan) if isinstance(raw_plan, dict) else {}
    )
    raw_artifacts = result.get("artifacts")
    artifacts: list[Any] = (
        cast(list[Any], raw_artifacts) if isinstance(raw_artifacts, list) else []
    )
    files: list[dict[str, Any]] = []
    for artifact in artifacts:
        if isinstance(artifact, dict):
            files.append(
                {
                    "path": artifact.get("path"),
                    "description": artifact.get("description", ""),
                    "exists": bool(artifact.get("exists", False)),
                    "operation": "modify" if artifact.get("exists") else "create",
                }
            )
    errors = [str(error) for error in result.get("errors", [])]
    status = str(result.get("status", "failed"))
    full_access_requested = str(requested_access_mode).strip().lower() == "full"
    next_steps = []
    if preview:
        next_steps.append(
            "Review the listed file changes; no files were written in preview mode."
        )
        next_steps.append(
            "Run again with --confirm-write and without --preview to write approved files."
        )
    if status == "failed":
        next_steps.append(
            "Fix the failure reason, choose an allowed target path, or reduce access scope."
        )
    if full_access_requested and not (confirm_full_access and acknowledge_risk):
        next_steps.append(
            "For full access writes, pass both --confirm-full-access and --acknowledge-risk after explicit authorization."
        )
    if status == "success":
        next_steps.append(
            "Inspect generated artifacts before adopting them into the workflow."
        )
    return cast(
        dict[str, Any],
        redact_sensitive(
            {
                "status": status,
                "permission_mode": requested_access_mode,
                "target_path": plan.get("target", str(requested_output)),
                "preview": preview,
                "confirm_write": confirm_write,
                "files_to_create_or_modify": files,
                "audit_log": {
                    "path": str(audit_log),
                    "available": audit_log.exists() or not preview,
                    "note": "Audit log is written for confirmed permission-gated writes when available.",
                },
                "failure_reason": "; ".join(errors) if errors else "",
                "message": result.get("message", ""),
                "full_access_notice": {
                    "full_access_requested": full_access_requested,
                    "explicit_full_access_confirmed": confirm_full_access,
                    "risk_notice_acknowledged": acknowledge_risk,
                    "semantics": (
                        "Full access uses only current user/process permissions and never "
                        "silently elevates, bypasses UAC, or bypasses operating-system "
                        "security controls."
                    ),
                },
                "next_steps": next_steps,
                "service_result": result,
            }
        ),
    )


def _paper_metadata_options(args) -> dict:
    metadata: dict = {}
    for field in ("title", "doi", "pmid", "notes"):
        value = getattr(args, field, None)
        if value is not None:
            metadata[field] = value
    tags = getattr(args, "tag", None)
    if tags is not None:
        metadata["tags"] = tags
    return metadata


def _load_params_json(raw_json: str) -> dict:
    """Parse structured plugin params from a JSON object string."""
    try:
        params = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--params-json must be valid JSON: {exc.msg}") from exc

    if not isinstance(params, dict):
        raise ValueError("plugin params must be a JSON object")
    return params


def _load_params_file(path: str) -> dict:
    """Read structured plugin params from a JSON object file."""
    params_path = Path(path)
    try:
        raw_json = params_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"--params-file could not be read: {exc}") from exc
    try:
        return _load_params_json(raw_json)
    except ValueError as exc:
        raise ValueError(f"--params-file {params_path}: {exc}") from exc


def _resolve_run_params(
    params_json: str | None, params_file: str | None
) -> dict | None:
    """Resolve optional structured params for the run command."""
    if params_json and params_file:
        raise ValueError("--params-json and --params-file cannot be used together")
    if params_json:
        return _load_params_json(params_json)
    if params_file:
        return _load_params_file(params_file)
    return None


def _permission_result(
    file_access: dict[str, Any],
    *,
    changed: bool,
    message: str | None = None,
) -> dict[str, Any]:
    mode = str(file_access.get("mode", "conservative"))
    mode_labels = {
        "sandbox": "沙箱",
        "safe": "沙箱",
        "conservative": "保守",
        "full": "完全访问",
    }
    return {
        "mode": mode,
        "mode_label": mode_labels.get(mode, "保守"),
        "full_mode_confirmed": bool(file_access.get("full_mode_confirmed")),
        "authorized_external_roots": list(
            file_access.get("authorized_external_roots", [])
        ),
        "changed": changed,
        "runtime_effect": "后续策略读取即时生效；已创建的独立策略对象需重新读取配置。",
        "risk_notice": PERMISSION_RISK_NOTICE,
        "message": message or "当前权限模式配置。",
    }


def _confirm_full_access_interactively() -> bool:
    if not sys.stdin.isatty():
        return False
    logger.warning(PERMISSION_RISK_NOTICE)
    logger.warning("请输入 FULL 确认切换到完全访问模式：")
    try:
        answer = input().strip()
    except EOFError:
        return False
    return answer == "FULL"


def _parse_llm_headers(
    header_items: list[str] | None, headers_json: str | None
) -> dict[str, str]:
    """Resolve LLM headers from repeated key=value args and optional JSON object."""
    headers: dict[str, str] = {}
    if headers_json:
        try:
            parsed = json.loads(headers_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--headers-json must be valid JSON: {exc.msg}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("--headers-json must be a JSON object")
        headers.update({str(key): str(value) for key, value in parsed.items()})
    for item in header_items or []:
        if "=" not in item:
            raise ValueError("--header must use KEY=VALUE format")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("--header key cannot be empty")
        headers[key] = value
    return headers
