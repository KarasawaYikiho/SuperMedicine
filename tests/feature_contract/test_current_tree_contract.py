from __future__ import annotations

import importlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.maintainers.human_maintenance_snapshot import (
    build_snapshot,
    collect_file_inventory,
)


BASELINE_PATH = Path("docs/maintainers/human-maintenance-baseline.json")
BUDGET_PATH = Path("docs/maintainers/human-maintenance-budget.json")
HISTORICAL_IMPORTS = {
    "core.workspace_tool_templates": "BUILTIN_TEMPLATES",
    "core.log_severity": "format_log_message",
    "core.paper_import.errors": "PaperImportError",
    "core.paper_import.models": "PaperMetadata",
    "core.llm_providers.openrouter": "OpenRouterClient",
    "plugins.standards.medical_citation.vancouver_format": "VancouverFormatter",
}


def _baseline(repository_root: Path) -> dict[str, Any]:
    return json.loads((repository_root / BASELINE_PATH).read_text(encoding="utf-8"))


def test_current_reviewed_feature_ids_are_frozen(
    repository_root: Path, manifest: dict[str, Any]
) -> None:
    baseline = _baseline(repository_root)
    current_ids = {record["feature_id"] for record in manifest["features"]}

    assert len(current_ids) >= 186
    assert set(baseline["feature_ids"]) <= current_ids
    assert "config_env:SM_PROJECT_ROOT" in current_ids


def test_current_surface_entries_do_not_regress(repository_root: Path) -> None:
    baseline = _baseline(repository_root)
    current = build_snapshot(repository_root)

    for surface, entries in baseline["surface_entries"].items():
        assert set(entries) <= set(current["surface_entries"][surface]), surface

    counts = {key: len(value) for key, value in current["surface_entries"].items()}
    assert counts["cli"] >= 43
    assert counts["web"] >= 48
    assert counts["plugin_provide"] >= 36
    assert counts["adapter"] >= 3
    assert counts["tui_action"] >= 5
    assert counts["config_env"] >= 6
    assert counts["database_table"] >= 5


def test_current_public_signatures_are_reviewed(repository_root: Path) -> None:
    baseline = _baseline(repository_root)
    _files, current_signatures = collect_file_inventory(repository_root)

    assert current_signatures == baseline["public_signatures"]


def test_human_maintenance_hard_budgets_do_not_regress(repository_root: Path) -> None:
    budget = json.loads((repository_root / BUDGET_PATH).read_text(encoding="utf-8"))
    current = build_snapshot(repository_root)["structural_metrics"]

    for metric, maximum in budget["hard_maximums"].items():
        assert current[metric] <= maximum, metric


def test_every_production_file_has_one_maintenance_role(repository_root: Path) -> None:
    baseline = _baseline(repository_root)
    current = build_snapshot(repository_root)
    allowed = {"authority", "interface", "compat", "data", "generated/release", "candidate"}

    assert set(current["files"]) == set(baseline["files"])
    assert all(item["role"] in allowed for item in current["files"].values())
    assert Counter(item["role"] for item in current["files"].values()) == Counter(
        item["role"] for item in baseline["files"].values()
    )


def test_feature_implementation_map_is_complete(repository_root: Path) -> None:
    baseline = _baseline(repository_root)
    rows = baseline["feature_implementation_map"]

    assert len(rows) == len(baseline["feature_ids"])
    assert {row["feature_id"] for row in rows} == set(baseline["feature_ids"])
    assert all((repository_root / row["authority"]).is_file() for row in rows)
    assert all(row["risk"] in {"medium", "high"} for row in rows)


def test_historical_module_contracts_remain_importable() -> None:
    for module_name, symbol in HISTORICAL_IMPORTS.items():
        assert hasattr(importlib.import_module(module_name), symbol), module_name
