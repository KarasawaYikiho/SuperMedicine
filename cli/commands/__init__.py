"""CLI command modules — one module per domain group."""

import sys

from cli.commands import execution as _execution
from cli.commands import research as _research
from cli.commands import system as _system
from cli.commands import tools as _tools

_COMPAT_MODULES = {
    "cli.commands.workspace": _research,
    "cli.commands.paper": _research,
    "cli.commands.experience": _research,
    "cli.commands.tool": _tools,
    "cli.commands.experiment": _tools,
    "cli.commands.log": _tools,
    "cli.commands.permission": _system,
    "cli.commands.self_evolve": _system,
    "cli.commands.llm": _execution,
}
for _module_name, _module in _COMPAT_MODULES.items():
    sys.modules.setdefault(_module_name, _module)
    setattr(sys.modules[__name__], _module_name.rsplit(".", 1)[1], _module)
