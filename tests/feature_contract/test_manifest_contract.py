from __future__ import annotations

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
    } <= entries
