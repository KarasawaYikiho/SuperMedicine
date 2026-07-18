from __future__ import annotations


def test_required_plugins_name_their_runtime_contract(manifest: dict[str, object]) -> None:
    required_plugins = [
        record
        for record in manifest["features"]
        if record["category"] == "plugin" and record.get("required")
    ]
    assert required_plugins
    assert {record["runtime_contract"] for record in required_plugins} == {
        "rag_local_query",
        "harness_checkpoint",
    }
