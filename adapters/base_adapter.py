"""平台适配器基类"""
from __future__ import annotations

import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


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

    def _tool_bash(self, params: dict[str, Any]) -> str:
        """执行 Shell 命令"""
        command = params.get("command", "")
        workdir = params.get("workdir", ".")
        timeout = self._normalize_timeout(params.get("timeout"), self.DEFAULT_TIMEOUT_SECONDS)
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=workdir, timeout=timeout,
            )
            return result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"

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

    def _tool_read(self, params: dict[str, Any]) -> str:
        """读取文件内容"""
        file_path = Path(params.get("filePath", ""))
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

    def _tool_write(self, params: dict[str, Any]) -> str:
        """写入文件"""
        file_path = Path(params.get("filePath", ""))
        content = params.get("content", "")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {file_path}"

    def _tool_edit(self, params: dict[str, Any]) -> str:
        """编辑文件（字符串替换）"""
        file_path = Path(params.get("filePath", ""))
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

    def _tool_glob(self, params: dict[str, Any]) -> str:
        """文件模式匹配"""
        pattern = params.get("pattern", "**/*")
        base_path = Path(params.get("path", "."))
        matches = sorted(base_path.rglob(pattern))
        return "\n".join(str(m) for m in matches[:200])  # Limit to 200

    def _tool_grep(self, params: dict[str, Any]) -> str:
        """内容搜索（正则）"""
        pattern = params.get("pattern", "")
        base_path = Path(params.get("path", "."))
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
