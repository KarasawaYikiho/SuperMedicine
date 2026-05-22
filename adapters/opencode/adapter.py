"""OpenCode 平台适配器 — 完整实现"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from adapters.base_adapter import BaseAdapter


class OpenCodeAdapter(BaseAdapter):
    """OpenCode 平台适配器

    将 SuperMedicine 的内部 API 映射到 OpenCode 平台的原生能力：
    - tool_call → OpenCode 原生工具 (bash, read, write, edit, glob, grep, skill, task)
    - skill_load → 加载 SuperMedicine 技能文件 (adapters/opencode/skills/*.md)
    - subagent_dispatch → 派发到 OpenCode 子代理 (Brain → Planner → Coder → Tester)
    """

    # Agent ID → OpenCode 角色映射
    AGENT_ROLE_MAP = {
        "alpha": "Brain/Planner",
        "beta": "Coder/Tester",
        "gamma": "Coder",
        "delta": "Brain",
    }

    @property
    def platform_name(self) -> str:
        return "opencode"

    # ── tool_call ──────────────────────────────────────────────

    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """调用 OpenCode 原生工具

        支持的 tool_id: bash, read, write, edit, glob, grep, skill, task
        """
        tool_handlers = {
            "bash": self._tool_bash,
            "read": self._tool_read,
            "write": self._tool_write,
            "edit": self._tool_edit,
            "glob": self._tool_glob,
            "grep": self._tool_grep,
            "skill": self._tool_skill,
            "task": self._tool_task,
        }
        handler = tool_handlers.get(tool_id)
        if handler is None:
            return {"status": "error", "tool": tool_id, "result": f"Unsupported tool: {tool_id}"}
        try:
            result = handler(params)
            return {"status": "ok", "tool": tool_id, "result": result}
        except Exception as e:
            return {"status": "error", "tool": tool_id, "result": str(e)}

    def _tool_bash(self, params: dict[str, Any]) -> str:
        """执行 shell 命令"""
        command = params.get("command", "")
        workdir = params.get("workdir", ".")
        timeout = params.get("timeout", 30)
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=workdir, timeout=timeout,
            )
            return result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s"

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
        return "\n".join(str(m) for m in matches[:200])  # limit to 200

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
        return "\n".join(results[:100])  # limit to 100 matches

    def _tool_skill(self, params: dict[str, Any]) -> str:
        """加载技能（委托给 skill_load）"""
        skill_name = params.get("name", "")
        return self.skill_load(skill_name)

    def _tool_task(self, params: dict[str, Any]) -> dict[str, Any]:
        """派发子代理任务（委托给 subagent_dispatch）"""
        agent_id = params.get("agent_id", params.get("subagent_type", "alpha"))
        task = params.get("task", params.get("prompt", ""))
        task_dict = task if isinstance(task, dict) else {"description": task}
        return self.subagent_dispatch(agent_id, task_dict)

    # ── skill_load ─────────────────────────────────────────────

    def skill_load(self, skill_name: str) -> str:
        """加载 SuperMedicine 技能文件

        从 adapters/opencode/skills/{skill_name}.md 读取技能内容。
        """
        adapter_dir = Path(__file__).parent
        skill_path = adapter_dir / "skills" / f"{skill_name}.md"

        if not skill_path.exists():
            # 尝试直接路径
            skill_path = Path(skill_name)
            if not skill_path.exists():
                return f"Skill not found: {skill_name}"

        try:
            return skill_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error loading skill {skill_name}: {e}"

    # ── subagent_dispatch ──────────────────────────────────────

    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """派发任务到 OpenCode 子代理

        根据 agent_id 查找对应的 Agent 定义文件，
        生成包含任务描述和 Agent 上下文的派发结果。
        """
        adapter_dir = Path(__file__).parent
        agent_path = adapter_dir / "agents" / f"{agent_id}.md"
        if not agent_path.exists():
            # 尝试名称映射
            name_map = {
                "alpha": "alpha-analyst.md",
                "beta": "beta-reviewer.md",
                "gamma": "gamma-writer.md",
                "delta": "delta-orchestrator.md",
            }
            mapped = name_map.get(agent_id, "")
            if mapped:
                agent_path = adapter_dir / "agents" / mapped

        agent_context = ""
        if agent_path.exists():
            agent_context = agent_path.read_text(encoding="utf-8")

        role = self.AGENT_ROLE_MAP.get(agent_id, "Unknown")

        return {
            "agent_id": agent_id,
            "status": "dispatched",
            "role": role,
            "task": task,
            "plan": {
                "workflow": "Brain → Planner → Coder → Tester",
                "agent_context": agent_context[:500],  # truncate for response
            },
        }
