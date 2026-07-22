"""Shared application services used by CLI, TUI, Web, and GUI adapters."""

import sys

from core.services import execution as _execution
from core.services import system as _system
from core.services.execution import AgentHarnessService, LLMService
from core.services.experiment_tool import ExperimentToolService
from core.services.experience_evolution import ExperienceEvolutionService
from core.services.paper_rag import PaperRAGService
from core.services.result import ServiceError, ServiceResult
from core.services.system import AdapterService, PermissionLogSystemService
from core.services.workspace import WorkspaceService

_COMPAT_MODULES = {
    "core.services.agent_harness": _execution,
    "core.services.llm": _execution,
    "core.services.adapter": _system,
    "core.services.permission_log_system": _system,
}
for _module_name, _module in _COMPAT_MODULES.items():
    sys.modules.setdefault(_module_name, _module)

__all__ = [
    "AgentHarnessService",
    "AdapterService",
    "ExperimentToolService",
    "ExperienceEvolutionService",
    "LLMService",
    "PaperRAGService",
    "PermissionLogSystemService",
    "ServiceError",
    "ServiceResult",
    "WorkspaceService",
]
