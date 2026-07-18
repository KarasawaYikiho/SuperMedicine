"""Agent 编排 — 状态机 + 检查点 + 多 Agent 协作"""

from __future__ import annotations

from agents.orchestrator import Orchestrator
from agents.roles import (
    ROLE_SPECS,
    AlphaAgent,
    BaseAgent,
    BetaAgent,
    DeltaAgent,
    GammaAgent,
    RoleSpec,
)
from agents.state_machine import StateMachine, TaskState
from agents.checkpoint import CheckpointManager

__all__ = [
    "Orchestrator",
    "RoleSpec",
    "ROLE_SPECS",
    "BaseAgent",
    "StateMachine",
    "TaskState",
    "CheckpointManager",
    "AlphaAgent",
    "BetaAgent",
    "GammaAgent",
    "DeltaAgent",
]
