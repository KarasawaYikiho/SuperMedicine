"""Structural contracts for the data-driven multi-agent subsystem."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_agents_are_consolidated_without_core_dependency_cycle():
    paths = sorted((PROJECT_ROOT / "agents").glob("*.py"))
    assert [path.name for path in paths] == [
        "__init__.py",
        "checkpoint.py",
        "orchestrator.py",
        "roles.py",
    ]
    function_count = 0
    core_imports: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function_count += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in ast.walk(tree)
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "core"
            ):
                core_imports.append(f"{path.name}:{node.lineno}:{node.module}")
            if isinstance(node, ast.Import):
                core_imports.extend(
                    f"{path.name}:{node.lineno}:{alias.name}"
                    for alias in node.names
                    if alias.name.startswith("core")
                )

    assert 30 <= function_count <= 40
    assert core_imports == []
