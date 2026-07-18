from __future__ import annotations


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
