"""Structural budgets and compatibility contracts for PR-10 convergence."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _python_files(directory: Path, *, recursive: bool = False) -> list[Path]:
    pattern = "**/*.py" if recursive else "*.py"
    return [path for path in directory.glob(pattern) if path.name != "__init__.py"]


def test_core_domain_file_budgets_are_converged():
    workspace = list((ROOT / "core").glob("workspace*.py"))
    log_domain = [
        path
        for path in (ROOT / "core").glob("log*.py")
        if path.name.startswith("log_report") or path.name == "log_severity.py"
    ]
    paper = _python_files(ROOT / "core" / "paper_import")

    assert len(workspace) <= 4
    assert len(log_domain) <= 3
    assert len(paper) <= 4


def test_remaining_domain_file_budgets_are_converged():
    llm = list((ROOT / "core").glob("*llm*.py")) + _python_files(
        ROOT / "core" / "llm_providers"
    )
    medical = _python_files(
        ROOT / "plugins" / "standards" / "medical_citation"
    ) + _python_files(ROOT / "plugins" / "standards" / "medical_writing")
    budgets = {
        "llm": (llm, 5),
        "database": (_python_files(ROOT / "core" / "database"), 4),
        "installer": (_python_files(ROOT / "installer"), 4),
        "agents": (_python_files(ROOT / "agents"), 5),
        "adapters": (_python_files(ROOT / "adapters", recursive=True), 6),
        "figure": (_python_files(ROOT / "plugins" / "figure"), 6),
        "harness": (_python_files(ROOT / "plugins" / "harness"), 3),
        "medical": (medical, 8),
    }
    for group, (files, maximum) in budgets.items():
        assert len(files) <= maximum, (group, [path.name for path in files])


def test_tui_python_budget_is_converged():
    assert len(_python_files(ROOT / "core" / "tui", recursive=True)) <= 12


def test_historical_converged_module_paths_remain_importable():
    expected = {
        "core.workspace_tool_spec": "TOOL_AUTHORING_SPEC",
        "core.workspace_tool_templates": "BUILTIN_TEMPLATES",
        "core.log_report_models": "TUI_LOG_SESSION_ID",
        "core.log_severity": "format_log_message",
        "core.paper_import.errors": "PaperImportError",
        "core.paper_import.models": "PaperMetadata",
        "core.llm_providers.openrouter": "OpenRouterClient",
        "plugins.standards.medical_citation.vancouver_format": "VancouverFormatter",
        "core.tui.screens.chat_view": "ChatView",
        "core.tui.screens.workspace_screen": "WorkspaceView",
        "core.tui.screens.paper_screen": "PaperView",
        "core.tui.screens.permission_screen": "PermissionView",
        "core.tui.prompt_input": "PromptInput",
        "core.tui.stream_capture": "_capture_current_thread_tui_streams",
    }
    for module_name, symbol in expected.items():
        assert hasattr(importlib.import_module(module_name), symbol), module_name


def _function_length(path: Path, name: str) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]
    assert len(matches) == 1, (path, name, len(matches))
    function = matches[0]
    assert function.end_lineno is not None
    return function.end_lineno - function.lineno + 1


def test_mandatory_long_functions_are_orchestrators():
    functions = {
        (ROOT / "cli" / "parser.py", "main"),
        (ROOT / "core" / "web" / "server.py", "create_app"),
        (ROOT / "core" / "kernel_llm_chat.py", "execute_llm_chat"),
        (ROOT / "installer" / "entrypoint.py", "_run_interactive_installer"),
        (ROOT / "plugins" / "figure" / "runner.py", "execute_figure_workflow"),
        (ROOT / "permission" / "engine.py", "check"),
        (ROOT / "core" / "paper_import" / "importer.py", "import_file"),
        (ROOT / "plugins" / "tools" / "r_survival" / "main.py", "execute"),
    }
    for path, name in functions:
        assert _function_length(path, name) <= 60, (path, name)


def test_permission_and_agents_do_not_import_core_backwards():
    for package in (ROOT / "permission", ROOT / "agents"):
        for path in _python_files(package, recursive=True):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = [
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            ]
            assert not any(module == "core" or module.startswith("core.") for module in imports), path
