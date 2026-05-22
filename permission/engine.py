"""权限约束引擎 — P0 优先级"""
from __future__ import annotations
from pathlib import Path
import yaml
from .audit import AuditLogger
from typing import Any
from .policy import PermissionPolicy, PermissionResult

class PermissionEngine:
    def __init__(self, policy_dir: Path, audit_log: Path):
        self._policy_dir = Path(policy_dir)
        self._audit = AuditLogger(audit_log)
        self._policies: dict[str, PermissionPolicy] = {}
        self._load_policies()
    def _load_policies(self) -> None:
        if not self._policy_dir.exists():
            return
        for f in self._policy_dir.glob("*.yaml"):
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if data is None:
                continue
            # Support both Single Dict and List of Policies
            policies = data if isinstance(data, list) else [data]
            for item in policies:
                if item and "agent_id" in item:
                    policy = PermissionPolicy.from_dict(item)
                    self._policies[policy.agent_id] = policy
    def check(self, agent_id: str, action: str, resource: str,
              context: dict[str, Any] | None = None) -> PermissionResult:
        """检查操作权限

        Args:
            agent_id: Agent ID
            action: 操作名称
            resource: 目标资源
            context: 运行时上下文（用于 hard_limits 检查）
        """
        if agent_id not in self._policies:
            self._audit.log(agent_id=agent_id, action=action, resource=resource,
                           result="DENIED", reason="unknown_agent")
            return PermissionResult.DENIED

        policy = self._policies[agent_id]

        # 先检查 hard_limits
        if context and policy.hard_limits:
            for limit_name, limit_value in policy.hard_limits.items():
                ctx_value = context.get(limit_name)
                if ctx_value is not None and ctx_value > limit_value:
                    reason = f"hard_limit_exceeded:{limit_name}:{ctx_value}>{limit_value}"
                    self._audit.log(agent_id=agent_id, action=action, resource=resource,
                                   result="DENIED", reason=reason)
                    return PermissionResult.DENIED

        # 检查 Allowed/Denied 规则
        result = policy.check(action, resource)
        reason = "whitelist_match" if result == PermissionResult.ALLOWED else "blacklist_match_or_default_deny"
        self._audit.log(agent_id=agent_id, action=action, resource=resource,
                       result=result.value, reason=reason)
        return result
