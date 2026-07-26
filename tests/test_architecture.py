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
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def test_ui_surfaces_use_application_services_instead_of_internal_stores() -> None:
    violations: list[str] = []
    for root in UI_PATHS:
        for path in _python_files(root):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and _call_name(node) in FORBIDDEN_CONSTRUCTORS
                ):
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:"
                        f"{_call_name(node)}"
                    )
    assert violations == []


def test_platform_adapters_do_not_bypass_application_services() -> None:
    violations: list[str] = []
    for path in _python_files(PROJECT_ROOT / "adapters"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in {
                "permission.engine",
                "core.kernel",
            }:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{node.module}"
                )
            if (
                isinstance(node, ast.Call)
                and _call_name(node) in FORBIDDEN_CONSTRUCTORS
            ):
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:"
                    f"{_call_name(node)}"
                )
    assert violations == []


def test_permission_and_agents_do_not_import_core_backwards() -> None:
    violations: list[str] = []
    for package in (PROJECT_ROOT / "permission", PROJECT_ROOT / "agents"):
        for path in _python_files(package):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (
                    node.module == "core"
                    or (node.module or "").startswith("core.")
                ):
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:"
                        f"{node.module}"
                    )
                elif isinstance(node, ast.Import):
                    violations.extend(
                        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{alias.name}"
                        for alias in node.names
                        if alias.name == "core" or alias.name.startswith("core.")
                    )
    assert violations == []
