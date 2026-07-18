from __future__ import annotations

import ast
from pathlib import Path

from tests.feature_contract.inventory import discovered_surface

def test_manifest_has_unique_ids_and_required_contract_fields(manifest: dict[str, object]) -> None:
    records = manifest["features"]
    assert isinstance(records, list)
    assert records
    ids = [record["feature_id"] for record in records]
    assert len(ids) == len(set(ids))
    required_fields = {
        "feature_id",
        "category",
        "entrypoint",
        "expected_result",
        "contract_test",
    }
    for record in records:
        assert required_fields <= set(record)


def test_manifest_covers_declared_web_and_plugin_entries(manifest: dict[str, object]) -> None:
    entries = {record["entrypoint"] for record in manifest["features"]}
    assert {
        "web:GET /api/v1/status",
        "web:POST /api/v1/chat",
        "plugin_provide:harness.integration.checkpoint",
        "plugin_provide:rag.query",
    } <= entries


def test_manifest_matches_static_inventory(
    repository_root: Path, manifest: dict[str, object]
) -> None:
    manifest_entries = {record["entrypoint"] for record in manifest["features"]}
    discovered_entries = {
        entrypoint
        for values in discovered_surface(repository_root).values()
        for entrypoint in values
    }
    assert discovered_entries <= manifest_entries


def test_manifest_covers_tui_actions_and_configuration_keys(manifest: dict[str, object]) -> None:
    entries = {record["entrypoint"] for record in manifest["features"]}
    assert {
        "tui_action:show_help",
        "config_env:SM_CONFIG",
        "config_env:SM_LLM_API_KEY",
    } <= entries


def test_each_manifest_contract_node_exists(
    repository_root: Path, manifest: dict[str, object]
) -> None:
    for record in manifest["features"]:
        path_text, function_name = record["contract_test"].split("::", maxsplit=1)
        test_path = repository_root / path_text
        assert test_path.is_file(), record["feature_id"]
        functions = {
            node.name
            for node in ast.walk(ast.parse(test_path.read_text(encoding="utf-8")))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert function_name in functions, record["feature_id"]


def test_feature_id_baseline_never_regresses(manifest: dict[str, object]) -> None:
    current_ids = {record["feature_id"] for record in manifest["features"]}
    baseline_ids = set(manifest["baseline_feature_ids"])
    assert baseline_ids <= current_ids
    assert len(current_ids) >= manifest["metrics"]["feature_id_count"]


def test_manifest_covers_release_entrypoints(manifest: dict[str, object]) -> None:
    entries = {record["entrypoint"] for record in manifest["features"]}
    assert {
        "entrypoint:cli_entry.py",
        "entrypoint:gui_entry.py",
        "entrypoint:install_entry.py",
        "entrypoint:uninstall_entry.py",
        "release_builder:scripts/ci/build_gui_exe.py",
        "release_builder:scripts/ci/build_installer_exe.py",
        "release_builder:scripts/ci/build_release_zip.py",
    } <= entries
