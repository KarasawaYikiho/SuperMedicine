"""权限声明解析与检查"""
from __future__ import annotations
import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class PermissionResult(Enum):
    ALLOWED = "allowed"
    DENIED = "denied"

@dataclass
class PermissionRule:
    action: str
    scope: str
    def matches(self, action: str, scope: str) -> bool:
        return fnmatch.fnmatch(action, self.action) and fnmatch.fnmatch(scope, self.scope)

@dataclass
class HardLimits:
    max_file_size: int = 0
    max_execution_time: int = 0
    max_memory: int = 0
    network_access: bool = True
    external_api: bool = True

    def items(self):
        """返回非零/非默认的限制项"""
        return [
            (k, v) for k, v in (
                ("max_file_size", self.max_file_size),
                ("max_execution_time", self.max_execution_time),
                ("max_memory", self.max_memory),
            ) if v > 0
        ]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HardLimits:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class PermissionPolicy:
    agent_id: str
    role: str
    security_level: str = "restricted"
    allowed: list[PermissionRule] = field(default_factory=list)
    denied: list[PermissionRule] = field(default_factory=list)
    hard_limits: HardLimits = field(default_factory=HardLimits)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PermissionPolicy:
        perms = data.get("permissions", {})
        allowed = [PermissionRule(action=r["action"], scope=r["scope"]) for r in perms.get("allowed", [])]
        denied = [PermissionRule(action=r["action"], scope=r["scope"]) for r in perms.get("denied", [])]
        hard_limits = HardLimits.from_dict(perms.get("hard_limits", {}))
        return cls(agent_id=data["agent_id"], role=data["role"], security_level=data.get("security_level", "restricted"), allowed=allowed, denied=denied, hard_limits=hard_limits)
    def check(self, action: str, scope: str) -> PermissionResult:
        for rule in self.denied:
            if rule.matches(action, scope):
                return PermissionResult.DENIED
        for rule in self.allowed:
            if rule.matches(action, scope):
                return PermissionResult.ALLOWED
        return PermissionResult.DENIED
