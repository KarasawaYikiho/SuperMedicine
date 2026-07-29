from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict[str, Any]:
    return json.loads(
        (REPOSITORY_ROOT / "feature_manifest.json").read_text(encoding="utf-8")
    )


def test_feature_manifest_preserves_unique_baseline_capabilities() -> None:
    manifest = _manifest()
    records = manifest["features"]
    feature_ids = [record["feature_id"] for record in records]

    assert feature_ids
    assert len(feature_ids) == len(set(feature_ids))
    assert set(manifest["baseline_feature_ids"]) <= set(feature_ids)
    assert all(
        {"feature_id", "category", "entrypoint", "expected_result"} <= set(record)
        for record in records
    )
    assert all("contract_test" not in record for record in records)


def test_feature_manifest_preserves_mandatory_and_optional_runtime_contracts() -> None:
    records = {record["feature_id"]: record for record in _manifest()["features"]}

    assert records["plugin:rag-interface"]["required"] is True
    assert records["plugin:rag-interface"]["runtime_contract"] == "rag_local_query"
    assert records["plugin:harness-core"]["required"] is True
    assert (
        records["plugin:harness-core"]["runtime_contract"] == "harness_checkpoint"
    )
    for role in ("alpha", "beta", "gamma", "delta"):
        assert records[f"agent:{role}"]["optional_enabled"] is True


def test_required_plugins_name_their_runtime_contract() -> None:
    manifest = _manifest()
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


def test_feature_manifest_covers_every_live_web_route(tmp_path: Path) -> None:
    from core.runtime_paths import RuntimePaths
    from core.web.server import create_app

    paths = RuntimePaths.resolve(
        project_root=REPOSITORY_ROOT,
        config_path=tmp_path / "config.yaml",
    )
    app = create_app(paths=paths)
    live_routes: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path or (
            not path.startswith("/api/v1") and path not in {"/", "/ws/chat"}
        ):
            continue
        methods = getattr(route, "methods", None)
        if methods:
            live_routes.update(
                f"web:{method} {path}"
                for method in methods
                if method not in {"HEAD", "OPTIONS"}
            )
        elif path == "/ws/chat":
            live_routes.add("web:WEBSOCKET /ws/chat")

    declared_routes = {
        record["feature_id"]
        for record in _manifest()["features"]
        if record["category"] == "web"
    }
    assert declared_routes == live_routes
