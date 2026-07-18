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


def test_figure_keeps_all_entrypoints_in_six_maintainer_owned_modules():
    paths = sorted((PROJECT_ROOT / "plugins" / "figure").glob("*.py"))
    assert [path.name for path in paths] == [
        "__init__.py",
        "audit.py",
        "export.py",
        "presentation.py",
        "profile.py",
        "runner.py",
    ]

    from plugins.figure.runner import _ACTION_MAP

    assert set(_ACTION_MAP) == {
        "figure-profile.profile",
        "figure-style.setup",
        "figure-style.list-fonts",
        "figure-export.export",
        "figure-check.audit",
        "figure-layout.labels",
        "figure-layout.finalize",
        "figure-qa.audit",
        "figure-qa.preview",
    }

    from plugins.figure.check import check_figure
    from plugins.figure.layout import finalize_figure
    from plugins.figure.qa import audit_layout
    from plugins.figure.style import setup_style

    assert all(
        callable(item)
        for item in (check_figure, finalize_figure, audit_layout, setup_style)
    )
