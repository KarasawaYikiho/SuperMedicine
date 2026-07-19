"""Architecture contracts for the human-maintainer application boundary."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_PATHS = (
    PROJECT_ROOT / "cli",
    PROJECT_ROOT / "core" / "tui",
    PROJECT_ROOT / "core" / "web",
    PROJECT_ROOT / "cli_entry.py",
    PROJECT_ROOT / "gui_entry.py",
    PROJECT_ROOT / "gui_standalone.py",
)
ADAPTER_PATH = PROJECT_ROOT / "adapters"
FORBIDDEN_CONSTRUCTORS = {
    "DialogHistoryStore",
    "ExperienceStore",
    "LogReportStore",
    "PermissionEngine",
    "PluginRegistry",
}


def _python_files(path: Path) -> list[Path]:
    return sorted(path.rglob("*.py")) if path.is_dir() else [path]


def _call_name(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def test_ui_adapters_do_not_construct_internal_stores_or_permission_runtime():
    violations: list[str] = []
    for root in UI_PATHS:
        for path in _python_files(root):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and _call_name(node) in FORBIDDEN_CONSTRUCTORS
                ):
                    relative = path.relative_to(PROJECT_ROOT)
                    violations.append(f"{relative}:{node.lineno}:{_call_name(node)}")

    assert violations == []


def test_platform_adapters_depend_on_application_services_not_permission_or_kernel():
    forbidden_modules = {"permission.engine", "core.kernel"}
    violations: list[str] = []
    for path in _python_files(ADAPTER_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in forbidden_modules:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{node.module}"
                )
            if (
                isinstance(node, ast.Call)
                and _call_name(node) in FORBIDDEN_CONSTRUCTORS
            ):
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{_call_name(node)}"
                )
    assert violations == []


def test_pr05_adapter_surface_is_consolidated_to_human_scale():
    paths = _python_files(ADAPTER_PATH)
    function_count = 0
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function_count += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in ast.walk(tree)
        )
    assert 5 <= len(paths) <= 6
    assert 35 <= function_count <= 45


def test_pr02_orchestration_entrypoints_remain_small():
    targets = {
        PROJECT_ROOT / "cli" / "parser.py": {"main": 60},
        PROJECT_ROOT / "core" / "web" / "server.py": {"create_app": 60},
        PROJECT_ROOT / "core" / "kernel_llm_chat.py": {"execute_llm_chat": 60},
    }
    observed: dict[str, int] = {}
    for path, limits in targets.items():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in limits
            ):
                size = int(node.end_lineno or node.lineno) - node.lineno + 1
                observed[f"{path.name}:{node.name}"] = size
                assert size <= limits[node.name]

    assert set(observed) == {
        "parser.py:main",
        "server.py:create_app",
        "kernel_llm_chat.py:execute_llm_chat",
    }
