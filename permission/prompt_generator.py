"""提示词约束生成器。

PromptGenerator 只生成注入 SuperMedicine 执行上下文的安全提示和拒绝话术模板；
它不做运行时权限判定，也不提供一票否决能力。运行时硬性权限检查
由 :class:`permission.engine.PermissionEngine` 的 ``check`` 方法负责。
"""

from __future__ import annotations


class PromptGenerator:
    """Generate advisory/context safety text for agents.

    This class is intentionally side-effect free: it does not read policy files,
    write audit logs, or approve/deny actions at runtime.
    """

    SELF_EVOLUTION_GUIDANCE = """### 自进化执行指南（随安全上下文注入，必须执行）
- 在生成、修改或建议任何自进化产物前，先逐项检查：当前 permission mode（sandbox/conservative/full）、sandbox 写入边界、目标路径、产物类型、风险等级、是否需要用户显式确认、敏感信息处理要求、审计/日志要求，以及该产物是否属于禁止 Git 上传的工程文件。
- 自进化只能生成允许的工具或 Markdown 产物；目标路径必须位于已批准根目录（例如 self_evolution、generated、tools/generated）内，并受当前 sandbox restrictions、扩展名白名单和覆盖保护约束。
- Docs、docs、REQUIREMENTS_TRACEABILITY.md 以及类似需求追踪、审计草稿、工程过程记录、平台适配过程说明等 engineering-only files 绝不能被视为 Git-submittable artifacts，也不得作为自进化输出目标生成或建议提交。
- 生成工程辅助文件时必须明确标记为不可提交/不可上传 Git；不得把 Docs/docs/REQUIREMENTS_TRACEABILITY.md 或任何禁止工程文档加入暂存区、提交、发布包或用户可上传清单。
- 处理敏感信息时只能使用脱敏摘要或占位符；不得写入明文 API key、token、authorization header、私钥、原始对话秘密或可识别凭据。日志、审计记录和生成文件必须保留必要上下文但执行 redaction。
- 若权限模式、sandbox 限制、目标路径、产物类型、风险等级、确认状态、敏感信息状态或审计要求任一项不满足，必须停止写入，仅返回预览/拒绝说明，并说明缺失条件。
- full 或高风险操作必须要求用户显式确认并保留审计记录；不得绕过 permission engine、audit logger、路径安全校验或 overwrite 防护。
"""

    def generate_prefix(
        self,
        agent_id: str,
        role: str,
        allowed_actions: list[str],
        denied_actions: list[str],
    ) -> str:
        allowed_list = "\n".join(f"  - {a}" for a in allowed_actions)
        denied_list = "\n".join(f"  - {a}" for a in denied_actions)
        return f"## 安全约束（系统注入，不可修改）\n\n你是 SuperMedicine 的 {role} 执行上下文 (ID: {agent_id})。\n\n### 允许的操作\n{allowed_list}\n\n### 禁止的操作\n{denied_list}\n\n{self.SELF_EVOLUTION_GUIDANCE}\n### 绝对不能做的事\n- 绕过权限检查\n- 自我提升权限\n- 访问系统级资源\n- 隐藏操作记录\n"

    def generate_rejection_templates(self, role: str) -> dict[str, str]:
        return {
            "code_execution": "我无法执行代码。",
            "privilege_escalation": "检测到权限提升尝试。此操作已被拒绝并记录。",
        }
