"""Shared application services used by CLI, TUI, Web, and GUI adapters."""

import sys

from core.services import execution as _execution
from core.services import research as _research
from core.services import system as _system
from core.services.execution import AgentHarnessService, LLMService
from core.services.experiment_tool import ExperimentToolService
from core.services.research import (
    ExperienceEvolutionService,
    PaperRAGService,
    WorkspaceService,
)
from core.services.result import ServiceError, ServiceResult
from core.services.system import AdapterService, PermissionLogSystemService

_COMPAT_MODULES = {
    "core.services.agent_harness": _execution,
    "core.services.llm": _execution,
    "core.services.adapter": _system,
    "core.services.permission_log_system": _system,
    "core.services.workspace": _research,
    "core.services.paper_rag": _research,
    "core.services.experience_evolution": _research,
}
for _module_name, _module in _COMPAT_MODULES.items():
    sys.modules.setdefault(_module_name, _module)
    setattr(sys.modules[__name__], _module_name.rsplit(".", 1)[1], _module)

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
