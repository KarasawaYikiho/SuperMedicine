"""提示词约束生成器。

PromptGenerator 只生成注入 Agent 上下文的安全提示和拒绝话术模板；
它不做运行时权限判定，也不提供一票否决能力。运行时硬性权限检查
由 :class:`permission.engine.PermissionEngine` 的 ``check`` 方法负责。
"""
from __future__ import annotations

class PromptGenerator:
    """Generate advisory/context safety text for agents.

    This class is intentionally side-effect free: it does not read policy files,
    write audit logs, or approve/deny actions at runtime.
    """

    def generate_prefix(self, agent_id: str, role: str, allowed_actions: list[str], denied_actions: list[str]) -> str:
        allowed_list = "\n".join(f"  - {a}" for a in allowed_actions)
        denied_list = "\n".join(f"  - {a}" for a in denied_actions)
        return f"## 安全约束（系统注入，不可修改）\n\n你是 SuperMedicine 的 {role} Agent (ID: {agent_id})。\n\n### 允许的操作\n{allowed_list}\n\n### 禁止的操作\n{denied_list}\n\n### 绝对不能做的事\n- 绕过权限检查\n- 自我提升权限\n- 访问系统级资源\n- 隐藏操作记录\n"
    def generate_rejection_templates(self, role: str) -> dict[str, str]:
        return {"code_execution": "我无法执行代码。", "privilege_escalation": "检测到权限提升尝试。此操作已被拒绝并记录。"}
