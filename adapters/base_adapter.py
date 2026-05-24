"""平台适配器基类"""
from __future__ import annotations

import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from permission.engine import PermissionEngine
from permission.policy import DEFAULT_POLICY_RELATIVE_PATH, PermissionResult


SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|credential)\s*[:=]\s*([^\s,;&]+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+\-/=]+)"),
)


def redact_sensitive(value: Any) -> Any:
    """Return a copy of value with common secret-like payloads redacted."""
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text.endswith("_env"):
                redacted[key] = item
            elif any(marker in key_text for marker in ("api_key", "apikey", "token", "secret", "password", "credential")):
                redacted[key] = "[REDACTED]" if item not in (None, "") else item
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, str):
        text = value
        for pattern in SENSITIVE_VALUE_PATTERNS:
            text = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
        return text
    return value


class BaseAdapter(ABC):
    """平台适配器基类 — 提供共享工具方法实现"""

    DEFAULT_TIMEOUT_SECONDS = 30
    MAX_TIMEOUT_SECONDS = 120
    PERMISSION_GATED_TOOLS = {"bash", "write", "edit"}

    def __init__(
        self,
        permission_engine: PermissionEngine | None = None,
        project_dir: Path | None = None,
        default_agent_id: str = "alpha",
    ):
        self._permission_engine = permission_engine
        self._project_dir = (Path.cwd() if project_dir is None else Path(project_dir)).resolve()
        self._default_agent_id = default_agent_id

    @property
    @abstractmethod
    def platform_name(self) -> str: ...

    @abstractmethod
    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def skill_load(self, skill_name: str) -> str: ...

    @abstractmethod
    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]: ...

    # ── 共享工具方法 ──────────────────────────────────────────

    def _tool_bash(self, params: dict[str, Any]) -> str | dict[str, Any]:
        """执行 Shell 命令"""
        command = params.get("command", "")
        workdir = self._resolve_sandbox_path(params.get("workdir", "."), resource_label="bash_workdir", must_exist=True)
        if isinstance(workdir, dict):
            return workdir
        timeout = self._normalize_timeout(params.get("timeout"), self.DEFAULT_TIMEOUT_SECONDS)
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=workdir, timeout=timeout,
            )
            return result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"

    def _execute_permissioned_tool_call(
        self,
        *,
        tool_id: str,
        params: dict[str, Any],
        handlers: dict[str, Any],
        unsupported_message: str,
    ) -> dict[str, Any]:
        handler = handlers.get(tool_id)
        if handler is None:
            return {"status": "error", "tool": tool_id, "result": unsupported_message}
        denied = self._tool_permission_denied(tool_id, params)
        if denied is not None:
            return denied
        try:
            result = handler(params)
            if isinstance(result, dict) and result.get("status") in {"denied", "error"}:
                result.setdefault("tool", tool_id)
                return result
            return {"status": "ok", "tool": tool_id, "result": result}
        except Exception as e:
            return {"status": "error", "tool": tool_id, "result": str(e)}

    def _tool_permission_denied(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if tool_id not in self.PERMISSION_GATED_TOOLS:
            return None

        engine = self._get_permission_engine()
        agent_id = str(params.get("agent_id") or self._default_agent_id)
        resource = self._tool_permission_resource(tool_id, params)
        context: dict[str, Any] = {
            "adapter": self.platform_name,
            "tool": tool_id,
            "resource": resource,
            "policy_path": str(self._project_dir / DEFAULT_POLICY_RELATIVE_PATH),
            "project_dir": str(self._project_dir),
            "permission_scope": "adapter_tool_call",
        }
        if tool_id == "bash":
            context["requires_shell"] = True
            context["command"] = redact_sensitive(str(params.get("command", "")))
            context["workdir"] = str(params.get("workdir", "."))
            context["risk"] = "high"
        if tool_id in {"write", "edit"}:
            context["mutates_file"] = True
            context["risk"] = "high"

        if engine is None:
            if tool_id == "bash":
                return self._permission_denied_result(tool_id, agent_id, "tool_call", resource, reason="permission_engine_unavailable")
            return None

        result = engine.check(agent_id, "tool_call", resource, context=context)
        if result == PermissionResult.ALLOWED:
            return None
        return self._permission_denied_result(tool_id, agent_id, "tool_call", resource)

    def _get_permission_engine(self) -> PermissionEngine | None:
        if self._permission_engine is not None:
            return self._permission_engine
        policy_dir = self._project_dir / DEFAULT_POLICY_RELATIVE_PATH.parent
        try:
            self._permission_engine = PermissionEngine(policy_dir, policy_dir / "audit.jsonl")
        except Exception:
            return None
        return self._permission_engine

    def _tool_permission_resource(self, tool_id: str, params: dict[str, Any]) -> str:
        if tool_id == "bash":
            return "bash"
        file_path = params.get("filePath") or params.get("path") or tool_id
        if file_path in (None, ""):
            return tool_id
        try:
            return str(Path(file_path))
        except TypeError:
            return str(file_path)

    def _permission_denied_result(
        self,
        tool_id: str,
        agent_id: str,
        action: str,
        resource: str,
        *,
        reason: str = "permission_denied",
    ) -> dict[str, Any]:
        return {
            "status": "denied",
            "tool": tool_id,
            "agent": agent_id,
            "action": action,
            "resource": resource,
            "result": "Permission denied by canonical policy chain.",
            "error": "Permission denied by canonical policy chain.",
            "error_code": reason,
            "metadata": {
                "policy_path": str(self._project_dir / DEFAULT_POLICY_RELATIVE_PATH),
                "security": {"permission": "denied", "permission_checked": True},
            },
        }

    def _sandbox_denied_result(self, *, tool_id: str, resource: str, message: str) -> dict[str, Any]:
        return {
            "status": "denied",
            "tool": tool_id,
            "resource": resource,
            "result": message,
            "error": message,
            "error_code": "sandbox_denied",
            "metadata": {
                "project_dir": str(self._project_dir),
                "security": {"sandbox": "project_root", "permission_checked": False},
            },
        }

    def _resolve_sandbox_path(
        self,
        path_value: Any,
        *,
        resource_label: str,
        must_exist: bool = False,
    ) -> Path | dict[str, Any]:
        raw_path = "." if path_value in (None, "") else path_value
        try:
            candidate = Path(raw_path)
        except TypeError:
            return self._sandbox_denied_result(
                tool_id=resource_label,
                resource=str(raw_path),
                message=f"Invalid path for project sandbox: {raw_path}",
            )

        if not candidate.is_absolute():
            candidate = self._project_dir / candidate

        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            return self._resource_error(
                status="error",
                resource=str(raw_path),
                message=f"Unable to resolve path inside project sandbox: {exc}",
                metadata={"project_dir": str(self._project_dir), "security": {"sandbox": "project_root"}},
            )

        try:
            resolved.relative_to(self._project_dir)
        except ValueError:
            return self._sandbox_denied_result(
                tool_id=resource_label,
                resource=str(raw_path),
                message=f"Path is outside project root sandbox: {raw_path}",
            )
        if must_exist and not resolved.exists():
            return self._resource_error(
                status="error",
                resource=str(raw_path),
                message=f"Path not found inside project sandbox: {raw_path}",
                metadata={"project_dir": str(self._project_dir), "security": {"sandbox": "project_root"}},
            )
        return resolved

    def _normalize_timeout(self, requested: Any, default: int | float | None = None) -> float:
        """Clamp timeout values to a practical adapter-wide range."""
        fallback = self.DEFAULT_TIMEOUT_SECONDS if default is None else default
        try:
            timeout = float(fallback if requested is None else requested)
        except (TypeError, ValueError):
            timeout = float(fallback)
        if timeout <= 0:
            timeout = float(fallback)
        return min(timeout, float(self.MAX_TIMEOUT_SECONDS))

    def _resource_error(
        self,
        *,
        status: str,
        resource: str,
        message: str,
        retryable: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a structured, redacted adapter resource/security error."""
        return {
            "status": status,
            "resource": resource,
            "error": redact_sensitive(message),
            "error_code": status,
            "retryable": retryable,
            "metadata": redact_sensitive(metadata or {}),
        }

    def _tool_read(self, params: dict[str, Any]) -> str | dict[str, Any]:
        """读取文件内容"""
        file_path = self._resolve_sandbox_path(params.get("filePath", ""), resource_label="read")
        if isinstance(file_path, dict):
            return file_path
        if not file_path.exists():
            return f"File not found: {file_path}"
        try:
            content = file_path.read_text(encoding="utf-8")
            offset = params.get("offset", 0)
            limit = params.get("limit")
            lines = content.splitlines()
            if offset > 0:
                lines = lines[offset - 1:]
            if limit is not None:
                lines = lines[:limit]
            return "\n".join(lines)
        except UnicodeDecodeError:
            return file_path.read_text(encoding="latin-1")

    def _tool_write(self, params: dict[str, Any]) -> str | dict[str, Any]:
        """写入文件"""
        file_path = self._resolve_sandbox_path(params.get("filePath", ""), resource_label="write")
        if isinstance(file_path, dict):
            return file_path
        content = params.get("content", "")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {file_path}"

    def _tool_edit(self, params: dict[str, Any]) -> str | dict[str, Any]:
        """编辑文件（字符串替换）"""
        file_path = self._resolve_sandbox_path(params.get("filePath", ""), resource_label="edit")
        if isinstance(file_path, dict):
            return file_path
        old_string = params.get("oldString", "")
        new_string = params.get("newString", "")
        replace_all = params.get("replaceAll", False)

        if not file_path.exists():
            return f"File not found: {file_path}"

        content = file_path.read_text(encoding="utf-8")
        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            count = content.count(old_string)
            if count == 0:
                return f"oldString not found in {file_path}"
            if count > 1:
                return f"Found {count} matches for oldString. Use replaceAll or provide more context."
            new_content = content.replace(old_string, new_string, 1)

        file_path.write_text(new_content, encoding="utf-8")
        return f"Edited {file_path}: replaced '{old_string[:50]}...'"

    def _tool_glob(self, params: dict[str, Any]) -> str | dict[str, Any]:
        """文件模式匹配"""
        pattern = params.get("pattern", "**/*")
        base_path = self._resolve_sandbox_path(params.get("path", "."), resource_label="glob", must_exist=True)
        if isinstance(base_path, dict):
            return base_path
        matches = sorted(base_path.rglob(pattern))
        return "\n".join(str(m) for m in matches[:200])  # Limit to 200

    def _tool_grep(self, params: dict[str, Any]) -> str | dict[str, Any]:
        """内容搜索（正则）"""
        pattern = params.get("pattern", "")
        base_path = self._resolve_sandbox_path(params.get("path", "."), resource_label="grep", must_exist=True)
        if isinstance(base_path, dict):
            return base_path
        include = params.get("include", "*")
        results = []
        for file_path in base_path.rglob(include):
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(pattern, line):
                        results.append(f"{file_path}:{i}: {line.strip()[:120]}")
            except (UnicodeDecodeError, OSError):
                continue
        return "\n".join(results[:100])  # Limit to 100 matches
