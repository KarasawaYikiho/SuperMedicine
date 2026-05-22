"""Standalone 适配器 — 自包含实现"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from adapters.base_adapter import BaseAdapter


class StandaloneAdapter(BaseAdapter):
    """Standalone 平台适配器 — 无需外部 AI 平台即可运行"""

    @property
    def platform_name(self) -> str:
        return "standalone"

    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """调用本地工具"""
        handlers = {
            "bash": self._tool_bash,
            "read": self._tool_read,
            "write": self._tool_write,
            "edit": self._tool_edit,
            "glob": self._tool_glob,
            "grep": self._tool_grep,
            "skill": self._tool_skill,
            "task": self._tool_task,
        }
        handler = handlers.get(tool_id)
        if handler is None:
            return {"status": "error", "tool": tool_id, "result": f"Unsupported: {tool_id}"}
        try:
            result = handler(params)
            return {"status": "ok", "tool": tool_id, "result": result}
        except Exception as e:
            return {"status": "error", "tool": tool_id, "result": str(e)}

    def _tool_bash(self, params: dict[str, Any]) -> str:
        cmd = params.get("command", "")
        timeout = params.get("timeout", 30)
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return r.stdout or r.stderr
        except subprocess.TimeoutExpired:
            return f"Timeout after {timeout}s"

    def _tool_read(self, params: dict[str, Any]) -> str:
        fp = Path(params.get("filePath", ""))
        if not fp.exists():
            return f"Not found: {fp}"
        try:
            return fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return fp.read_text(encoding="latin-1")

    def _tool_write(self, params: dict[str, Any]) -> str:
        fp = Path(params.get("filePath", ""))
        content = params.get("content", "")
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {fp}"

    def _tool_edit(self, params: dict[str, Any]) -> str:
        fp = Path(params.get("filePath", ""))
        old = params.get("oldString", "")
        new = params.get("newString", "")
        replace_all = params.get("replaceAll", False)
        if not fp.exists():
            return f"Not found: {fp}"
        content = fp.read_text(encoding="utf-8")
        if replace_all:
            content = content.replace(old, new)
        else:
            count = content.count(old)
            if count == 0:
                return "oldString not found"
            if count > 1:
                return f"Found {count} matches, use replaceAll"
            content = content.replace(old, new, 1)
        fp.write_text(content, encoding="utf-8")
        return f"Edited {fp}"

    def _tool_glob(self, params: dict[str, Any]) -> str:
        pattern = params.get("pattern", "**/*")
        base = Path(params.get("path", "."))
        matches = sorted(base.rglob(pattern))
        return "\n".join(str(m) for m in matches[:200])

    def _tool_grep(self, params: dict[str, Any]) -> str:
        pattern = params.get("pattern", "")
        base = Path(params.get("path", "."))
        include = params.get("include", "*")
        results = []
        for fp in base.rglob(include):
            if not fp.is_file():
                continue
            try:
                for i, line in enumerate(fp.read_text(encoding="utf-8").splitlines(), 1):
                    if re.search(pattern, line):
                        results.append(f"{fp}:{i}: {line.strip()[:120]}")
            except Exception:
                continue
        return "\n".join(results[:100])

    def _tool_skill(self, params: dict[str, Any]) -> str:
        return self.skill_load(params.get("name", ""))

    def _tool_task(self, params: dict[str, Any]) -> dict[str, Any]:
        agent_id = params.get("agent_id", "standalone")
        task = params.get("task", params.get("prompt", ""))
        return self.subagent_dispatch(agent_id, task if isinstance(task, dict) else {"description": task})

    def skill_load(self, skill_name: str) -> str:
        """从本地加载技能文件"""
        adapter_dir = Path(__file__).parent.parent
        skill_path = adapter_dir / "opencode" / "skills" / f"{skill_name}.md"
        if skill_path.exists():
            return skill_path.read_text(encoding="utf-8")
        return f"Skill not found: {skill_name}"

    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """进程内模拟 Dispatch"""
        return {
            "agent_id": agent_id,
            "status": "dispatched",
            "platform": "standalone",
            "task": task,
            "message": f"Task dispatched to {agent_id} in standalone mode",
        }
