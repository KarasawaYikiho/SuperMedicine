"""OpenCode 平台适配器 — 工具方法继承自 BaseAdapter"""
from __future__ import annotations

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

    def __init__(self, orchestrator=None):
        self._orchestrator = orchestrator

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

        有 orchestrator 时执行真实 dispatch，否则降级到文件查找模式。
        """
        # 真实 Dispatch（需要 Orchestrator）
        if self._orchestrator is not None:
            try:
                return self._orchestrator.dispatch(agent_id, task)
            except KeyError:
                return {
                    "agent_id": agent_id,
                    "status": "error",
                    "message": f"Unknown agent: {agent_id}",
                }
            except Exception as e:
                return {
                    "agent_id": agent_id,
                    "status": "error",
                    "message": str(e),
                }

        # 降级路径（无 Orchestrator）
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
                "agent_context": agent_context[:500],  # Truncate for Response
            },
        }
