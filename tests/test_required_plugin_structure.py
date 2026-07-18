"""Structural contracts for required RAG and Harness plugins."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _function_count(paths: list[Path]) -> int:
    return sum(
        sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        )
        for path in paths
    )


def test_rag_stays_within_consolidated_file_and_function_targets():
    paths = sorted((PROJECT_ROOT / "plugins" / "rag").glob("*.py"))
    assert [path.name for path in paths] == [
        "__init__.py",
        "main.py",
        "providers.py",
        "pubmed_provider.py",
    ]
    assert 35 <= _function_count(paths) <= 45


def test_harness_keeps_one_entrypoint_and_one_shared_monitor_module():
    paths = sorted((PROJECT_ROOT / "plugins" / "harness").glob("*.py"))
    assert [path.name for path in paths] == ["__init__.py", "main.py", "monitor.py"]
    monitor_source = (PROJECT_ROOT / "plugins" / "harness" / "monitor.py").read_text(
        encoding="utf-8"
    )
    assert "from agents.checkpoint import CheckpointRepository" in monitor_source
