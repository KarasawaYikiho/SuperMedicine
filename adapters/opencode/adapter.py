"""Optional OpenCode platform adapter.

This module is an add-on integration surface around the standalone
SuperMedicine core.  It must not be required for core runtime execution, and
it only reports native OpenCode sub-agent behavior when an explicit
orchestrator/runtime bridge is supplied by the caller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.base_adapter import BaseAdapter
from core.redaction import redact_sensitive
from permission.engine import PermissionEngine


class OpenCodeAdapter(BaseAdapter):
    """OpenCode 平台适配器（可选附加层）

    将 SuperMedicine 的内部 API 映射到 OpenCode 插件/文件能力，并仅暴露
    `SuperMedicine` 作为平台用户可见 Agent：
    - tool_call → OpenCode 原生工具 (bash, read, write, edit, glob, grep, skill, task)
    - skill_load → 加载 SuperMedicine 技能文件 (adapters/opencode/skills/*.md)
    - subagent_dispatch → 仅在注入 orchestrator 时执行；否则返回 structured degraded
      状态和本地非用户可见 role context 文档上下文，不声称原生 OpenCode 子代理运行时已执行。
    """

    SUPPORTED_TOOLS = {
        "bash",
        "read",
        "write",
        "edit",
        "glob",
        "grep",
        "skill",
        "task",
        "opencode.capabilities",
    }

    SKILL_FILES = {
        "rag-query": "rag-query.md",
        "harness-monitor": "harness-monitor.md",
        "medical-writing": "medical-writing.md",
        "medical-citation": "medical-citation.md",
        "python-stats": "python-stats.md",
        "r-survival": "r-survival.md",
    }

    AGENT_FILES = {
        "alpha": "alpha-analyst.md",
        "beta": "beta-reviewer.md",
        "gamma": "gamma-writer.md",
        "delta": "delta-orchestrator.md",
    }

    USER_FACING_AGENT = {
        "name": "SuperMedicine",
        "id": "supermedicine",
        "file": "supermedicine.md",
    }

    AI_PROVIDER_SUPPORT = {
        "config_sources": [
            "Installer/runtime injection flags: Install.py --provider <any-name> --base-url <url> --api-key <secret> --model <model>",
            "Generic environment variables: SM_LLM_PROVIDER, SM_LLM_BASE_URL, SM_LLM_API_KEY, SM_LLM_MODEL",
            "Provider environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY",
            "Project-local config: .supermedicine/config.yaml llm.provider and llm.providers.*",
        ],
        "supported_api_formats": {
            "openai": {
                "api_format": "openai",
                "default_base_url": "https://api.openai.com/v1",
                "provider_key_env": "OPENAI_API_KEY",
                "generic_key_env": "SM_LLM_API_KEY",
                "custom_base_url": True,
            },
            "anthropic": {
                "api_format": "anthropic",
                "default_base_url": "https://api.anthropic.com/v1",
                "provider_key_env": "ANTHROPIC_API_KEY",
                "generic_key_env": "SM_LLM_API_KEY",
                "custom_base_url": True,
            },
            "openrouter": {
                "api_format": "openai",
                "default_base_url": "https://openrouter.ai/api/v1",
                "provider_key_env": "OPENROUTER_API_KEY",
                "generic_key_env": "SM_LLM_API_KEY",
                "custom_base_url": True,
            },
        },
        "custom_base_url": True,
        "secret_redaction": {
            "required": True,
            "redacted_value": "<redacted>",
            "plain_text_keys_in_manifest_or_docs": False,
        },
        "degraded_without_orchestrator": True,
        "boundary": "Optional add-on; provider config is supplied by installer/runtime/project config and is visible only through the SuperMedicine OpenCode agent surface.",
    }

    def __init__(
        self,
        orchestrator=None,
        permission_engine: PermissionEngine | None = None,
        project_dir: Path | None = None,
        default_agent_id: str = "beta",
    ):
        super().__init__(
            permission_engine=permission_engine,
            project_dir=project_dir,
            default_agent_id=default_agent_id,
        )
        self._orchestrator = orchestrator

    # Runtime ID → SuperMedicine role-position mapping
    AGENT_ROLE_MAP = {
        "alpha": "Research analysis and planning",
        "beta": "Quality review and verification",
        "gamma": "Manuscript composition and formatting",
        "delta": "Workflow coordination and dispatch",
    }

    @property
    def platform_name(self) -> str:
        return "opencode"

    @property
    def registration(self) -> dict[str, Any]:
        """Return adapter discovery metadata for registries and callers."""
        return {
            "platform": self.platform_name,
            "adapter_class": self.__class__.__name__,
            "status": "optional_add_on",
            "optional": True,
            "core": False,
            "default": False,
            "module": "adapters.opencode.adapter",
            "capability_tool": "opencode.capabilities",
            "requires_core_runtime": False,
            "ai_provider_support": self.AI_PROVIDER_SUPPORT,
            "limitations": [
                "Optional add-on; not imported, initialized, or probed by default.",
                "Native OpenCode dispatch requires an explicit orchestrator/runtime bridge.",
                "Only SuperMedicine is exposed as a user-facing platform agent; alpha/beta/gamma/delta files are internal role context only.",
            ],
        }

    def capabilities(self) -> dict[str, Any]:
        """Report OpenCode adapter features and limitations truthfully."""
        return {
            "platform": self.platform_name,
            "status": "available" if self._orchestrator is not None else "degraded",
            "optional_add_on": True,
            "supported_tools": sorted(self.SUPPORTED_TOOLS),
            "features": {
                "registration_discovery": True,
                "capability_reporting": True,
                "permission_checked_dangerous_tools": True,
                "project_root_sandbox": True,
                "adapter_skill_file_load": True,
                "agent_context_file_load": True,
                "orchestrator_backed_dispatch": self._orchestrator is not None,
                "native_opencode_subagent_runtime": False,
                "core_runtime_dependency": False,
                "ai_provider_config_discovery": True,
                "ai_provider_secret_redaction": True,
                "custom_ai_provider_base_url": True,
            },
            "ai_provider": self.AI_PROVIDER_SUPPORT,
            "user_facing_agents": [self.USER_FACING_AGENT],
            "internal_role_contexts": sorted(self.AGENT_FILES.values()),
            "limits": [
                "OpenCode support is optional add-on content and is not required by the standalone core.",
                "Without an injected orchestrator/runtime bridge, subagent_dispatch returns a degraded context result instead of executing a native OpenCode sub-agent.",
                "OpenCode exposes exactly one user-facing agent: SuperMedicine; α/β/γ/δ are non-user-facing role contexts/capabilities.",
                "Dangerous tools remain permission-checked before execution through the canonical policy chain.",
            ],
        }

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
            "opencode.capabilities": lambda _params: self.capabilities(),
        }
        result = self._execute_permissioned_tool_call(
            tool_id=tool_id,
            params=params,
            handlers=tool_handlers,
            unsupported_message=f"Unsupported tool: {tool_id}",
        )
        if (
            tool_id == "task"
            and result.get("status") == "ok"
            and isinstance(result.get("result"), dict)
            and result["result"].get("status") in {"degraded", "unavailable"}
        ):
            degraded = result["result"]
            degraded.setdefault("tool", tool_id)
            return degraded
        return result

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

        从 adapters/opencode/skills/{skill_name}.md 读取声明过的技能内容。
        """
        adapter_dir = Path(__file__).parent
        requested = Path(str(skill_name)).name
        requested_stem = requested[:-3] if requested.endswith(".md") else requested
        skill_file = self.SKILL_FILES.get(requested_stem)

        if skill_file is None:
            return f"Skill not found: {skill_name}"

        skill_path = adapter_dir / "skills" / skill_file
        if not skill_path.exists():
            return f"Skill unavailable: declared OpenCode skill file is missing: {skill_file}"

        try:
            return skill_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error loading skill {skill_name}: {e}"

    # ── subagent_dispatch ──────────────────────────────────────

    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """派发任务到 OpenCode 子代理

        有 orchestrator 时执行真实 dispatch，否则返回降级文件上下文模式。
        """
        # 真实 Dispatch（需要 Orchestrator）
        if self._orchestrator is not None:
            try:
                return redact_sensitive(self._orchestrator.dispatch(agent_id, task))
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
                    "message": redact_sensitive(str(e)),
                }

        # 降级路径（无 Orchestrator）：只加载本地非用户可见 role context 文档上下文，不声称已派发
        # 到原生 OpenCode 子代理运行时。
        adapter_dir = Path(__file__).parent
        agent_file = self.AGENT_FILES.get(str(agent_id))
        agent_path = adapter_dir / "agents" / agent_file if agent_file else None

        agent_context = ""
        if agent_path is not None and agent_path.exists():
            agent_context = agent_path.read_text(encoding="utf-8")

        role = self.AGENT_ROLE_MAP.get(agent_id, "Unknown")

        return {
            "agent_id": agent_id,
            "status": "degraded",
            "platform": self.platform_name,
            "error_code": "orchestrator_unavailable",
            "message": "OpenCode native sub-agent dispatch is unavailable without an injected orchestrator/runtime bridge.",
            "role": role,
            "task": redact_sensitive(task),
            "capabilities": redact_sensitive(self.capabilities()["features"]),
            "context": {
                "agent_file": agent_file,
                "user_facing": False,
                "internal_role_context": True,
                "agent_context_preview": redact_sensitive(agent_context[:500]),
                "native_dispatch_executed": False,
            },
        }
