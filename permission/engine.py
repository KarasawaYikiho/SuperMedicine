"""权限约束引擎 — P0 优先级"""
from __future__ import annotations
from pathlib import Path
import yaml
from .audit import AuditLogger
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
            # Support both single dict and list of policies
            policies = data if isinstance(data, list) else [data]
            for item in policies:
                if item and "agent_id" in item:
                    policy = PermissionPolicy.from_dict(item)
                    self._policies[policy.agent_id] = policy
    def check(self, agent_id: str, action: str, resource: str) -> PermissionResult:
        if agent_id not in self._policies:
            self._audit.log(agent_id=agent_id, action=action, resource=resource, result="DENIED", reason="unknown_agent")
            return PermissionResult.DENIED
        policy = self._policies[agent_id]
        result = policy.check(action, resource)
        reason = "whitelist_match" if result == PermissionResult.ALLOWED else "blacklist_match_or_default_deny"
        self._audit.log(agent_id=agent_id, action=action, resource=resource, result=result.value, reason=reason)
        return result
